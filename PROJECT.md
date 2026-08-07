# getting-started

A "Getting Started with AstraeaDB" HTML / GitHub Pages site that turns the
existing blog posts and the scattered demo repositories into one coherent,
tested learning path. Lessons are organized **Crawl → Walk → Run**. *Crawl*
carries the parallel Python and R getting-started tracks from `./blogs` so a
reader can choose their language. *Walk* introduces GraphRAG and semantic
similarity, consolidating and updating `astraea-graphrag-demo`,
`data_lake_demo`, and `astraeadb-embeddings-demo` into a single series of
lessons, and introduces Eunomia and A-llama. *Run* covers advanced
investigative use cases for fraud and cyber plus AI-assisted development,
drawing on `GNN-test-and-improve`, `cyber-graph-demo`, and `adb-claude-kit`.
Every code snippet and instruction is verified in an Apple container before
publication — the same approach used when the blogs were written — and all
lessons are reachable from a single `index.html` landing page.

See [`CONCEPT.md`](CONCEPT.md) for the original brief.

## Template

Scaffolded from `templates/rag/` on 2026-08-07. This project shows a
minimal retrieval-only RAG pipeline over a small corpus. Augment the
corpus under `corpus/`; tune the chunker in `ingest.py`.

## Getting started

```bash
just up                  # launch backing AstraeaDB
just ingest              # embed corpus/*.md into DocChunk nodes
just query "your q"      # vector search, prints top-k chunks
just down                # stop (data persists)
```

Real graph-RAG (subgraph extraction + LLM completion via `astraea-rag`)
is planned for Phase 5 when project subagents come online. For now,
`query.py` does vector-only retrieval.
