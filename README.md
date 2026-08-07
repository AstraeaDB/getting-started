# RAG template

Retrieval-Augmented Generation over a tiny document corpus, backed by
AstraeaDB as the vector + graph store. Minimal dependencies — Python 3
and a local ollama running `embeddinggemma`.

## Flow

```
just up                 # astraea-launcher start --profile single-node-server ...
just ingest             # embed corpus/ into AstraeaDB (one DocChunk per ~500 chars)
just query "your question"
just down               # stop the instance
```

## Status

Phase 3 skeleton. Real graph-RAG (subgraph extraction, LLM prompting via
`astraea-rag`) is deferred to Phase 5 when project subagents come online.
The current `query.py` performs vector-only retrieval and prints the
highest-scoring chunks.
