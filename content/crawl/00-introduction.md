<!-- SEO subtitle (Medium meta description): Graph database and vector search fundamentals: key graph concepts, why they matter for AI, and a tour of the AstraeaDB ecosystem across R, Python, and Rust. -->

# Why Graphs, and Why Now: An Introduction to AstraeaDB

*Nodes, edges, and embeddings are the building blocks, and AstraeaDB is a database built to keep them together.*

Almost everything interesting about your data lives in the connections between
things: which customers bought which products, who cites whom in a research
paper, or which account sent money to which other account at 3 a.m. Yet most of
us store that connection-rich data in tables, then spend our careers fighting
the database to get the connections back out. This post is a gentle
introduction to graph databases, and to **AstraeaDB**, a database that pairs the
classic graph way of storing connections with a newer technique for finding
items by their meaning, called [vector search](../glossary.html#vector-search). There is no R or Python code here
yet, only the ideas, with the hands-on tutorials to follow.

## Tables are great, until you need relationships

The relational model, the familiar way of organizing data into tables of rows
and columns, is one of the best ideas in computing. It has a catch, though: it
stores relationships only indirectly. To connect two tables, you place a shared
value (called a foreign key) in each one, then match them up when you ask your
question, using an operation called a JOIN that stitches rows from different
tables together. A question like "who are my customers' customers?" forces you
to join a table to itself. A deeper one, such as "find every chain of purchases
connecting these two people, up to six steps apart," pushes you into long,
repetitive queries, or into exporting the data to another tool to analyze it.

The trouble is not that table-based databases cannot answer these questions, but
that relationships are an afterthought. Every question about connections costs a
JOIN, and deeper questions cost more of them.

## A graph stores relationships directly

A **graph** turns this around. It is built from just two kinds of pieces.

- **Nodes** (sometimes called vertices) are the things themselves, such as a
  person, a movie, a bank transaction, a gene, or a small software service.
- **Edges** are the relationships that connect those things, such as
  `ACTED_IN`, `PURCHASED`, `DEPENDS_ON`, or `SENT_MONEY_TO`. Each edge points in
  a direction and has a type, and, most importantly, it is stored as a real
  object rather than being figured out later.

Both nodes and edges can carry **properties**, which are simple pieces of
labeled information like a name, a year, or a weight. Nodes can also carry
**labels** that record what type of thing they are, such as `Person` or `Movie`.
That is the entire data model. Here is a tiny movie example described in words.

```
(Keanu Reeves:Person) --ACTED_IN--> (The Matrix:Movie) --IN_GENRE--> (Sci-Fi:Genre)
```

Because each edge is a real, stored object, following it from one node to the
next is fast. This step-by-step following is called traversing the graph, or a
[traversal](../glossary.html#traversal), and finding a node's immediate neighbors is a direct lookup, not a
table join. That one difference makes a whole class of questions easy to ask:

- **Recommendations** become a short walk across edges: "people who bought this
  also bought that" is two steps out from a product.
- **Social and professional networks** yield friends of friends, the shortest
  path between two people, or tightly connected communities.
- **Fraud and security** work surfaces rings of connected accounts, unusual
  chains of transactions, and how far a problem could spread.
- **Knowledge graphs** hold entities and how they relate, organized so software
  can reason over them.
- **Dependency maps** show which services break if this one goes down.

Many graph databases let you ask questions in a language designed for graphs.
One well-known example is Cypher, and a related standard is [GQL](../glossary.html#graph-query-language-gql), short for Graph
Query Language. Such languages let you describe the pattern you are looking for
almost as if you were drawing it:

```
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)-[:IN_GENRE]->(:Genre {name: "Sci-Fi"})
RETURN p.name, m.title
```

That query reads almost like the picture it matches, and that resemblance is
exactly the point.

## Adding AI: meaning can live in the graph too

Something important has changed in recent years. Modern artificial intelligence
can turn a piece of content into a list of numbers that captures its meaning.
Such a list is called a vector, and the vector produced for a specific item is
called its [embedding](../glossary.html#embedding). You can picture each embedding as a point in space, where
items with similar meaning sit close together and unrelated items sit far apart.
Once a movie's plot or a paragraph of text has been turned into an embedding,
you can find similar items by looking for the stored embeddings closest to it.
That ability powers semantic search, that is, search based on meaning rather
than exact keywords. It also powers a technique called retrieval-augmented
generation, or [RAG](../glossary.html#retrieval-augmented-generation-rag), which fetches relevant information first and then asks an AI
language model to write its answer using that information.

Until recently, using embeddings meant running a separate specialized system
called a vector database next to your graph or table-based database, plus extra
code to keep the two copies of your data in step. Yet questions about how your
data is connected and what it means are usually about the same things, so two
systems mean avoidable work and a risk that they drift out of sync.

A **vector-property graph** keeps both in one place. Every node can carry its
own embedding, stored right next to that node's edges and properties and
organized with a special index so the closest embeddings can be found quickly
even across millions of nodes. (An index is simply a supporting structure that
makes searching fast, like the index at the back of a book.) With everything in
one store, you can ask questions that neither a plain graph nor a plain vector
database handles well alone:

- You can search purely by meaning, for example asking for movies whose plots
  feel similar to a given one.
- You can combine both kinds of search at once, which is often called hybrid
  search: you might ask for movies that are both closely connected to a
  particular actor in the graph and similar in mood to a film you like.
- You can gather a small, relevant piece of the graph around a topic, hand it to
  an AI language model, and get an answer grounded in your own data. Combining
  graph retrieval with a language model this way is called **[GraphRAG](../glossary.html#graphrag)**.

## Meet AstraeaDB

**AstraeaDB** is a graph database written in the Rust programming language and
designed with these AI uses in mind. At its heart is the vector-property graph
described above: nodes with labels, edges with types, properties on both, and an
embedding on each node. Those embeddings are organized by an index called [HNSW](../glossary.html#hierarchical-navigable-small-world-hnsw),
short for Hierarchical Navigable Small World, a well-known method for finding
the closest embeddings quickly without checking every single one. Because the
connections and the embeddings share one store, following relationships and
searching by meaning happen side by side. Building on that foundation, AstraeaDB
offers several capabilities:

- **Graph traversals** let you explore outward from a node, find the shortest
  path between two nodes, or list a node's neighbors filtered by edge direction
  and type. Two common styles are breadth-first, which fans out one level at a
  time, and depth-first, which follows a single chain as far as it goes before
  backtracking.
- **Vector, hybrid, and semantic search** let you find the items whose
  embeddings are closest to a query, blend that closeness with graph connections
  using a dial you control, and follow walks guided by a chosen concept.
- **Graph algorithms run inside the server**, so heavy calculations happen where
  the data lives. They include PageRank, which scores how important each node is
  by how many important nodes point to it (the idea that originally ranked web
  pages); community detection, which groups nodes more connected to each other
  than to the rest; connected-components analysis, which finds separate clusters
  with no links between them; and centrality measures, which rank how
  influential each node is.
- **Temporal queries**, sometimes called time-travel queries, work because edges
  can record the span of time during which they were valid, so you can ask what
  the graph looked like as of an earlier date rather than only how it looks now.
- **GraphRAG** support lets you pull a relevant piece of the graph around a
  topic, turn it into plain text a language model can read, and answer questions
  with responses grounded in your own data.

## The ecosystem: one server, many front doors

AstraeaDB runs as a server that your program connects to. It understands several
communication methods, so you can pick the one that fits your setup:

- **JSON over TCP** sends data as plain text in a common format called JSON, over
  the standard internet connection called TCP. It needs no extra software and is
  the client libraries' default.
- **gRPC** is a fast, structured method with a strict message format, suited to
  production services.
- **Apache Arrow Flight** moves large tables with very little copying, which
  helps heavy analysis and pairs well with Python tools such as pandas and
  Polars.
- **MCP**, the Model Context Protocol, presents AstraeaDB as tools an AI
  assistant can call on its own, so an assistant like Claude can query your
  graph directly.

Surrounding the server is a growing collection of client libraries, small
packages that let you use AstraeaDB from a language you already know:

- For **R**, there is the
  [`AstraeaDB`](https://github.com/AstraeaDB/R-AstraeaDB) package. It is
  awaiting publication on CRAN, R's standard package repository, so for now you
  install it from GitHub. The R lessons show you how.
- For **Python**, there is the
  [`astraeadb`](https://pypi.org/project/astraeadb/) package on PyPI, Python's
  standard package repository.
- For **Go** and **Java**, there are full clients supporting the JSON, gRPC, and
  Arrow methods above.

Because AstraeaDB is open source, its core building blocks are also published as
Rust packages (which Rust calls crates) on
[crates.io](https://crates.io/crates/astraea-core), so a Rust program can build
the database engine in directly and run without a separate server.

## Where to go from here

To sum up: relationships are stored directly as data, embeddings sit right next
to them, and a single store can answer questions about structure, about meaning,
and about both at once, along with graph analytics, time-travel queries, and
GraphRAG.

The rest of this series is hands-on. Each language has its own three-part track
that builds the same small movie knowledge graph step by step, starting from a
first simple example and moving on to recommendations, graph algorithms, and
GraphRAG.

- For R, begin with [Getting Started with AstraeaDB in R](./r-01-getting-started.md).
- For Python, begin with [Getting Started with AstraeaDB in Python](./py-01-getting-started.md).

Choose the language you are most comfortable with, start a server, and work
through its track at your own pace.
