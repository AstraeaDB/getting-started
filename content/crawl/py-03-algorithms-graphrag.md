<!-- SEO subtitle (Medium meta description): Advanced AstraeaDB in Python: PageRank and Louvain graph algorithms, temporal time-travel queries, GraphRAG for LLM-ready answers, and pandas integration. -->

# Graph Algorithms, Time-Travel, and GraphRAG with AstraeaDB in Python

*You can rank the most connected nodes, discover hidden communities, rewind the graph to a past date, and feed a small slice of it to a language model, all from Python.*

In [*Getting Started with AstraeaDB in Python*](./py-01-getting-started.md) we built a small movie knowledge graph, a set of records (nodes) joined by relationships (edges). In [*Vector and Hybrid Search with AstraeaDB in Python*](./py-02-vector-search.md) we turned it into a recommender using embeddings. This final post covers three features that a graph database is especially good at. The first is a set of graph algorithms that run inside the database itself. The second is temporal queries, which reconstruct what the graph looked like on an earlier date. The third is [GraphRAG](../glossary.html#graphrag), a technique for packaging a small slice of the graph as background for a language model. Everything here runs against a live `astraeadb serve` on the address `127.0.0.1:7687`.

## Rebuilding the graph

If you followed post 1, you already have this graph and can skip ahead. Otherwise, the block below rebuilds the whole thing at once. It adds a `Genre` layer now and, later in the post, `User` nodes for ratings.

```python
from astraeadb import AstraeaClient
from collections import defaultdict

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

genres = {g: client.create_node(["Genre"], {"name": g})
          for g in ["Action", "Sci-Fi", "Drama"]}

people = {p: client.create_node(["Person"], {"name": p})
          for p in ["Keanu Reeves", "Sandra Bullock", "Al Pacino",
                    "Lana Wachowski", "Christopher Nolan"]}

# (title, year, genres, actors, director)
movie_rows = [
    ("The Matrix", 1999, ["Sci-Fi", "Action"], ["Keanu Reeves"], "Lana Wachowski"),
    ("John Wick", 2014, ["Action"], ["Keanu Reeves"], None),
    ("Speed", 1994, ["Action"], ["Keanu Reeves", "Sandra Bullock"], None),
    ("The Lake House", 2006, ["Drama"], ["Keanu Reeves", "Sandra Bullock"], None),
    ("Heat", 1995, ["Action", "Drama"], ["Al Pacino"], None),
    ("Inception", 2010, ["Sci-Fi", "Action"], [], "Christopher Nolan"),
]

movies = {}
for title, year, gs, actors, director in movie_rows:
    mid = client.create_node(["Movie"], {"title": title, "year": year})
    movies[title] = mid
    for g in gs:
        client.create_edge(mid, genres[g], "IN_GENRE")
    for actor in actors:
        client.create_edge(people[actor], mid, "ACTED_IN")
    if director:
        client.create_edge(people[director], mid, "DIRECTED")
```

Notice that Keanu Reeves acts in four of the six movies. Keep him in mind, because the algorithms are about to notice him too.

## Who matters most? PageRank and centrality

PageRank is a scoring method first made famous by web search. It gives each node a score based not only on how many other nodes point to it, but on how important those pointing nodes are in turn. A node referenced by many well-connected nodes ends up with a high score. `run_pagerank` runs this same idea over your own graph. It returns a plain Python dictionary, a set of key-and-value pairs, that maps each node's identifier, given as a string, to its score. A higher score means the node sits closer to the center of all the connections. We can use it to find the most important nodes overall.

```python
scores = client.run_pagerank()   # {"12": 0.087, ...}

top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:5]
for nid, score in top:
    node = client.get_node(int(nid))
    name = node["properties"].get("name") or node["properties"].get("title")
    print(f"{name:16s} {score:.4f}")
```

Keanu Reeves and the genres his movies belong to rise to the top, because many connections pass through them. `run_pagerank` also accepts `damping`, `max_iterations`, and `tolerance` if you want to adjust how the calculation settles on its final numbers, plus an optional `nodes=[...]` list to score only a subset of the graph.

A simpler and faster measure is degree centrality. Centrality is any measure of how important a node is, and the degree version simply counts how many connections a node has. `run_degree_centrality` returns the same `{node_id: score}` shape and takes a `direction` of `"outgoing"`, `"incoming"`, or `"both"`.

```python
deg = client.run_degree_centrality(direction="both")
busiest = max(deg, key=deg.get)
print("Most connected node:", client.get_node(int(busiest))["properties"])
```

PageRank rewards being connected to other well-connected nodes, while degree centrality only counts connections. When the two measures disagree about a node, that difference is often worth investigating. There is also `run_betweenness_centrality`, which finds nodes that sit on many of the shortest paths between other nodes. Those nodes act as bridges between otherwise separate parts of the graph.

## Communities without labels: Louvain

We labeled the genres by hand. Could the graph discover those clusters on its own? The `run_louvain` method does exactly that. Louvain community detection is an algorithm that automatically groups nodes into communities, where a community is a set of nodes with many connections among themselves and fewer connections to the rest of the graph. It returns a dictionary with two keys: `communities`, which maps each node's identifier to a community number, and `num_communities`, the total count.

```python
result = client.run_louvain()
print(f"{result['num_communities']} communities detected")

groups = defaultdict(list)
for nid, community in result["communities"].items():
    node = client.get_node(int(nid))
    props = node["properties"]
    groups[community].append(props.get("title") or props.get("name"))

for community, members in groups.items():
    print(f"Community {community}: {members}")
```

The communities tend to echo the genre structure we built by hand. Action movies and the actors they share group together, and dramas gather elsewhere. This is the useful part. On a real dataset where nobody has labeled anything in advance, Louvain finds the hidden groupings for you.

## Time-travel: the graph as of a past date

This next feature is one that sets AstraeaDB apart. Each edge can carry a `valid_from` timestamp, recorded as the number of milliseconds since the start of 1970, a common way for computers to represent a moment in time. Temporal queries, sometimes called time-travel queries, let you ask what the graph looked like at any past moment. We will add `User` nodes and `RATED` edges that come into existence on specific dates.

```python
from datetime import datetime, timezone

def ms(year, month, day):
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)

alice = client.create_node(["User"], {"name": "Alice"})
bob = client.create_node(["User"], {"name": "Bob"})

client.create_edge(alice, movies["The Matrix"], "RATED",
                   properties={"rating": 5}, valid_from=ms(2020, 1, 1))
client.create_edge(alice, movies["John Wick"], "RATED",
                   properties={"rating": 4}, valid_from=ms(2023, 6, 1))
client.create_edge(bob, movies["The Matrix"], "RATED",
                   properties={"rating": 4}, valid_from=ms(2024, 2, 1))
```

Who had rated *The Matrix* as of the start of 2021? Only Alice, because Bob's rating does not exist yet on that timeline. The `neighbors_at` method answers this by ignoring any edge whose `valid_from` is later than the timestamp you pass in. It returns a list of `{node_id, edge_id}` dictionaries.

```python
as_of_2021 = ms(2021, 1, 1)
raters = client.neighbors_at(movies["The Matrix"], "incoming", as_of_2021)
for r in raters:
    print(client.get_node(r["node_id"])["properties"]["name"], "had rated it")
# -> Alice had rated it
```

Run the same call with `ms(2024, 6, 1)` and Bob appears too. The `bfs_at` method applies the same time filter to a full [traversal](../glossary.html#traversal), which means following connections outward from a starting node step by step. The code below finds everything reachable from Alice as of early 2021.

```python
reachable = client.bfs_at(alice, max_depth=2, timestamp=as_of_2021)
for entry in reachable:
    print("depth", entry["depth"], client.get_node(entry["node_id"])["properties"])
```

As of that date, Alice reaches *The Matrix* and its genres but not *John Wick*, which she will not rate until 2023. You do not need to save separate snapshots or keep a separate history table, because the past is stored directly in the graph. The methods `dfs_at` and `shortest_path_at` round out the set of temporal tools.

## Zooming in: subgraphs and stats

Before we hand any context to a language model, here are two helper methods. `graph_stats` gives a high-level count of everything in the store, and `get_subgraph` pulls out the raw nodes and edges around a center node so you can inspect them or draw them. A [subgraph](../glossary.html#subgraph) is simply a small slice of the larger graph: a chosen node together with its nearby neighbors and the connections among them.

```python
stats = client.graph_stats()
print("nodes:", stats["total_nodes"], "edges:", stats["total_edges"])

sub = client.get_subgraph(movies["The Matrix"], hops=2, max_nodes=50)
print("subgraph:", len(sub["nodes"]), "nodes,", len(sub["edges"]), "edges")
```

## From graph to prompt: GraphRAG

GraphRAG builds on an idea called retrieval-augmented generation, usually shortened to [RAG](../glossary.html#retrieval-augmented-generation-rag). The idea is to answer a question by first fetching relevant information and then handing it to a language model, also known as a large language model or [LLM](../glossary.html#large-language-model-llm), so the model can base its answer on real data rather than only on its training. In ordinary RAG, the fetched information is a set of text passages. In GraphRAG, it is a subgraph instead, so the model sees how things are related rather than a handful of disconnected snippets. AstraeaDB builds this in two steps, and the first step needs no language model at all.

The `extract_subgraph` method walks outward from a center node and turns the result into plain text, flattening the nodes and connections into readable lines. It returns `{nodes_count, edges_count, estimated_tokens, text}`. That text is the exact context that would be sent to a model, so you can print it and inspect it at no cost.

```python
context = client.extract_subgraph(movies["The Matrix"], hops=2, format="structured")
print(context["nodes_count"], "nodes,", context["edges_count"], "edges")
print(context["text"])
```

The `format` argument also accepts `"prose"`, `"triples"`, or `"json"` if you prefer a different layout for that text. Once the context looks right, the `graph_rag` method does the same retrieval and packages it together with your question, returning `{question, context, nodes_in_context, edges_in_context, estimated_tokens, anchor_node_id, note}`.

```python
result = client.graph_rag(
    question="Which action movies star Keanu Reeves?",
    anchor=people["Keanu Reeves"],
    hops=2,
)
print(result["nodes_in_context"], "nodes in context")
print("(context used ~", result["estimated_tokens"], "tokens)")
print(result["note"])
```

Writing the final answer needs a language model, and that has to be configured
on the server, for example a local Ollama installation or an API key set in the
server's configuration. Until you configure one, the call still succeeds and
still does the retrieval: you get the assembled context, the counts, and a
`note` reading "LLM completion requires server-side provider configuration. Use
the context with your own LLM." That is a useful way to work, because you can
build and test the whole retrieval pipeline, and check exactly what the model
would see, before connecting a model at all. Once a provider is configured, the
same call also returns the generated answer.

## A quick pandas detour

Graph results are often the starting point for an analysis you will finish in pandas, a popular Python library for working with tables of data. Its main structure is the DataFrame, which is a table of rows and columns much like a spreadsheet. The client ships optional DataFrame helpers, which you install with `pip install "astraeadb[pandas]"`.

```python
from astraeadb.dataframe import export_nodes_df

movie_ids = client.find_by_label("Movie")
df = export_nodes_df(client, movie_ids)   # node_id, labels, + flattened properties
print(df.sort_values("year")[["title", "year"]])
```

You can also build a DataFrame directly from a [GQL](../glossary.html#graph-query-language-gql) query, GQL being the graph query language used to ask the database questions. The `query_dict` method always returns a plain `{columns, rows}` dictionary, which loads straight into pandas.

```python
import pandas as pd

res = client.query_dict("MATCH (m:Movie) RETURN m.title, m.year")
frame = pd.DataFrame(res["rows"], columns=res["columns"])
print(frame)

client.close()
```

From here it is ordinary pandas work. You can join PageRank scores onto the table, group ratings by year, or export the results to a CSV file.

## Wrapping up the series

Across three posts we went from an empty database to a capable system, all in Python and all against the same small movie graph. Post 1 covered nodes, edges, traversals, and the GQL query language. Post 2 added embeddings, which are numeric representations of meaning, for vector, hybrid, and semantic search, giving us a recommender in a few dozen lines. This post added algorithms that run inside the server (PageRank, Louvain, and centrality), time-travel queries that reconstruct the graph at any past moment, and GraphRAG, which turns relationships into context a language model can use.

The common thread is that AstraeaDB keeps graph structure, vector similarity, temporal history, and retrieval in a single store, so you do not have to stitch together four separate systems to build one intelligent application. With these three posts, you have seen the full set of tools. You can now point them at your own data and see what the graph reveals.

*Everything shown in these posts is real, runnable API, so you can try each example against your own AstraeaDB instance.*
