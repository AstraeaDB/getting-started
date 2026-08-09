<!-- SEO subtitle (Medium meta description): Add embeddings to your graph in Python with AstraeaDB: vector search, hybrid graph and vector queries, and semantic traversals to build a recommender. -->

# Vector and Hybrid Search with AstraeaDB in Python

*Turn your movie graph into a recommender by combining its connections with search over embedding vectors.*

In the first post, [Getting Started with AstraeaDB in Python: A Graph + Vector Database in Minutes](./py-01-getting-started.md), we started a server, connected with `AstraeaClient`, and built a small movie knowledge graph. A knowledge graph stores facts as nodes joined by labeled connections, so ours recorded who acted in what and which genre a film belongs to. Those facts are exact, but they cannot tell you that two movies simply feel alike. In this post we attach a short list of numbers, called an [embedding](../glossary.html#embedding), to each movie, then use AstraeaDB's vector and [hybrid search](../glossary.html#hybrid-search) to answer the question every recommender is really asking: what else feels like this one?

## Why vectors live next to the graph

A graph handles exact facts well: Keanu Reeves acted in *The Matrix*. It struggles with softer questions, though. The idea that "these two movies have a similar mood" is not a connection you can draw by hand, because similarity is a matter of degree rather than a simple yes or no. An embedding captures that degree. It is a list of numbers, also called a vector, that places each item at a point in an imaginary space where items sitting close together are alike. Picture it like placing towns on a map, where neighbors tend to share a climate. AstraeaDB stores these vectors on the nodes and builds a fast search structure over them, an [HNSW](../glossary.html#hierarchical-navigable-small-world-hnsw) index (Hierarchical Navigable Small World), right beside the graph. Because both live in one database, a single system can answer "who directed this?" and "which movies are closest in meaning to this one?"

When AstraeaDB compares two vectors, it reports a distance, a single number measuring how far apart they are. The rule to remember is simple: a smaller distance means the two items are more similar.

## Recap: connect and rebuild, this time with embeddings

If you followed the first post you already have the graph, but this time each `Movie` also carries a small embedding for its plot. To keep the example easy to paste and run, we use hand-written vectors of four numbers each, and you can read the four positions as `[sci-fi, action, romance, drama]`. In a real system you would generate them from each movie's plot text with an embedding model, such as a sentence-transformer or an embeddings service you call over the web. One rule always holds: every vector you store must have the same number of values, a property called its dimensionality.

```python
from astraeadb import AstraeaClient

# Toy "plot" embeddings. Axes ~ [sci-fi, action, romance, drama].
MOVIES = {
"The Matrix":         (1999, [0.90, 0.80, 0.05, 0.20]),
"The Matrix Reloaded":(2003, [0.85, 0.85, 0.05, 0.15]),
"John Wick":          (2014, [0.10, 0.95, 0.05, 0.25]),
"Inception":          (2010, [0.80, 0.55, 0.15, 0.55]),
"Interstellar":       (2014, [0.85, 0.35, 0.25, 0.75]),
"The Notebook":       (2004, [0.05, 0.10, 0.95, 0.80]),
"Forrest Gump":       (1994, [0.10, 0.20, 0.45, 0.90]),
}

# Open a connection and keep it open for the rest of this lesson.
client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

# Movies carry the embedding via the create_node `embedding` argument.
movies = {}
for title, (year, vec) in MOVIES.items():
    movies[title] = client.create_node(
        ["Movie"], {"title": title, "year": year}, embedding=vec
    )

# A few people, and who acted in / directed what.
people = {}
for name in ["Keanu Reeves", "Carrie-Anne Moss",
             "Lana Wachowski", "Christopher Nolan"]:
    people[name] = client.create_node(["Person"], {"name": name})

def acted(name, title):
    client.create_edge(people[name], movies[title], "ACTED_IN")

def directed(name, title):
    client.create_edge(people[name], movies[title], "DIRECTED")

acted("Keanu Reeves", "The Matrix")
acted("Keanu Reeves", "The Matrix Reloaded")
acted("Keanu Reeves", "John Wick")
acted("Carrie-Anne Moss", "The Matrix")
acted("Carrie-Anne Moss", "The Matrix Reloaded")
directed("Lana Wachowski", "The Matrix")
directed("Lana Wachowski", "The Matrix Reloaded")
directed("Christopher Nolan", "Inception")
directed("Christopher Nolan", "Interstellar")

print("movies:", len(movies), "people:", len(people))
```

Everything from here on reuses the `client` you opened above, so run it in the same session. `client`, `movies`, and `people` all stay in scope.

## `vector_search`: find movies with a similar feel

The most direct kind of recommendation is a nearest-neighbor search: you hand the database a query vector and get back the stored nodes whose vectors are closest to it. Here we ask for movies that suit a sci-fi action night, meaning ones that score high on the first two axes and low on romance and drama:

```python
vibe = [0.90, 0.90, 0.05, 0.10]          # what we're in the mood for
hits = client.vector_search(vibe, k=5)   # list of {node_id, distance, score}

id_to_title = {nid: t for t, nid in movies.items()}
for h in hits:
    title = id_to_title.get(h["node_id"], f"node {h['node_id']}")
    print(f"{title:22s} distance={h['distance']:.4f}")
```

You will see the *Matrix* films and *John Wick* rise to the top, while *The Notebook* falls to the bottom, which is exactly the ordering our axes encode. Each result carries a `node_id`, a `distance`, and a `score`. The `score` field is a legacy alias of `distance`: it holds the very same number and is kept only so older code keeps working. Do not read it as "higher score is better." Here, a lower number is better.

A common variation is "find more movies like this one." Instead of writing a query vector by hand, you use an existing movie's own embedding as the query. A node is always closest to itself, so you simply skip the first result:

```python
query_vec = MOVIES["The Matrix"][1]      # The Matrix's own embedding
similar = client.vector_search(query_vec, k=4)
similar = [h for h in similar if h["node_id"] != movies["The Matrix"]]
print("More like The Matrix:",
      [id_to_title[h["node_id"]] for h in similar])
```

## `hybrid_search`: blend graph connections with vector similarity

Plain [vector search](../glossary.html#vector-search) ignores everything the graph already knows. A good recommender should respect connections as well. If you are browsing an actor's page, movies near that actor in the graph are usually more relevant than a random film that happens to have a similar embedding. Hybrid search does exactly this, and "hybrid" just means it mixes two kinds of information. It starts from an anchor node, the node you want results to stay near, explores outward up to `max_hops` steps away (one hop being one connection you follow), and ranks the candidates by combining two signals:

- Graph proximity measures how close a candidate is to the anchor by counting connections.
- Vector similarity measures how close a candidate's embedding is to your query vector.

The `alpha` argument is the dial between the two signals. Setting `alpha=0` uses graph proximity alone, `alpha=1` uses vector similarity alone, and `0.5` gives an even mix. Below we anchor on Keanu Reeves and ask for sci-fi-leaning recommendations near him:

```python
scifi = [0.95, 0.50, 0.05, 0.20]
blended = client.hybrid_search(
    anchor=people["Keanu Reeves"],
    query_vector=scifi,
    max_hops=3,
    k=5,
    alpha=0.5,          # half graph proximity, half vibe
)
for h in blended:       # list of {node_id, score}
    label = id_to_title.get(h["node_id"], f"node {h['node_id']}")
    print(f"{label:22s} score={h['score']:.4f}")
```

Try adjusting `alpha`. Push it toward `0` and the results stay close to Keanu's actual filmography no matter the query. Push it toward `1` and the graph fades into the background, leaving something close to a plain `vector_search`. That single setting lets you tune how much to trust the connections versus the content, without rewriting the query itself.

## `semantic_neighbors` and `semantic_walk`: steer toward a concept

Sometimes you do not want the closest match overall. Instead, you want to move through the graph in the direction of a particular idea. You give AstraeaDB a concept vector, which is just an embedding that stands for the theme you are chasing, and it ranks or steps through neighboring nodes by how well each points toward that theme. Moving from node to node along connections like this is called traversing the graph.

`semantic_neighbors` ranks the immediate neighbors of a node, meaning the nodes one connection away, by how close they sit to a concept. Starting from *Inception*, we can ask which of its connected nodes lean most toward thoughtful science fiction:

```python
cerebral_scifi = [0.90, 0.30, 0.10, 0.60]
near = client.semantic_neighbors(
    movies["Inception"], cerebral_scifi,
    direction="outgoing", k=5,
)                                  # list of {node_id, distance}
print("Neighbors of Inception, by concept:", near)
```

`semantic_walk` goes further. From a starting node it takes up to `max_hops` steps, and at each step it moves to whichever neighbor best matches the concept. This is a greedy path, meaning it always takes the best-looking next step rather than planning the whole route ahead, and it is guided by meaning instead of by connection type alone:

```python
path = client.semantic_walk(
    movies["The Matrix"], cerebral_scifi, max_hops=3,
)
print("Concept walk from The Matrix:", path)
```

Think of these two methods as the exploring half of a recommender. `vector_search` answers "what is most similar overall?", `hybrid_search` answers "what is relevant given where I already am?", and the semantic walk answers "if I keep leaning into this theme, where do I end up?" All three read from the same vectors and the same graph, so there is no separate vector store to keep in sync.

## What's next

With these five methods you have built the core of a recommender: nearest-neighbor lookups, a tunable blend of graph and vector signals, and concept-guided exploration. In the final post, [Graph Algorithms, Time-Travel, and GraphRAG with AstraeaDB in Python](./py-03-algorithms-graphrag.md), we will add `User` nodes and `RATED` edges. We will rank the most influential people and movies with PageRank, an algorithm that scores each node by how many well-connected nodes point to it. We will group similar nodes into genre-like communities with Louvain, a method that finds clusters whose members are tightly linked. We will query the graph as it looked on a past date using time-travel traversals, which ask questions about an earlier state of the data. We will finish by feeding a small piece of the graph into [GraphRAG](../glossary.html#graphrag), short for graph retrieval-augmented generation, which hands relevant graph facts to a language model so it can answer questions in plain English.

When you are finished with this lesson, close the connection you opened at the
start:

```python
client.close()
```
