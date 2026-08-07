# Graph RAG

Retrieval-Augmented Generation (RAG) grounds a language model in a
corpus by fetching relevant passages at inference time and inserting them
into the prompt. Traditional RAG uses a pure vector index.

Graph RAG extends this by retrieving a *subgraph* — a seed node plus its
neighbourhood — rather than isolated passages. Because relationships are
preserved, the generated answer can cite paths through the graph, not
just disconnected chunks.

AstraeaDB's `astraea-rag` crate implements subgraph extraction with a
token budget, textual linearisation, and pluggable LLM providers. For
small corpora the simpler vector-only path often works well enough; the
graph structure pays off once the corpus gets denser and relationships
matter.
