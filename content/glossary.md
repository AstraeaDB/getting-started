Every term the lessons use is defined here in ordinary words. A lesson links
here the first time it uses one of these, so nothing has to be explained twice
and nothing is assumed.

## Graph terms

### Graph

A collection of items and the connections between them. A social
network is a graph: the people are the items and the friendships are the
connections.

### Node

One item in a graph. A movie, a person, or a server is a node. Every
node has a whole number called an ID that you use to refer to it later.

### Edge

One connection between two nodes. An edge has a direction, so an
`ACTED_IN` edge that points from a person to a film means something different
from one pointing the other way.

### Label

A category name attached to a node, such as `Movie` or `Person`. A
node can carry more than one.

### Property

A named detail stored on a node or an edge, such as a title or a
year.

### Traversal

Following edges from one node to the next in order to reach nodes
further away.

### Breadth-first search (BFS)

A traversal that explores a graph one level at a
time: first everything one step from the start, then everything two steps away.
Use it when you want the nearest things first.

### Depth-first search (DFS)

A traversal that follows one path as far as it
goes before backing up and trying another. Use it when you want to reach far
parts of the graph quickly.

### Shortest path

The fewest edges that connect two nodes.

### Subgraph

A smaller piece cut out of a larger graph, usually everything
within a few steps of some starting node.

### Graph Query Language (GQL)

A written language for asking a graph database
questions, in the same way that SQL asks questions of a table-shaped database.

## Vector and search terms

### Vector

A list of numbers.

### Embedding

A vector that represents the meaning of something, such as a
sentence or an image, as a point in space, arranged so that things with similar
meanings sit close together. Comparing two embeddings is how a database judges
whether two things mean roughly the same thing.

### Dimension

How many numbers are in a vector. This site uses 768 throughout,
because that is what the `embeddinggemma` model produces.

### Cosine distance

One way of measuring how far apart two embeddings are.
Smaller means more similar.

### Vector search

Finding the stored items whose embeddings are closest to a
query embedding, which is how you search by meaning rather than by keyword.

### Hierarchical Navigable Small World (HNSW)

The structure AstraeaDB uses to
find nearby embeddings quickly without comparing the query against every stored
item.

### Hybrid search

Ranking results by combining two signals: how close items are
in the graph, and how similar their embeddings are.

## Language-model terms

### Large language model (LLM)

A program trained on a large amount of text that
can write an answer to a question posed in ordinary language.

### Retrieval-augmented generation (RAG)

Answering a question by first fetching
relevant material and then giving it to a language model, so the answer is based
on real source material rather than only on what the model absorbed in training.

### GraphRAG

Retrieval-augmented generation where the fetched material is a
subgraph rather than loose passages of text, so the model sees how facts relate
to each other and every claim can be traced back to a node.

### Linearization

Turning a subgraph into plain readable text so that a
language model can be given it as input.

## Practical terms

### Server

The database program running in the background, holding your data.

### Client

The library your own code uses to send requests to the server.

### Port

A numbered channel on a machine that a server listens on. AstraeaDB
uses `7687` by default, so the full local address is `127.0.0.1:7687`, where
`127.0.0.1` means this machine.

### Write-ahead log (WAL)

A file the server appends to before changing its main
data file, so that an interrupted write can be recovered rather than lost.
