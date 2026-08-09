<!-- SEO subtitle (meta description): Store real 768-dimension embeddings in AstraeaDB, choose what text to embed per node type, and tune alpha to blend graph structure with meaning. -->

# Searching a Graph by Meaning, Not by Keyword

*Give every node a real embedding, then blend how close things are in the graph with how close they are in meaning.*

In the last post you made embeddings by hand and measured the distance between two of them. Now you will put them where they belong, next to your data, and let the database do the comparing. Along the way you will meet the decision that matters more than any other in this tier, which is not which model you use but which text you choose to feed it.

## Tell the server how wide your vectors are

A store fixes its embedding width the first time you insert one, so the server has to agree with your model before you start. Put a `[vector]` section in the configuration file you pass to `astraeadb serve`:

<!-- verify: skip reason="the verification container is started from verify/server.toml with this exact section already applied, so writing a second config here would have no effect" -->
```toml
[vector]
dimension = 768
metric = "cosine"
```

If you leave that section out entirely the server quietly defaults to 128 dimensions, and your first 768-number insert fails with a dimension mismatch. Setting it explicitly is one line and saves a confusing afternoon.

## Choosing what to embed

Here is the part that decides whether any of this works.

An embedding represents whatever text you hand it. If you embed a person's name, you get a position that means "this arrangement of letters", which is close to other similar-looking names and to nothing else useful. Ask for actors similar to Keanu Reeves and you will get back people whose names sound alike. That is almost never what anyone wants.

The fix is to embed a short sentence that describes the thing, built from the properties you already have. Not the name, but what the name refers to:

```python
import json
import os
import urllib.request

from astraeadb import AstraeaClient

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def embed(texts):
    payload = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


MOVIES = [
    ("The Matrix", 1999, "A hacker discovers reality is a simulation and joins a rebellion against the machines."),
    ("The Matrix Reloaded", 2003, "Neo fights on to free humankind as the machine army closes in on the last human city."),
    ("John Wick", 2014, "A retired hitman returns to the criminal underworld to avenge his dog."),
    ("Arrival", 2016, "A linguist is recruited to communicate with aliens whose language reshapes how she experiences time."),
    ("The Notebook", 2004, "A young couple fall in love one summer and are separated by class and war."),
]

# For a movie the plot is already a description, so embed that.
movie_text = [plot for _, _, plot in MOVIES]

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

movies = {}
for (title, year, plot), vec in zip(MOVIES, embed(movie_text)):
    movies[title] = client.create_node(
        ["Movie"], {"title": title, "year": year, "plot": plot}, embedding=vec)

print("stored", len(movies), "movies")
```

A `Movie` was easy, because a plot is already a description. A `Person` is the interesting case. There is no descriptive text on the node, so you compose one from the graph around it:

```python
PEOPLE = {
    "Keanu Reeves": "An actor known for science fiction and action films about identity and violence.",
    "Amy Adams": "An actor known for thoughtful science fiction and character-driven drama.",
    "Ryan Gosling": "An actor known for romantic drama and quiet, brooding leading roles.",
}

people = {}
for (name, blurb), vec in zip(PEOPLE.items(), embed(list(PEOPLE.values()))):
    people[name] = client.create_node(
        ["Person"], {"name": name, "blurb": blurb}, embedding=vec)

for actor, film in [("Keanu Reeves", "The Matrix"), ("Keanu Reeves", "The Matrix Reloaded"),
                    ("Keanu Reeves", "John Wick"), ("Amy Adams", "Arrival"),
                    ("Ryan Gosling", "The Notebook")]:
    client.create_edge(people[actor], movies[film], "ACTED_IN")

# Genres give the graph a second layer, which matters for the last section.
GENRES = ["Science Fiction", "Action", "Romance"]
genres = {}
for name, vec in zip(GENRES, embed([f"Films in the {g} genre." for g in GENRES])):
    genres[name] = client.create_node(["Genre"], {"name": name}, embedding=vec)

for film, genre in [("The Matrix", "Science Fiction"), ("The Matrix", "Action"),
                    ("The Matrix Reloaded", "Science Fiction"), ("John Wick", "Action"),
                    ("Arrival", "Science Fiction"), ("The Notebook", "Romance")]:
    client.create_edge(movies[film], genres[genre], "IN_GENRE")

print("stored", len(people), "people and", len(genres), "genres")
```

Writing those descriptions by hand does not scale, and in a real system you would generate them, which is exactly what the next post does with a book. The point to carry forward is that the sentence you embed is a design decision, and a bad one cannot be rescued by a better model.

## Searching the whole store

[Vector search](../glossary.html#vector-search) compares your query against every embedding in the store and returns the closest, wherever they sit in the graph:

```python
query = embed(["a film about language and how it shapes thought"])[0]

for hit in client.vector_search(query, k=3):
    node = client.get_node(hit["node_id"])
    label = node["properties"].get("title") or node["properties"].get("name")
    print(f'{hit["distance"]:.3f}  {label}')
```

`Arrival` should come first, and nothing in that query appears in its plot text. No keyword matched. The word "linguist" is not "language", and "reshapes how she experiences time" is not "shapes thought". The embedding found it because the meanings are close.

Note the field name. Results carry a `distance`, and **lower is better**. It is easy to read a number as a score where bigger wins, and get your ranking backwards.

## Blending meaning with structure

Vector search ignores your graph completely, which is a waste when the connections are the reason you chose a graph database. [Hybrid search](../glossary.html#hybrid-search) fixes that by starting from an anchor node and scoring nearby nodes on both counts at once:

```python
anchor = people["Keanu Reeves"]
query = embed(["a thoughtful science fiction film about language"])[0]

for alpha in (0.0, 0.5, 1.0):
    hits = client.hybrid_search(anchor, query, max_hops=3, k=5, alpha=alpha)
    names = []
    for h in hits:
        props = client.get_node(h["node_id"])["properties"]
        names.append(props.get("title") or props.get("name"))
    print(f"alpha={alpha}: {names}")
```

Watch `John Wick` move down the list. At `alpha = 0` it sits with the other two
films Keanu acted in, because all three are one hop away and nothing but hops
counts. As alpha rises it falls behind them, and at `alpha = 1` it is last,
because a film about avenging a dog has little to do with language. The graph
never changed. Only the weighting did.

The scoring rule is worth knowing exactly, because it explains everything you will see:

    score = alpha * vector_distance + (1 - alpha) * graph_distance

Both parts are distances, so a lower score wins. `alpha = 0` ignores meaning entirely and ranks purely by how few hops away something is. `alpha = 1` ignores the graph and ranks purely by meaning. Anything between blends the two.

Now look at what is missing from every one of those lists. `Arrival` is the best
answer in the store to a query about language, and vector search put it first a
moment ago. Hybrid search never returns it at any alpha, because hybrid search
only considers nodes it can **reach from the anchor within `max_hops`**, and
following edges in the direction they point there is no route from Keanu Reeves
to `Arrival`. Raising alpha cannot help, because the node was never a candidate.

That is the trade. Vector search sees everything and knows nothing about your
graph. Hybrid search respects your graph and therefore cannot see past it. When
a hybrid result looks wrong, check reachability before you touch alpha.

Two smaller details. The anchor is excluded from its own results. And a node
with **no embedding** is given the worst possible vector distance of 1.0, so if
you embed only some of your node types, the unembedded ones sink as you raise
alpha rather than being skipped.

There is no correct alpha. Start at 0.5, look at the results, and move toward 1 when you want meaning to dominate or toward 0 when you want closeness in the graph to dominate.

```python
client.close()
```

<details>
<summary>The same idea in R</summary>

The R client has the same three calls with the same arguments:
`client$vector_search(query, k)`, `client$hybrid_search(anchor, query, max_hops, k, alpha)`, and an `embedding` argument on `client$create_node()`. You produce the vectors by calling Ollama with `httr2`, as in the previous post. The scoring rule and the `max_hops` bound are properties of the server, so they behave identically.

</details>

## What's next

You can now store real embeddings, search by meaning across a whole store, and blend that with the shape of your graph.

So far you have written the descriptive text yourself. In the next post, **[Turning a Book Into a Knowledge Graph](./03-text-to-graph.md)**, you will take a full novel and build the graph automatically: pulling out characters, places, and events, linking them, and keeping a trail back to the passage each fact came from.
