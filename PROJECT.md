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

## Origin

Scaffolded from `templates/rag/` on 2026-08-07, then restructured by T1 on the
same day. The rag scaffold was the closest available starting point, not a
description of the project: `ingest.py`, `query.py`, and `corpus/` were deleted
and the directory now follows [`DESIGN.md`](DESIGN.md) section 3.1. Nothing of
the template's retrieval pipeline remains.

## Getting started

```bash
just build               # render content/ into docs/
just serve               # preview at http://127.0.0.1:8000
just verify crawl-py-01  # run one lesson's code blocks in a container
just verify-all          # run every lesson marked verify = "required"
just up / just down      # authoring AstraeaDB instance (not used by verify)
```

See [`README.md`](README.md) for the full layout and the toolchain notes.

## Where things stand

Design v1 is complete: 29 tasks in 6 phases, with the content inventory,
verification design, and open questions in [`DESIGN.md`](DESIGN.md). Phase 0
(T1 through T4) builds the toolchain and gates everything after it. No lesson
content has been ported yet.

Resolved so far: the site lives in a new public `AstraeaDB/getting-started`
published from `/docs` on `main` (Q6); embeddings are 768-dimensional, not
truncated to 128 (Q9); Medium is not a publication target (Q7); and
`astraea-cli` should reach crates.io, filed upstream as AstraeaDB issue #28
(Q2). Six questions remain open in DESIGN.md section 10, none of which block
Phase 0.
