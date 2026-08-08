<!-- SEO subtitle (Medium meta description): A hands-on AstraeaDB tutorial in Python: pip install the graph and vector database client, build a knowledge graph, and run BFS, shortest path, and GQL queries. -->

# Getting Started with AstraeaDB in Python: A Graph + Vector Database in Minutes

*Set up a graph database written in Rust, connect to it from Python, and build your first knowledge graph in one session.*

Many databases force a trade-off. Some are good at storing the relationships between things, while others are good at finding items by meaning rather than by exact keywords. AstraeaDB, written in the Rust programming language, does both at once. It stores your data as a graph, which is a network of items and the connections between them, and it can also attach a list of numbers, called an embedding, to any item so it can find items with a similar meaning. This design is called a Vector-Property Graph: every item and connection can hold ordinary details, such as a name or a year, and can also carry one of those number lists for similarity search. In this post you will install the server, connect from Python, and build a small movie knowledge graph you can query. Embeddings come in the second post, so here the focus is on the graph basics.

## What AstraeaDB actually is

You can picture AstraeaDB as a labeled graph. The items in it are called nodes, and the connections between them are called edges. A node usually stands for a thing, such as a movie or a person, and an edge stands for a relationship, such as one person acting in one movie. Each node carries one or more labels, which are just category names like `Movie` or `Person`. Nodes and edges can also hold properties, the named details you choose: a `Movie` node might have a title and a year, while an `ACTED_IN` edge connects a `Person` node to a `Movie` node. Every node and edge is given a whole number called an ID, which you use to refer to it later. Nodes can also carry an embedding for similarity search, but that feature waits for the second post.

## Setting up the server

The Python client is a small library that sends your requests to a running AstraeaDB server. The server is the database program running in the background, and the client is the code in your program that talks to it. On your own computer they communicate at the address `127.0.0.1:7687`, where `127.0.0.1` means this machine and `7687` is the port, a numbered channel the server listens on. The first step is to get the server running. Because AstraeaDB is written in Rust, you need Rust's build tools, which you can get from [rustup.rs](https://rustup.rs) if you do not already have them. Building the server also relies on Protocol Buffers, a data format from Google, so on a fresh Linux machine you first need a few system packages. On Debian or Ubuntu, one command installs all of them:

```bash
sudo apt-get install -y protobuf-compiler libprotobuf-dev pkg-config libssl-dev build-essential
```

On macOS with [Homebrew](https://brew.sh), the equivalent is `brew install protobuf`. With those in place, you can install the command-line program using `cargo`, which is Rust's package and build tool:

```bash
# Installs the `astraeadb` binary (compiles from source; takes a few minutes)
cargo install --git https://github.com/AstraeaDB/AstraeaDB-Official.git astraea-cli

# Start the server (JSON/TCP on 127.0.0.1:7687, data persisted to disk)
astraeadb serve
```

Leave `astraeadb serve` running in this terminal window, and open a second window for your Python work. A few other commands are worth knowing:

```bash
astraeadb status              # quick health check
astraeadb shell               # interactive REPL
astraeadb serve --port 7700   # run on a different port
```

## Installing the Python client

In your second terminal window, install the client from PyPI, the Python Package Index, which is the standard online catalog of Python libraries:

```bash
pip install astraeadb
# or, to add pandas + Arrow Flight support:
pip install "astraeadb[all]"
```

The base package installs quickly because it does not rely on any large extra libraries. The optional extras shown above add data-science conveniences that later posts use, so you can skip them for now.

## Connecting

The simplest way to connect uses Python's `with` statement. When you open a `with` block, `AstraeaClient` connects to the server automatically, and when the block ends, it closes the connection for you, so you never leave one open by accident:

```python
from astraeadb import AstraeaClient

with AstraeaClient(host="127.0.0.1", port=7687) as client:
    print(client.graph_stats())   # a quick "are we talking?" check
```

If that call prints a dictionary of statistics rather than a connection error, everything is working. A dictionary is Python's name for a collection of key-and-value pairs. `AstraeaClient` automatically chooses the best way to send data to the server. Two more specific clients exist if you ever need them: `JsonClient`, which uses a plain text format, and `ArrowClient`, which uses a faster format for large tables and needs the `pyarrow` library. For this tutorial, the default `AstraeaClient` is the right choice.

## Building a movie knowledge graph

Now you will fill a small graph with a few movies, the people who made them, and their genres. The graph uses three kinds of nodes, labeled `Movie`, `Person`, and `Genre`, joined by three kinds of edges: `ACTED_IN`, `DIRECTED`, and `IN_GENRE`.

The `create_node(labels, properties)` method returns the new node's ID as a whole number. The code below stores those IDs in dictionaries so it can connect edges by looking up nodes by name:

```python
from astraeadb import AstraeaClient

with AstraeaClient(host="127.0.0.1", port=7687) as client:
    # --- People (actors and directors) ---
    people = {}
    for name in ["Keanu Reeves", "Carrie-Anne Moss", "Laurence Fishburne",
                 "Sandra Bullock", "Lana Wachowski", "Chad Stahelski"]:
        people[name] = client.create_node(["Person"], {"name": name})

    # --- Movies ---
    movies = {}
    for title, year, plot in [
        ("The Matrix",          1999, "A hacker discovers reality is a simulation."),
        ("The Matrix Reloaded", 2003, "Neo fights on to free humankind."),
        ("John Wick",           2014, "A retired hitman comes back for revenge."),
        ("Speed",               1994, "A bus wired to explode if it slows down."),
    ]:
        movies[title] = client.create_node(
            ["Movie"], {"title": title, "year": year, "plot": plot})

    # --- Genres ---
    genres = {}
    for name in ["Science Fiction", "Action"]:
        genres[name] = client.create_node(["Genre"], {"name": name})

    # --- Edges: source, target, type ---
    for actor, film in [
        ("Keanu Reeves", "The Matrix"), ("Keanu Reeves", "The Matrix Reloaded"),
        ("Keanu Reeves", "John Wick"),  ("Keanu Reeves", "Speed"),
        ("Carrie-Anne Moss", "The Matrix"), ("Carrie-Anne Moss", "The Matrix Reloaded"),
        ("Laurence Fishburne", "The Matrix"), ("Laurence Fishburne", "The Matrix Reloaded"),
        ("Sandra Bullock", "Speed"),
    ]:
        client.create_edge(people[actor], movies[film], "ACTED_IN")

    for director, film in [
        ("Lana Wachowski", "The Matrix"), ("Lana Wachowski", "The Matrix Reloaded"),
        ("Chad Stahelski", "John Wick"),
    ]:
        client.create_edge(people[director], movies[film], "DIRECTED")

    for film, genre in [
        ("The Matrix", "Science Fiction"), ("The Matrix", "Action"),
        ("The Matrix Reloaded", "Science Fiction"), ("The Matrix Reloaded", "Action"),
        ("John Wick", "Action"), ("Speed", "Action"),
    ]:
        client.create_edge(movies[film], genres[genre], "IN_GENRE")
```

That code creates twelve nodes and eighteen edges, small enough to follow by hand. Edges have a direction: an `ACTED_IN` edge points from a person to a movie, and that direction matters when you read the graph back.

## Reading it back

The remaining examples assume you are still inside that same `with` block. Start by reading a single node. The `get_node(id)` method returns a dictionary containing the node's `labels` and `properties`:

```python
matrix = movies["The Matrix"]
print(client.get_node(matrix))
# {'id': 7, 'labels': ['Movie'],
#  'properties': {'title': 'The Matrix', 'year': 1999, 'plot': '...'}}
```

To move from one node to the nodes connected to it, use the `neighbors(id, direction, edge_type)` method. Because `ACTED_IN` edges point into the movie, you find the cast by asking for the incoming neighbors, the nodes whose edges point toward this one. Each result is a dictionary of the form `{node_id, edge_id}`:

```python
for n in client.neighbors(matrix, direction="incoming", edge_type="ACTED_IN"):
    person = client.get_node(n["node_id"])
    print(person["properties"]["name"])
# Keanu Reeves / Carrie-Anne Moss / Laurence Fishburne
```

To collect every node of one kind, the `find_by_label` method returns a simple list of IDs:

```python
print(client.find_by_label("Movie"))   # [7, 8, 9, 10]
```

## Walking the graph

Reading one connection at a time is useful, but the real strength of a graph database is following many connections in a row, which is called traversal. The `bfs(start, max_depth)` method performs a breadth-first search, abbreviated BFS. It explores the graph one level at a time: first every node one step from the start, then every node two steps away, and so on. It returns dictionaries of the form `{node_id, depth}`, where `depth` is how many steps a node sits from the start:

```python
keanu = people["Keanu Reeves"]
for hop in client.bfs(keanu, max_depth=2):
    props = client.get_node(hop["node_id"])["properties"]
    print(hop["depth"], props)
# depth 1: the movies Keanu is in; depth 2: their genres and co-stars
```

The `dfs(start, max_depth)` method does a similar walk using depth-first search, abbreviated DFS. Instead of fanning out level by level, it follows one path as far as it can before backing up to try another, and it returns the node IDs in the order it visited them:

```python
print(client.dfs(keanu, max_depth=2))   # [11, 7, 1, ...]
```

When you want the link between two specific nodes, the `shortest_path` method finds the fewest steps between them. For example, you might ask how Keanu Reeves connects to the Science Fiction genre. The answer runs through one of his movies:

```python
path = client.shortest_path(keanu, genres["Science Fiction"])
print(path)   # {'path': [11, 7, 5], 'length': 2}
```

The `path` value is a list of node IDs, and `length` is the number of steps. Here there are two steps: from Keanu Reeves to one of his movies, and from that movie to Science Fiction.

## Asking questions with a query language

For questions you make up as you go, AstraeaDB understands a graph query language, abbreviated GQL. A query language lets you describe the pattern of data you want and have the database find every match, rather than writing step-by-step method calls. AstraeaDB's version reads much like Cypher, a popular query language used by other graph databases. The `query()` method returns a dictionary with `columns` and `rows`, which fits neatly into a table:

```python
result = client.query(
    "MATCH (p:Person)-[:ACTED_IN]->(m:Movie) "
    "RETURN p.name, m.title, m.year"
)
print(result["columns"])       # ['p.name', 'm.title', 'm.year']
for row in result["rows"]:
    print(row)                 # ['Keanu Reeves', 'The Matrix', 1999], ...
```

This is the same graph you built earlier, now described as a query instead of a series of method calls. Use whichever approach suits your task.

## Taking stock

Finally, the `graph_stats()` method gives an overview of the whole graph, including total counts and a breakdown by label:

```python
print(client.graph_stats())
# {'total_nodes': 12, 'total_edges': 18, 'labels': {...}, ...}
```

That is twelve nodes and eighteen edges, exactly what you inserted.

## What's next

You now have a running AstraeaDB server, a working Python connection, and a small but complete knowledge graph that you can create, read, walk through, and query. That covers the graph half of a graph and vector database.

The other half is where the database puts those embeddings to work. In the next post, **[Vector and Hybrid Search with AstraeaDB in Python](./py-02-vector-search.md)**, you will attach an embedding to each movie's plot and use `vector_search` to find films whose descriptions are closest in meaning to a phrase you provide. You will then combine two signals, how close nodes are in the graph and how similar their embeddings are, using `hybrid_search`, to build a simple recommendation engine. Keep your server running, and the next post will continue from this same graph.
