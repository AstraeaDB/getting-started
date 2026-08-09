# getting-started: Design

> Status: **design v1** (2026-08-07). Produced by the `architect` agent from
> [`CONCEPT.md`](./CONCEPT.md) (the authoritative brief) and
> [`PROJECT.md`](./PROJECT.md), against the AstraeaDB knowledge graph and a
> direct audit of the six demo repositories named in the brief.
>
> This is a **content and documentation project**. The deliverable is a static
> site plus a set of code samples that are proven to run. AstraeaDB crate
> analysis appears here only to answer two questions: which public APIs each
> lesson must teach, and whether the existing demo code still works against the
> current API surface.
>
> **All site prose is bound by [`../../blogs/STYLE.md`](../../blogs/STYLE.md).**
> The five rules (no em-dashes, no sentence fragments, warm but not familiar,
> no unexplained jargon, explain concepts before showing code) are acceptance
> criteria on every content task below, not suggestions. This design document
> follows the em-dash rule itself so that it models the house voice.

---

## 1. Goal and non-goals

### Goal

Build a public "Getting Started with AstraeaDB" site, served from GitHub Pages,
that takes a reader who has never used a graph database from installing the
server to running a fraud or cyber investigation. The path is ordered
**Crawl, then Walk, then Run**. Crawl carries the seven existing blog posts,
with Python and R as parallel tracks so a reader picks a language once and stays
in it. Walk consolidates three scattered demo repositories into one coherent
lesson series on embeddings, semantic search, and GraphRAG, and introduces
Eunomia and a-llama. Run covers investigative work on fraud and cyber graphs and
AI-assisted development. Every instruction and every code snippet is executed in
an Apple container before publication, and every lesson is reachable from a
single `index.html`.

### Non-goals

- **Not a Rust crate.** No new AstraeaDB crate, no new client library. If a
  lesson needs an API that does not exist, that becomes an issue against
  AstraeaDB, not new code in this project.
- **Not an API reference.** The site teaches by worked example. Exhaustive
  method listings belong in the client packages' own documentation.
- **Not a replacement for the demo repositories.** The site consolidates and
  supersedes their *narrative*; the repositories remain the home of large or
  license-encumbered data and of code too long to inline in a lesson.
- **Not a rewrite of AstraeaDB.** Where a demo no longer compiles against the
  current API, the fix goes in the demo or the lesson, unless the audit finds a
  genuine server bug, which is filed in `astraeadb-issues.md`.
- **Not a marketing site.** There is a `marketing/` directory in this dev
  environment for that. This site is instructional.

---

## 2. What already exists, and the two mismatches to resolve

### 2.1 The rag scaffold is the wrong scaffold

`projects/getting-started/` was created from `templates/rag/` on 2026-08-07. It
therefore contains a retrieval-only RAG pipeline (`ingest.py`, `query.py`,
`corpus/01-graphs.md`, `corpus/02-vector-search.md`, `corpus/03-graph-rag.md`,
`justfile`, `astraea-config/default.toml`) and a running AstraeaDB instance
named `getting-started-instance` on TCP 50102 and gRPC 50103. There is no
static-site scaffolding at all.

**Verdict, stated plainly:**

| Scaffold artifact | Disposition | Reason |
| --- | --- | --- |
| `ingest.py` | **Delete** | Its job (chunk markdown, embed, create `DocChunk` nodes) is done better and with a real corpus by `astraea-graphrag-demo`, which builds a 229-node, 317-edge graph from a novel. Keeping both would ship two competing RAG examples and confuse the Walk tier. |
| `query.py` | **Delete** | Retrieval-only vector search over three files. Crawl lesson `crawl-py-02` already teaches `vector_search` properly, and Walk teaches the real pipeline. |
| `corpus/*.md` | **Delete** | Three placeholder documents. The Walk tier uses *A Tale of Two Cities*, which the reader can actually reason about. |
| `justfile` | **Rewrite in place** | Keep the file, replace every recipe. The new recipes are `build`, `serve`, `verify`, `verify-all`, `images`, `clean`. |
| `astraea-config/default.toml` | **Rewrite in place** | Keep the launcher profile binding, rename the instance to `getting-started-authoring`. |
| `getting-started-instance` (running server, TCP 50102) | **Keep, rename** | This is the **authoring server**. `STYLE.md` requires that claimed outputs be verified against a live server, and lesson authors need one they can poke at while writing. It is explicitly *not* the verification server; verification always runs a fresh server inside a container. |
| `PROJECT.md` template section | **Rewrite** | It currently describes the rag template. |

### 2.2 The existing blog HTML is a Medium artifact, not a website

Every `.html` file in `blogs/` is roughly 635 KB. Inspection shows
`<meta name="generator" content="pandoc">` plus the R Markdown `html_document`
boilerplate, an inlined jQuery 3.6.0, and inlined Bootstrap. These were produced
by pandoc in self-contained mode, which is exactly right for pasting into
Medium (`blogs/README.md` calls the series "Medium-ready" and tells you to swap
the relative links for Medium URLs before posting) and exactly wrong for a
multi-lesson website: there is no shared navigation, no shared stylesheet, and
each page ships its own copy of two JavaScript libraries.

**Verdict:** keep pandoc as the house converter, because it is already the tool
that produced every existing page and because `pandoc 3.9` is installed at
`/opt/homebrew/bin/pandoc`. Change only the invocation. The site build uses
`--standalone` with a project template and one shared stylesheet, not
`--embed-resources --standalone`. The self-contained Medium exports become a
separate, optional output (see section 8 and open question Q7).

Two further findings on the existing HTML:

- `r-02-vector-search.html` and `r-03-algorithms-graphrag.html` are dated
  2026-08-02, but their `.md` sources were rewritten on 2026-08-05 by commit
  `701fc01` ("editorial rewrite for clarity and style"). **Those two exports are
  stale** and do not reflect the current prose.
- `py-02-vector-search.md`, `py-03-algorithms-graphrag.md`, and
  `ui-explore-your-graph.md` have **no export at all**. The Python track is
  therefore not at parity with R in the Medium artifacts. For the *site* this
  gap closes automatically, because the build renders every lesson from
  markdown. Medium is dropped (Q7), so this is not a gap at all.

### 2.3 Package availability, checked today

These facts change what the install instructions can honestly say, and they were
verified against the live registries on 2026-08-07.

| Artifact | Status | Consequence |
| --- | --- | --- |
| `astraea-core`, `astraea-graph`, `astraea-vector`, `astraea-storage`, `astraea-rag` | on crates.io at **0.3.1** | Rust library lessons can use plain version dependencies. |
| `astraea-cli`, `astraea-server`, `astraea-algorithms`, `astraea-query`, `astraea-gnn`, `astraea-mcp` | **not published** | The server must be installed with `cargo install --git https://github.com/AstraeaDB/AstraeaDB-Official.git astraea-cli`, a multi-minute source build. The GNN lesson needs a git dependency. See Q2. |
| `astraeadb` on PyPI | **0.1.1**, live | `pip install astraeadb` works as written in `py-01`. |
| `AstraeaDB` on CRAN | **404, not published** | `blogs/r-01-getting-started.md` line 65 tells the reader `install.packages("AstraeaDB")`, and `blogs/README.md` links the CRAN page. **Both are broken today.** The fallback on line 74, `remotes::install_github("AstraeaDB/R-AstraeaDB")`, does work. See Q1. |

---

## 3. Site architecture

### 3.1 Repository and file layout

```
getting-started/
  README.md                 what this repo is, how to build it, how to verify it
  PROJECT.md CONCEPT.md DESIGN.md   planning artifacts, not published
  LICENSE
  lessons.toml              THE manifest: every lesson's id, title, tier, track,
                            order, sibling, source, and verification policy
  content/
    index.md                landing-page prose only; the lesson lists are generated
    crawl/  00-introduction.md
            py-01-getting-started.md  py-02-vector-search.md  py-03-algorithms-graphrag.md
            r-01-getting-started.md   r-02-vector-search.md   r-03-algorithms-graphrag.md
            08-ui-explore-your-graph.md
    walk/   01-embeddings.md 02-semantic-search.md 03-text-to-graph.md
            04-graphrag.md 05-data-lake.md 06-eunomia.md 07-a-llama.md
    run/    01-fraud-elliptic.md 02-cyber-build.md 03-cyber-hunt.md
            04-cyber-report.md 05-ai-assisted-dev.md
    _shared/                language-neutral prose fragments, included at build time
            install-server.md  what-is-an-embedding.md  what-is-graphrag.md
            ollama-setup.md    glossary.md
  samples/                  runnable code per lesson, extracted and kept in sync
    walk-03-text-to-graph/  run-01-fraud-elliptic/  ...
  data/                     small, redistributable sampled datasets (see Q4)
  site/
    build.py                stdlib-only pandoc driver and index generator
    templates/lesson.html   pandoc template: nav, track switcher, prev/next, verified stamp
    templates/index.html    landing page template
    templates/status.html   verification dashboard template
    assets/site.css  assets/site.js  assets/logo.svg
  verify/
    Dockerfile.base         Debian bookworm + build deps + rustup + astraeadb binary
    Dockerfile.py  Dockerfile.r  Dockerfile.rust
    extract.py  run.py  normalize.py
    report.json             generated; consumed by build.py
  docs/                     GENERATED OUTPUT. GitHub Pages serves this directory.
    .nojekyll  index.html  status.html  crawl/*.html  walk/*.html  run/*.html
    assets/*  samples/*  data/*
  justfile
```

`docs/` is committed. GitHub Pages is configured to serve the `main` branch,
`/docs` folder. This needs no GitHub Action to publish, which keeps the first
release simple; an Action that runs `just build` and `just verify-all` on push
is a later hardening step (T30).

### 3.2 URL layout

| URL | Page |
| --- | --- |
| `/` | landing page |
| `/crawl/00-introduction.html` | tier-opening, language-agnostic |
| `/crawl/py-01-getting-started.html` | Python track |
| `/crawl/r-01-getting-started.html` | R track |
| `/walk/04-graphrag.html` | Walk lesson |
| `/run/01-fraud-elliptic.html` | Run lesson |
| `/status.html` | verification dashboard |
| `/samples/walk-03-text-to-graph/` | downloadable sample code |

The path mirrors `content/`, so a lesson's source file and its URL are trivially
derivable from each other. `build.py` enforces that.

### 3.3 Navigation model

Three navigation surfaces, all generated from `lessons.toml`:

1. **A persistent sidebar** listing the three tiers and their lessons, with the
   current lesson marked. Inside Crawl, lessons carry a `track` of `py`, `r`, or
   `both`.
2. **A track switcher** in the header, offering Python and R. Choosing one sets
   `localStorage.astraeaTrack` and hides the other track's sidebar entries. When
   the current page has a sibling in the other track, the switcher navigates to
   that sibling rather than to the landing page, so a reader can change their
   mind on lesson two and land on lesson two.
3. **Prev and next links** at the foot of every lesson, computed within the
   reader's chosen track so the Python reader never lands on an R page by
   accident.

The switcher is roughly forty lines of vanilla JavaScript in `assets/site.js`.
There is no framework and no build step beyond pandoc. With JavaScript disabled
the sidebar shows both tracks and every link still resolves, which matters
because GitHub Pages readers include people behind restrictive browsers.

`build.py` writes the sibling relationship into each page as a
`<link rel="alternate" data-track="r" href="...">`, taken from the `sibling`
field in `lessons.toml`. The JavaScript reads it; it does not guess from
filenames.

### 3.4 Sharing prose across the two tracks without duplicating it

The Python and R getting-started posts today repeat, nearly verbatim, the
server-install section, the explanation of what a graph is, and the explanation
of what an embedding is. Two copies drift. The rule for the site is:

- **Language-neutral prose lives once**, in `content/_shared/*.md`, and is
  pulled into a lesson with a single directive line:
  `<!-- include: _shared/install-server.md -->`. `build.py` expands these before
  handing the file to pandoc, so pandoc still sees one flat markdown document
  and heading levels stay correct.
- **A fragment may not contain a language-specific code fence.** A fragment may
  contain `bash`, because both tracks install the same server the same way. It
  may not contain `python` or `r`. `build.py` fails the build if it finds one,
  which stops the rule from eroding.
- **Everything else stays in the track file**, including all narrative that
  refers to a language's idioms.

Four fragments carry most of the shared weight: `install-server.md` (the
protobuf prerequisites and the `cargo install --git` line), `ollama-setup.md`
(installing Ollama and pulling `embeddinggemma`), `what-is-an-embedding.md`, and
`what-is-graphrag.md`. `glossary.md` renders as its own page and every lesson
links to it on first use of a term, which is how the site satisfies STYLE.md
rule 4 without redefining "HNSW" in nine places.

### 3.5 How `index.html` is organized

Generated by `build.py` from `content/index.md` plus `lessons.toml`, in this
order down the page:

1. **A hero**, two sentences: one saying what AstraeaDB is in plain words, one
   saying what a reader can do after finishing the path.
2. **A "choose your language" control**, Python or R, which sets the track
   preference before the reader enters Crawl. A third option, "show me both,"
   leaves the preference unset.
3. **Three tier cards**, each with a short paragraph on what the reader will be
   able to do after that tier, an estimated time, the prerequisites, and the
   generated lesson list filtered by the chosen track.
4. **A verification strip**: "Every lesson on this site was last run against
   AstraeaDB `<rev>` on `<date>`," linking to `/status.html`.
5. **A footer** with the repository link, the license, and a link to the writing
   style guide, because the site is meant to be contributed to.

The lesson lists on the landing page are generated, never hand-maintained. A
lesson that is not in `lessons.toml` does not exist, and a lesson in
`lessons.toml` that has no content file fails the build. That invariant is what
makes "all lessons reachable from index.html," which CONCEPT.md asks for,
structurally true rather than a thing someone has to remember.

---

## 4. Content inventory

Twenty lessons. "Track" is `py`, `r`, or `both`. "Status" describes the work
needed, not the eventual state.

### Crawl (8 lessons)

| ID | Title | Track | Source | Status |
| --- | --- | --- | --- | --- |
| `crawl-00-intro` | Why Graphs, and Why Now: An Introduction to AstraeaDB | both | `blogs/00-introduction.md` | **Exists.** Port, add front matter, no rewrite expected. |
| `crawl-py-01` | Getting Started with AstraeaDB in Python | py | `blogs/py-01-getting-started.md` | **Exists.** Port, factor out `_shared/install-server.md`, re-verify. |
| `crawl-py-02` | Vector and Hybrid Search with AstraeaDB in Python | py | `blogs/py-02-vector-search.md` | **Exists as markdown, no export.** Port and verify. Site HTML is generated. |
| `crawl-py-03` | Graph Algorithms, Time-Travel, and GraphRAG in Python | py | `blogs/py-03-algorithms-graphrag.md` | **Exists as markdown, no export.** Port and verify. |
| `crawl-r-01` | Getting Started with AstraeaDB in R | r | `blogs/r-01-getting-started.md` | **Exists, needs a factual fix.** The CRAN install line is broken today (section 2.3, Q1). |
| `crawl-r-02` | Vector and Hybrid Search with AstraeaDB in R | r | `blogs/r-02-vector-search.md` | **Exists; export is stale.** Port and verify. |
| `crawl-r-03` | Graph Algorithms, Time-Travel, and GraphRAG in R | r | `blogs/r-03-algorithms-graphrag.md` | **Exists; export is stale.** Port and verify. |
| `crawl-08-ui` | See Your Graph: Visual Exploration with the Astraea UI | both | `blogs/ui-explore-your-graph.md` | **Exists as markdown, no export.** Port. Cannot be container-verified (it is a browser GUI); gets a manual checklist instead. |

### Walk (7 lessons)

| ID | Title | Track | Source | Status |
| --- | --- | --- | --- | --- |
| `walk-01-embeddings` | What an Embedding Is, and How to Make One | py (r sidebar) | `astraeadb-embeddings-demo` (**private**), `tools/embeddings/embed.py` | **Net-new prose.** Teaches Ollama plus `embeddinggemma`, `embeddinggemma` at its native 768 dimensions, which is what the whole site standardizes on (Q9). No Matryoshka truncation: the reader never slices a vector. |
| `walk-02-semantic-search` | Searching a Graph by Meaning, Not by Keyword | py (r sidebar) | `astraeadb-embeddings-demo` | **Net-new prose, consolidates.** Goes past `crawl-*-02` by building the corpus, choosing what text to embed per node type, and tuning `alpha` in hybrid search. |
| `walk-03-text-to-graph` | Turning a Book Into a Knowledge Graph | py | `astraea-graphrag-demo` | **Net-new prose over existing code.** Extraction to `Character` / `Location` / `Event` / `Theme` / `Chapter` / `Passage` nodes with provenance edges back to source text. |
| `walk-04-graphrag` | GraphRAG End to End: Retrieve, Extract, Linearize, Answer | py | `astraea-graphrag-demo` | **Net-new prose over existing code.** The four-stage pipeline, with the comparison mode that shows the same question answered without the graph. |
| `walk-05-data-lake` | A Metadata Graph Over a Messy Data Lake | py | `data_lake_demo` | **Net-new prose over existing code.** Concept nodes, `SUCCEEDED_BY` temporal edges, identity-mapping edges, and an agent that plans a DuckDB query from the graph. |
| `walk-06-eunomia` | Eunomia: A Semantic Cache in Front of Your Graph | py | `AstraeaDB/eunomia`, `data_lake_demo/EUNOMIA_INTEGRATION.md` | **Net-new.** Introduce and link (see Q10): what working memory is, install, one worked example, and the measured effect on the data-lake demo. |
| `walk-07-a-llama` | a-llama: A Local LLM Server That Remembers | py | `AstraeaDB/a-llama` | **Net-new.** Introduce and link: Ollama-compatible API with AstraeaDB and Eunomia compiled in-process, and what "memory that grows" means in practice. |

### Run (5 lessons)

| ID | Title | Track | Source | Status |
| --- | --- | --- | --- | --- |
| `run-01-fraud-elliptic` | Finding Fraud: Classifying Bitcoin Transactions with an In-Database GNN | **rust** | `GNN-test-and-improve` | **Net-new prose, needs update.** The repo is a Rust harness on the Elliptic dataset (203,769 nodes, 234,355 edges, 165-dimensional features). GNN has no wire protocol, so this lesson is necessarily Rust. Needs a sampled dataset (Q4). |
| `run-02-cyber-build` | Building a Network Graph From Security Telemetry | py | `cyber-graph-demo` (**private**) Act 1 | **Net-new prose over existing code.** Ingestion, graph statistics, PageRank, Louvain, degree and betweenness centrality on authentication, process, flow, and DNS events. |
| `run-03-cyber-hunt` | Hunting Lateral Movement With Embeddings and Time Travel | py | `cyber-graph-demo` Act 2 | **Net-new prose over existing code.** Behavioral embeddings, semantic neighbors, and temporal traversal to trace a red-team compromise. |
| `run-04-cyber-report` | Explaining an Investigation: GraphRAG for Audit-Grade Reports | py | `cyber-graph-demo` Act 3 | **Net-new prose over existing code.** Grounding an LLM narrative in retrieved subgraphs so every claim traces to a node. |
| `run-05-ai-assisted-dev` | Giving Your Coding Assistant a Memory | py | `adb-claude-kit` | **Net-new prose over existing code.** `astraeadb mcp` over stdio as a Claude Code sidecar, cheap chunked ingestion versus agent-driven typed ingestion, and writing notes back into the graph. |

**Counts by status:** 8 exist as prose and need porting plus re-verification, 12
are net-new prose (10 of those over code that already exists in a demo
repository and needs an audit first, 2 are pure introductions).

---

## 5. AstraeaDB APIs each tier must teach

Named concretely so lesson authors are not guessing. Node ids are
knowledge-graph ids; a dev agent can jump straight to the source with
`kg_read_span`.

### 5.1 The wire surface, which bounds what Python and R can teach

`astraea-server::protocol::Request` (node_id=1386) has 33 variants and is the
complete set of operations any non-Rust client can perform. Both clients cover
it: the Python `JsonClient` exposes 44 methods over those 33 commands, and the R
package mirrors them. Two consequences that shape the site:

- **There is no GNN command.** `astraea-gnn` (crate node_id=345) is a Rust
  library only. `run-01-fraud-elliptic` must therefore be a Rust lesson, and no
  amount of wishing makes it a Python one.
- **Vector-aware requests need a vector index.** `VectorSearch`, `HybridSearch`,
  `SemanticNeighbors`, `SemanticWalk`, and anchor-less `GraphRag` return an
  error rather than a panic if the server was built without one. Every lesson
  from `crawl-*-02` onward must show a server started with `[vector]` configured
  and must say what happens if it is not.

### 5.2 Crawl

| Lesson | APIs and node ids |
| --- | --- |
| `crawl-*-01` | `Request::CreateNode` / `CreateEdge` / `GetNode` / `Neighbors` / `Bfs` / `ShortestPath` / `Query` / `GraphStats` (all in the enum at node_id=1386). Server-side these land on `Graph::neighbors` (node_id=653) and `Graph::neighbors_filtered` (node_id=654). GQL is parsed and run by `astraea-query` (crate node_id=907); the lesson should say plainly that a pattern must start with a node and then alternate edge and node. |
| `crawl-*-02` | `Request::VectorSearch`, `HybridSearch`, `SemanticNeighbors`, `SemanticWalk`. Behavior to explain comes from `Graph::hybrid_search` (node_id=666), `Graph::semantic_neighbors` (node_id=667), and `Graph::semantic_walk` (node_id=668). `alpha` blends graph proximity against vector similarity, where `alpha = 1.0` is pure vector and `alpha = 0.0` is pure graph; the tests at node_id=683 and node_id=682 pin that behavior and are the right thing to read before writing the paragraph. |
| `crawl-*-03` | Algorithms via `RunPageRank` / `RunLouvain` / `RunConnectedComponents` / `RunDegreeCentrality` / `RunBetweennessCentrality`, implemented by `pagerank` (node_id=41) with `PageRankConfig` (node_id=39), `louvain` (node_id=14), `degree_centrality` (node_id=3), `betweenness_centrality` (node_id=4), and `connected_components` (node_id=23). Two honest caveats the lesson must state: PageRank follows only outgoing edges and computes only over the nodes you supply, and Louvain is single-level, not the multi-level variant. Time travel via `NeighborsAt` / `BfsAt` / `ShortestPathAt` / `DfsAt`, backed by `bfs_at` (node_id=724), `shortest_path_unweighted_at` (node_id=725), `dijkstra_at_temporal` (node_id=751), and the interval test `ValidityInterval::contains` (node_id=192). GraphRAG via `Request::GraphRag` and `ExtractSubgraph`. |
| `crawl-08-ui` | No server API beyond what the dashboard issues. The lesson is about `AstraeaDB/astraea-ui`, a Leptos application compiled to WebAssembly. |

### 5.3 Walk

| Lesson | APIs and node ids |
| --- | --- |
| `walk-01-embeddings` | No AstraeaDB API. Ollama's `/api/embed` with `embeddinggemma`, used at its native 768 dimensions (Q9). `tools/embeddings/embed.py` in this dev environment is the reference implementation but currently truncates to 128, so it must be updated before it is cited. Tie the dimension choice to `astraea-core`'s invariant that a node's embedding dimension is pinned by the HNSW index on first insert, so a store must not mix dimensions (crate node_id=170). |
| `walk-02-semantic-search` | Same wire calls as `crawl-*-02`, taught at depth. Add the server's `[vector] dimension` and `metric` configuration, which `astraea-cli` (crate node_id=69) reads and which defaults to 128-dimensional cosine when the section is omitted. Because the site standardizes on 768 (Q9), every lesson sets `[vector] dimension = 768` explicitly rather than relying on the default. |
| `walk-03-text-to-graph` | `CreateNode` with `embedding`, `CreateEdge` with `valid_from` and `valid_to`, `FindByLabel`, `FindEdgeByType`, and the bulk helpers `create_nodes` and `create_edges` in the Python client. |
| `walk-04-graphrag` | The pipeline in `astraea-rag` (crate node_id=1093): `graph_rag_query` (node_id=1190) and `graph_rag_query_anchored` (node_id=1191), `extract_subgraph` (node_id=1206) and `extract_subgraph_semantic` (node_id=1207), `linearize_subgraph` (node_id=1114) with `TextFormat` (node_id=1113), and the token budget via `estimate_tokens` (node_id=1217) and `extract_with_budget` (node_id=1218). Configuration and result shapes are `GraphRagConfig` (node_id=1187) and `GraphRagResult` (node_id=1189). Providers are pluggable behind `LlmProvider` (node_id=1132) and `EmbeddingProvider` (node_id=1095), with `OllamaProvider` (node_id=1156) implementing both. From Python the same thing is reached with `Request::GraphRag` or through the MCP tool `graph_rag` (node_id=879). |
| `walk-05-data-lake` | `SemanticNeighbors` for concept matching, `NeighborsAt` for platform succession, `GetSubgraph` for the planning context, and `Query` for the GQL used in planning. |
| `walk-06-eunomia` | Eunomia's own REST, gRPC, and MCP surface. The AstraeaDB touchpoint is the optional `eunomia-astraea` bridge, which calls `GraphOps::create_node` and `get_node` from `astraea-core` (crate node_id=170). |
| `walk-07-a-llama` | a-llama's Ollama-compatible HTTP verbs (`generate`, `chat`, `embeddings`, `tags`). AstraeaDB is embedded in-process, so there is no wire call to show. |

### 5.4 Run

| Lesson | APIs and node ids |
| --- | --- |
| `run-01-fraud-elliptic` | `astraea-gnn` (crate node_id=345), all Rust: `train_node_classification` (node_id=519) with `TrainingConfig` (node_id=501), `TrainingData` (node_id=502), and `TrainingResult` (node_id=503); the model stack `GNNModel` (node_id=382), `GNNLayer` (node_id=380), and `ClassificationHead` (node_id=381); `message_passing` (node_id=370) with `MessagePassingConfig` (node_id=368), `Aggregation` (node_id=366), and `Activation` (node_id=367); sparse adjacency via `CSRAdjacency` (node_id=412) built by `from_graph` (node_id=413) with `FeatureMatrix` (node_id=405); GraphSAGE-style `sample_subgraph` (node_id=398) with `SamplingConfig` (node_id=396); and inference via `predict_from_logits` (node_id=387). Two facts the lesson must state because they are load-bearing: passing `hidden_dim = Some(_)` selects analytical backpropagation while `None` selects a legacy finite-difference path that only tunes edge weights, and training is single-threaded by design because `Tensor::grad` is a `RefCell`. For the temporal variant, `TemporalGNNModel` (node_id=426) with `GRUCell` (node_id=423) and `train_temporal` (node_id=435). |
| `run-02-cyber-build` | The five algorithm commands from `crawl-*-03`, at a scale where they matter, plus `GraphStats`. |
| `run-03-cyber-hunt` | `SemanticNeighbors`, `SemanticWalk`, `HybridSearch`, and the four temporal commands. `astraea-graph` ships a cybersecurity test module worth reading as a modeling reference, in particular `dhcp_lease_temporal_validity` (node_id=625), which shows how to express a lease as an edge with a validity interval. |
| `run-04-cyber-report` | `Request::GraphRag` and `ExtractSubgraph`, with `TextFormat` (node_id=1113) driving the linearization the model sees. |
| `run-05-ai-assisted-dev` | `astraea-mcp` (crate node_id=752): `McpServer` (node_id=805) over `StdioTransport` (node_id=902), `ToolRegistry` (node_id=873) exposing 28 tools, all proxied by `ProxyClient` (node_id=754), which opens a fresh TCP connection per call to a running server. The lesson must say that the MCP server holds no graph state of its own and that stdout is reserved for JSON-RPC frames, so any logging goes to stderr. |

### 5.5 Crates the site depends on, and why

The site links no crates as a build dependency, so "depends on" here means "a
lesson teaches its behavior and the verification loop exercises it."

| Crate | node_id | Why the site needs it |
| --- | --- | --- |
| `astraea-cli` | 69 | Every lesson starts with `astraeadb serve`. It is also the crate whose absence from crates.io shapes the install instructions (Q2). |
| `astraea-server` | 1223 | Defines the 33-command wire surface that bounds both client tracks. |
| `astraea-core` | 170 | Source of the invariants the lessons must state honestly: server-assigned ids, pinned embedding dimension. |
| `astraea-graph` | 616 | Semantics of traversal, hybrid search, semantic walk, and temporal filtering. |
| `astraea-vector` | 1768 | HNSW behavior, and why a dimension cannot be changed after first insert. |
| `astraea-algorithms` | 1 | PageRank, Louvain, centrality, components, plus their documented limits. |
| `astraea-query` | 907 | GQL pattern rules the lessons teach. |
| `astraea-rag` | 1093 | The whole Walk GraphRAG tier. |
| `astraea-gnn` | 345 | The fraud lesson, which is Rust because this crate has no wire protocol. |
| `astraea-mcp` | 752 | The AI-assisted-development lesson. |

Five crates are deliberately **not** taught: `astraea-storage` (node_id=1459, an
implementation detail the reader never calls), `astraea-flight` (node_id=288,
mentioned once as an optional Python extra and no further), `astraea-cluster`
(node_id=103, a documented stub with no consensus, replication, or transport),
`astraea-gpu` (node_id=531, which despite the name contains no GPU code, only a
single-threaded CPU reference backend), and `astraea-crypto` (node_id=213, whose
own crate documentation states that the primitives are not cryptographically
secure, so teaching it would be irresponsible).

---

## 6. Source-repository audit plan

None of the demos are dependencies. Each is a **source of narrative and of code
that must be re-proven** against AstraeaDB at its current revision. Four are
cloned locally and two are not.

| Repo | Local clone | Language | Last push | Visibility |
| --- | --- | --- | --- | --- |
| `astraea-graphrag-demo` | `~/Documents/graphrag-demo` at `229bdbf` | Python | 2026-04-08 | public |
| `data_lake_demo` | `~/Documents/data_lake_demo` at `58c1f1d` | Python | 2026-06-16 | public |
| `astraeadb-embeddings-demo` | **not cloned** | Python | 2026-03-25 | **private** |
| `GNN-test-and-improve` | **not cloned** | Rust | 2026-03-07 | public |
| `cyber-graph-demo` | `~/Documents/cyber-graph-demo` at `f213607` | Python | 2026-03-26 | **private** |
| `adb-claude-kit` | `~/Documents/adb-claude-kit` at `9e6c9bf` | Python | 2026-05-07 | public |

The oldest three predate AstraeaDB 0.3.1 by four to five months. **I cannot
resolve whether they still work from a design seat**, so each audit is an
explicit task (T9 through T14) with a fixed checklist.

### The checklist every audit runs

1. Clone or pull to a scratch directory. Record the commit sha in the project KG
   as a `Fixture` node so the lesson can cite exactly what was tested.
2. Diff the client calls the demo makes against the 33 variants of `Request`
   (node_id=1386) and against the current Python client's 44 methods. Flag any
   call that no longer exists, any renamed argument, and any place the demo
   assumes a response shape that has changed.
3. Check the embedding dimension the demo configures against the site standard
   of 768 (Q9). Demos written at 128 predate the issue #25 fix and must be
   updated, not copied. Record any divergence and why.
4. Run the demo's own test file where it has one (`test_demo.py` exists in
   `graphrag-demo` and `data_lake_demo`) against a container-hosted server.
5. Note every external prerequisite: dataset downloads, API keys, model pulls,
   Kaggle credentials. These decide whether a lesson can be container-verified
   at all or needs a sampled subset.
6. Produce a one-page audit note as a `Note` node in the project KG, listing
   what still works, what broke, and the minimum change that makes the lesson
   runnable.

### What "consolidated" means, per repo

- **`astraea-graphrag-demo`.** The narrative splits cleanly into two lessons:
  `walk-03-text-to-graph` (how the 229-node graph gets built from the novel) and
  `walk-04-graphrag` (the orchestration loop in `src/orchestrator.py` and
  `src/mcp_bridge.py`). Consolidated means the site owns the prose, the
  repository keeps `tale_of_two_cities.txt` and the extraction scripts, and the
  site's `samples/` holds the trimmed versions the reader actually pastes. Its
  prompt-engineered tool-calling workaround for `gemma3:4b` is worth keeping as
  a teaching point, not hiding.
- **`data_lake_demo`.** Becomes `walk-05-data-lake`, with its Eunomia
  integration lifted into `walk-06-eunomia` rather than mentioned twice.
  Consolidated means the site teaches the *metadata graph pattern* (concept
  nodes, succession edges, identity mapping) as a reusable idea, and links the
  repository for the generated data and the DuckDB tooling. Its
  `DEMO_EXPLAINED.md` is the best existing prose of the three and should be
  mined heavily.
- **`astraeadb-embeddings-demo`.** Becomes `walk-01-embeddings` and
  `walk-02-semantic-search`. It is the smallest of the three and the most
  duplicative of `crawl-*-02`, so consolidated here means **absorbed**: the site
  takes what is distinctive (choosing what text to embed per node type,
  Matryoshka truncation, tuning `alpha`) and the repository is not linked at
  all, which also sidesteps its private visibility. See Q3.
- **`GNN-test-and-improve`.** Becomes `run-01-fraud-elliptic`. The repository is
  a *report*, not a tutorial: it documents ingestion throughput of 1,531 nodes
  per second bounded by HNSW insertion, and a feature-dimension discrepancy
  where the Kaggle documentation says 166 but the data has 165. Consolidated
  means the lesson teaches the workflow and keeps the honest performance
  findings as a closing section, because a reader who hits 1,531 nodes per
  second deserves to know that this is expected and why.
- **`cyber-graph-demo`.** Its three acts map one-to-one onto `run-02`, `run-03`,
  and `run-04`. Consolidated means the site owns the three-act narrative, and
  the repository keeps `download_data.py`, `extract_subset.py`, and the LANL
  handling. Its `voiceover.md` and `voiceover-short.md` are presentation scripts
  and are a good source of plain-language explanation.
- **`adb-claude-kit`.** Becomes `run-05-ai-assisted-dev`. It is the newest and
  most likely to still work. Consolidated means the lesson is essentially a
  guided tour of its README plus one worked session, and the repository stays
  the installable artifact. Its `docs/mcp-tool-coverage.md` should be checked
  against the 28 tools in `ToolRegistry` (node_id=873) as part of the audit.

---

## 7. Verification design

CONCEPT.md makes this a hard requirement: every instruction and every code
snippet is tested in containers using the Apple container service, the same
method used when the blogs were written.

### 7.1 What the environment actually provides, measured

- `container` CLI **0.10.0** is installed at `/usr/local/bin/container`, with a
  buildkit builder already running.
- Cached images today are `r-base:latest` and `koopman-cran-check`, which is
  consistent with the R blogs having been checked in a container. **No container
  tooling was left behind in this repository**: a search across `tools/`,
  `justfile`, and every `*.sh` finds no `container run` or `container build`
  anywhere. There is nothing to reuse, so `verify/` is net-new.
- A container receives an address on `192.168.64.0/24` (a probe run for this
  design got `192.168.64.13`) and the host appears on the bridge at
  `192.168.64.1`.
- **The host's services are not reachable from a container.** Both `ollama`
  (port 11434) and the `getting-started-instance` server (ports 50102 and 50103)
  bind `127.0.0.1` only. This was verified with `lsof`, not assumed, and it is
  the single most important constraint on the design below.

### 7.2 Images

Four images, built by `just images`, all `linux/arm64`.

| Image | Base | Contents | Used by |
| --- | --- | --- | --- |
| `astraea-verify-base` | `debian:bookworm-slim` | `protobuf-compiler`, `libprotobuf-dev`, `pkg-config`, `libssl-dev`, `build-essential`, `curl`, `git`, rustup with a pinned toolchain | parent of the rest |
| `astraea-verify-py` | base | Python 3.11, `pip`, and a prebuilt `astraeadb` binary from `cargo install --git ... astraea-cli` | all Python lessons |
| `astraea-verify-r` | `r-base:latest` plus the base packages | R, `remotes`, and the same prebuilt `astraeadb` binary | all R lessons |
| `astraea-verify-rust` | base | cargo registry warmed with the 0.3.1 crates | `run-01-fraud-elliptic` |

The install step is split deliberately into two modes:

- **`--mode install`** builds the image *from scratch*, running the exact
  commands the Crawl lessons print, including the `apt-get install` line and the
  `cargo install --git` line. Building the image **is** the test of the install
  instructions. This runs once per release and on any change to
  `_shared/install-server.md`.
- **`--mode fast`** uses the cached image with `astraeadb` already present. This
  runs on every snippet check and keeps the loop to seconds rather than minutes.

This split is what stops "verification is too slow to run" from quietly becoming
"verification does not run."

### 7.3 How a lesson's snippets get extracted and run

`verify/extract.py` parses a lesson's markdown for fenced code blocks and reads
an optional HTML-comment directive on the line immediately before the fence.
HTML comments are invisible in the rendered page, so the directives never leak
into the reader's view.

| Directive | Meaning |
| --- | --- |
| *(none)* | Default. A `bash`, `python`, or `r` block runs, in document order, in the lesson's session. Any other language is treated as illustrative and skipped. |
| `<!-- verify: skip reason="..." -->` | Not run. The reason is required and is displayed on `/status.html`, so skipping is visible rather than silent. |
| `<!-- verify: expect-output -->` | The block runs and its stdout is compared against the immediately following `text` block, after normalization. |
| `<!-- verify: setup -->` | Runs before the lesson body. Used for fixtures a reader would already have from a prior lesson. |
| `<!-- verify: continues -->` | This block shares an interpreter session with the previous block of the same language, so a variable defined earlier is still bound. |

`verify/run.py <lesson-id>` then does the following:

1. Starts a fresh container from the lesson's image with `samples/<lesson-id>/`
   and `data/` mounted read-only.
2. Starts `astraeadb serve` **inside** the container on `127.0.0.1:7687` with a
   `[vector]` section at 768 dimensions and cosine distance. Because the server
   is in the container, the literal `127.0.0.1:7687` in the lesson text is the
   thing being tested, not a substitute.
3. Concatenates the lesson's `bash` blocks into one script and each language's
   blocks into one interpreter session, honoring `continues`.
4. Runs them, capturing exit code, stdout, and stderr per block.
5. Compares `expect-output` blocks after `normalize.py` masks the things that
   legitimately vary: node and edge ids, timestamps, durations, and float digits
   past the fourth decimal place.
6. Tears the container down. Every lesson starts from an empty graph, so no
   lesson can accidentally depend on another lesson's leftovers.
7. Appends a record to `verify/report.json`.

Lessons that need a large language model are the exception to the self-contained
rule. The recommendation is to run `OLLAMA_HOST=0.0.0.0 ollama serve` on the
host during verification and inject `OLLAMA_URL=http://192.168.64.1:11434` into
the container, since `embeddinggemma` and `qwen3:32b` are already pulled on this
machine and re-pulling a 19 GB model per run is not viable. That creates a
divergence between the tested URL and the published one, which is Q8.

### 7.4 What "green" means

A lesson is green when **all** of the following hold:

1. Every non-skipped block exits `0`.
2. Every `expect-output` block matches after normalization.
3. Every skipped block carries a non-empty `reason`.
4. The run recorded the AstraeaDB git revision, the client package versions, and
   the date.
5. No block wrote to stderr with a pattern matching `error`, `panic`,
   `traceback`, or `Error in ` (case-insensitive), unless the block is
   explicitly marked as demonstrating an error.

The path is green when every lesson whose `lessons.toml` entry says
`verify = "required"` is green.

**The build enforces this.** `build.py` reads `verify/report.json` and refuses to
render a `verify = "required"` lesson whose latest run is not green. Every
rendered page carries a footer stamp reading "Verified against AstraeaDB `<rev>`
on `<date>`," and `/status.html` shows the full matrix with every skip reason
spelled out. A reader can therefore see exactly which parts of the site are
machine-checked and which are not.

`crawl-08-ui` cannot be container-verified because it drives a browser. It is
marked `verify = "manual"` and carries a checklist in
`verify/manual/crawl-08-ui.md` that a human runs before each release. The status
page shows it as manually verified with a date, not as green.

---

## 8. Tooling decision

**The site is built by pandoc, driven by a small stdlib-only Python script.**

- **Converter:** `pandoc 3.9`, already installed at `/opt/homebrew/bin/pandoc`,
  invoked as `pandoc --standalone --template site/templates/lesson.html
  --highlight-style tango --toc --toc-depth=2 --metadata-file <generated>`.
  Note that pandoc is **not** on the default `PATH` in this environment, so
  `build.py` resolves it explicitly and fails with a clear message if it is
  absent.
- **Driver:** `site/build.py`, roughly 200 lines, standard library only. It
  reads `lessons.toml`, expands `<!-- include: -->` directives, generates the
  per-page metadata (title, tier, track, sibling, prev, next, verified stamp),
  calls pandoc once per lesson, renders `index.html` and `status.html`, copies
  `assets/`, `samples/`, and `data/`, and writes `.nojekyll`.
- **Styling:** one hand-written `site/assets/site.css`, no framework, no content
  delivery network. Pages should land near 30 KB rather than the current 635 KB.
- **Publishing:** GitHub Pages from `main` and `/docs`. `docs/` is committed.

**Why not something else.** Jekyll is what Pages runs by default and would work,
but it introduces a Ruby toolchain that nothing else here uses. Hugo or MkDocs
would both do the job well, and either would be defensible, but each is a new
dependency to install, pin, and maintain, and neither buys anything that the
combination of pandoc plus a manifest does not already provide for twenty pages.
Pandoc is already the tool that produced every existing HTML file in `blogs/`,
so staying with it keeps one converter in the house rather than two. The
`.nojekyll` file stops Pages from trying to process the pandoc output.

**The Medium exports are gone.** Q7 is resolved: Medium is not a publication
target, and the five self-contained RStudio pages were deleted in `e0a1332`.
There is no `just medium` recipe and no `medium/` directory. The site is the
only HTML output, which also removes the drift that left two exports stale.

**Disposition of the rag scaffold** is the table in section 2.1. In short:
delete `ingest.py`, `query.py`, and `corpus/`; rewrite `justfile` and
`astraea-config/default.toml` in place; keep the running instance as the
authoring server and rename it.

---

## 9. Task list

Thirty tasks. Dependencies are marked `after:`. Tasks marked **[parallel]** can
run at the same time as their siblings in the same phase.

### Phase 0: foundation. Nothing else starts until T4 passes.

- **T1 [documentarian] Restructure the project directory.** Delete `ingest.py`,
  `query.py`, and `corpus/`. Create `content/`, `site/`, `verify/`, `samples/`,
  `data/`, and `docs/`. Rewrite `justfile`, `astraea-config/default.toml`,
  `README.md`, and the template section of `PROJECT.md`. Rename the launcher
  instance to `getting-started-authoring`.
  *Accept:* the tree matches section 3.1; `just --list` shows only the new
  recipes; the authoring server still answers a ping on its new name; no
  reference to the rag template survives in any file.
  *after:* nothing. Q6 is resolved (`AstraeaDB/getting-started`, `/docs` on `main`), so this is the entry point for Phase 0.
- **T2 [documentarian] Build the site toolchain.** Write `lessons.toml` with all
  20 entries, `site/build.py`, the three templates, `site/assets/site.css`, and
  `site/assets/site.js` (track switcher plus `localStorage` preference).
  *Accept:* `just build` renders a two-page smoke site with a working sidebar,
  track switcher, and prev/next; a lesson in `lessons.toml` with no content file
  fails the build; a `_shared` fragment containing a `python` or `r` fence fails
  the build; output pages are under 60 KB; `.nojekyll` is written.
  *after:* T1.
- **T3 [tester] Build the verification harness.** Write the four Dockerfiles,
  `verify/extract.py`, `verify/run.py`, and `verify/normalize.py`. Build all four
  images in both modes.
  *Accept:* `just images` completes; `--mode install` proves the `apt-get` and
  `cargo install --git` lines from `_shared/install-server.md` work from
  scratch; a fresh container starts `astraeadb serve` on `127.0.0.1:7687` and
  answers `Ping`; `verify/run.py` on a three-block fixture lesson returns green,
  and returns red when a block is made to fail.
  *after:* T1. **[parallel with T2]**
- **T4 [reviewer] Gate the toolchain.** Run the full loop on two real lessons,
  `crawl-py-01` and `crawl-r-01`, straight from the existing blog markdown.
  *Accept:* both render, both verify green or produce a specific actionable
  failure; the verified stamp appears in the footer; `/status.html` renders.
  *after:* T2, T3. **This is the gate for every phase below.**

### Phase 1: Crawl. All parallel with Phase 2.

- **T5 [documentarian] Port the eight Crawl lessons.** Move the markdown into
  `content/crawl/`, add front matter, factor `install-server.md`,
  `ollama-setup.md`, `what-is-an-embedding.md`, and `what-is-graphrag.md` into
  `_shared/`, and build `glossary.md`. Apply the CRAN fix from Q1 to
  `crawl-r-01`. Add verification directives to every code block.
  *Accept:* eight pages render; a STYLE.md pass finds zero em-dashes in prose,
  zero sentence fragments, and every acronym spelled out on first use; the two
  tracks share four fragments with no duplicated prose; every cross-link
  resolves; word counts stay in the 1,100 to 1,600 band.
  *after:* T4.
- **T6 [tester] Verify the six code-bearing Crawl lessons.** Run `crawl-py-01`
  through `crawl-py-03` and `crawl-r-01` through `crawl-r-03`. File each failure
  as an `Issue` node in the project KG.
  *Accept:* all six green, or every non-green lesson has an `Issue` node naming
  the block, the exit code, and the diagnosis. The R install path must be
  confirmed working end to end in the container, not assumed.
  *after:* T5.
- **T7 ~~[documentarian] Close the Medium export gap.~~ DROPPED 2026-08-07.**
  Q7 resolved: Medium is not a publication target and the five RStudio exports
  were deleted in `e0a1332`. Task count is therefore **29**, not 30. No `medium/`
  directory and no `just medium` recipe are built.
- **T8 [tester] Write and run the UI manual checklist.** Build the Astraea UI
  from source on the host, follow `crawl-08-ui` step by step, and record which
  steps work.
  *Accept:* `verify/manual/crawl-08-ui.md` exists with a dated result;
  `cargo-leptos 0.3.5`, the `wasm32-unknown-unknown` target, and the Tailwind
  command-line version stated in the lesson are all confirmed current.
  *after:* T5. **[parallel with T6, T7]**

### Phase 2: source audits. All six run in parallel with each other and with Phase 1.

Each follows the checklist in section 6 and produces a `Note` node plus a
`Fixture` node recording the audited commit sha.

- **T9 [tester] Audit `astraea-graphrag-demo`** at `229bdbf`. *Accept:* audit
  note filed; `test_demo.py` result recorded; the graph builds to 229 nodes and
  317 edges against a current server, or the discrepancy is explained.
  *after:* T4. **[parallel]**
- **T10 [tester] Audit `data_lake_demo`** at `58c1f1d`. *Accept:* audit note
  filed; the DuckDB and Anthropic prerequisites are enumerated; the Eunomia
  integration is confirmed against the current Eunomia release.
  *after:* T4. **[parallel]**
- **T11 [tester] Audit `astraeadb-embeddings-demo`.** Requires a clone; the repo
  is private. *Accept:* audit note filed, or a blocked note stating that access
  was unavailable. Recommend explicitly whether the material is worth absorbing
  at all given its overlap with `crawl-*-02`.
  *after:* T4, Q3. **[parallel]**
- **T12 [tester] Audit `GNN-test-and-improve`.** *Accept:* audit note filed; the
  crate builds against `astraea-gnn` at the current revision, given that it is
  not on crates.io; the 165-dimension finding is confirmed; a proposal for a
  redistributable sampled subset is included.
  *after:* T4. **[parallel]**
- **T13 [tester] Audit `cyber-graph-demo`** at `f213607`. *Accept:* audit note
  filed; the LANL download size and license terms are recorded; a proposal for a
  sampled subset is included; the three acts are confirmed to still run.
  *after:* T4, Q3. **[parallel]**
- **T14 [tester] Audit `adb-claude-kit`** at `9e6c9bf`. *Accept:* audit note
  filed; `docs/mcp-tool-coverage.md` reconciled against the tools in `ToolRegistry`
  (node_id=873); the standalone install path confirmed. **Corrected
  2026-08-08: the registry holds 29 real tools, not 28. The 30th name,
  `echo`, is defined inside a test in `tools/mod.rs`.**
  *after:* T4. **[parallel]**

### Phase 2.5: prerequisite, added 2026-08-09

- **T28-BLOCK [dev-core] Land AstraeaDB issue #28 before writing lesson prose.**
  Decided 2026-08-09: the lessons are written against `cargo install astraeadb`
  rather than the `--git` form, so #28 is now on the critical path rather than a
  nice-to-have. The work is adding `description`, `license.workspace` and
  `repository.workspace` to nine crates and `publish = false` to
  `astraea-encrypt-demo`, then publishing in dependency order. See
  `astraeadb-issues.md` #28.
  *Accept:* `cargo install astraeadb` works from a clean container; the Crawl
  `_shared/install-server.md` fragment is rewritten to use it; the verification
  images drop their `cargo install --git` step and rebuild much faster.
  *Blocks:* all Walk and Run prose, because every lesson opens with an install
  line and nobody should write it twice.

### Phase 3: Walk. Each lesson depends on its audit.

- **T15 [documentarian] Write `walk-01-embeddings`.** *after:* T11.
- **T16 [documentarian] Write `walk-02-semantic-search`.** *after:* T11, T15.
- **T17 [documentarian] Write `walk-03-text-to-graph`.** *after:* T9. **[parallel with T15]**
- **T18 [documentarian] Write `walk-04-graphrag`.** *after:* T9, T17.
- **T19 [documentarian] Write `walk-05-data-lake`.** *after:* T10. **[parallel with T15, T17]**
- **T20 [documentarian] Write `walk-06-eunomia`.** *after:* T10, T19.
- **T21 [documentarian] Write `walk-07-a-llama`.** *after:* T4. **[parallel]**

*Accept, for each of T15 through T21:* the lesson renders; it passes a STYLE.md
review; every AstraeaDB API it names exists in the knowledge graph and is cited
by node id in a `Note` node; the corresponding `verify/run.py` invocation is
green or its skips carry reasons; a `samples/<lesson-id>/` directory holds the
runnable version of every snippet.

### Phase 4: Run. Each lesson depends on its audit.

- **T22 [documentarian] Write `run-01-fraud-elliptic`.** Rust. *after:* T12, Q4.
- **T23 [documentarian] Write `run-02-cyber-build`.** *after:* T13, Q4. **[parallel with T22]**
- **T24 [documentarian] Write `run-03-cyber-hunt`.** *after:* T23.
- **T25 [documentarian] Write `run-04-cyber-report`.** *after:* T24.
- **T26 [documentarian] Write `run-05-ai-assisted-dev`.** *after:* T14. **[parallel with T22, T23]**

*Accept, for each of T22 through T26:* the same criteria as Phase 3, plus every
lesson that needs an external dataset either runs against the sampled subset in
`data/` or carries an explicit, reasoned `skip`.

### Phase 5: assembly and launch.

- **T27 [documentarian] Write the landing page and the status page.** Hero,
  language chooser, three tier cards, verification strip, footer.
  *Accept:* all 20 lessons reachable in at most two clicks from `/`; the lesson
  lists are generated, not hand-written; adding a lesson to `lessons.toml`
  changes the landing page with no other edit; the page renders sensibly with
  JavaScript disabled.
  *after:* T21, T26.
- **T28 [reviewer] Full style and accuracy pass.** Read all 20 lessons against
  STYLE.md and against the knowledge graph.
  *Accept:* zero em-dashes in prose; zero sentence fragments; every acronym
  spelled out on first use; no invented API anywhere, checked by grepping every
  method name against the client surfaces and the knowledge graph; every claimed
  output traceable to a verification run.
  *after:* T27.
- **T29 [tester] Full-path verification run.** `just verify-all` from clean
  images in `--mode install`.
  *Accept:* every `verify = "required"` lesson green; `/status.html` shows the
  complete matrix; the total wall time is recorded so the team knows what a
  release costs.
  *after:* T28.
- **T30 [reviewer] Launch readiness.** Confirm the Pages configuration, all
  external links, the license, and the repository description. Add the optional
  GitHub Action that runs `just build` and a fast-mode `just verify-all` on push.
  *Accept:* the site is live at its URL; every outbound link returns 200; the
  Action passes on a trial push; a `Decision` node records the launch revision.
  *after:* T29. Publish to `AstraeaDB/getting-started` from `/docs` on `main`; the URL is `https://astraeadb.github.io/getting-started/` (Q6). Whether `AstraeaDB-Official`'s README points here as its primary entry point is decided at this step.

---

## 10. Open questions for the user

CONCEPT.md asks for questions to be raised in the plan. These are genuine
blockers or genuine forks, not formalities. Each is recorded as a `Decision`
node in the `getting-started` project knowledge graph. Where I have a
recommendation, it is stated.

**Q1. The R install instruction is broken today. What should it say?**
`blogs/r-01-getting-started.md` line 65 tells the reader
`install.packages("AstraeaDB")`, and `blogs/README.md` links
`https://CRAN.R-project.org/package=AstraeaDB`. That URL returns **404**. The R
package is not on CRAN. The `remotes::install_github("AstraeaDB/R-AstraeaDB")`
fallback on line 74 does work.
*Recommendation:* make `remotes::install_github(...)` the primary instruction
now, and keep a single sentence saying a CRAN release is planned. Reversing them
once CRAN accepts the package is a one-line change. The alternative, holding the
whole R track until CRAN acceptance, blocks half the Crawl tier on a process we
do not control.
*Also decide:* should the R package's CRAN submission be treated as a
prerequisite for launch, or as a follow-up?

*ANSWER* Note in the docs that the CRAN submission has been made and is awaiting manual review. Explain how to check to see if the package is available in CRAN, and that if it isn't showing in their mirror, they can install from GitHub

**Q2. Should `astraea-cli` be published to crates.io before the site launches?
RESOLVED 2026-08-07: yes, and it is far cheaper than this question assumed.**
Only five crates are on crates.io at 0.3.1 (`astraea-core`, `astraea-graph`,
`astraea-vector`, `astraea-storage`, `astraea-rag`). `astraea-cli` and
`astraea-server` are not, so every lesson would otherwise open with
`cargo install --git https://github.com/AstraeaDB/AstraeaDB-Official.git
astraea-cli`, which compiles the whole server from source and takes several
minutes on a first run.

*Investigation, 2026-08-07.* The design assumed publishing was a project. It is
not. Nothing structural blocks any of the ten unpublished crates:

- There is **no `publish = false`** anywhere in the workspace.
- **Every internal path dependency already carries `version = "0.3.1"`.** This is
  normally the blocking work, and it is already done. The workspace comment in
  `Cargo.toml` claims the version is only needed for the published five; in fact
  all ten unpublished crates score zero on "path dependency without a version".
- The **only** gap is metadata. All ten lack `description`, `license`, and
  `repository`, and crates.io hard-rejects a publish missing `description` or
  `license`. `astraea-cli`'s `[package]` block carries nothing but
  `version.workspace` and `edition.workspace`, where `astraea-core` carries an
  explicit `description` plus `license.workspace` and `repository.workspace`.

The fix is three lines per crate, two of which are `.workspace = true` because
the workspace already defines `license = "MIT"` and `repository`.

One risk checked and cleared: `astraea-cli` depends on `astraea-graph` with
`features = ["test-utils"]`. That is a real feature (`test-utils = []`), and the
already-published `astraea-rag` 0.3.1 depends on it the same way, so it is proven
to resolve through crates.io.

*Answer:* publish. **This work is out of scope for this project** and is filed
against AstraeaDB as issue **#28** in `astraeadb-issues.md`. Two constraints
recorded there: crates must go out in dependency order
(core, storage, vector, graph, then algorithms and query, then rag, then server,
then cli, flight, mcp, gnn, cluster, gpu), and `astraea-encrypt-demo` should get
`publish = false` rather than metadata, because it is a demo.

*Consequence for this project:* lessons should be written against
`cargo install astraeadb`. If #28 has not landed when a lesson is written, use
the `--git` form and leave a `TODO(#28)` marker so the sweep is mechanical.

**Q3 RESOLVED 2026-08-09: both stay private. Absorb both, link neither.**

`astraeadb-embeddings-demo` could not be audited at all (T11, KG Note 2224):
404 unauthenticated with no local clone. Absorb the material; `crawl-*-02`
already proves the mechanics and what remains is narrative.

`cyber-graph-demo` **stays private, and its pipeline code is absorbed inline**
into `run-02` through `run-04`. This is the most expensive of the three options
considered and it leaves the ingestion and subset-extraction code living in two
places with nothing keeping them in step. Mitigation: the absorbed code goes
into `samples/<lesson-id>/` as real files the harness executes, not as prose in
the page, so it cannot silently rot without a verification run going red.

**Q3. Two source repositories are private. What happens to them?**
`cyber-graph-demo` and `astraeadb-embeddings-demo` are private. Three of the
five Run lessons and two of the seven Walk lessons derive from them.
*Recommendation:* two different answers for the two repositories. For
`astraeadb-embeddings-demo`, **absorb and do not link**: the material is small,
easy to reproduce, and largely overlaps `crawl-*-02`, so the site can be
self-contained and the repository never appears. For `cyber-graph-demo`, **make
it public**, because the cyber lessons will want to link working code for the
LANL download and subset extraction, and rewriting all of that inline is a large
amount of work for no benefit. If it must stay private, the three cyber lessons
need to be scoped down to what the site can ship itself, which is a material
reduction in the Run tier.

*ANSWER* Keep them private, but borrow liberally from them. It is not necessary to reproduce all of the functionality, but demonstrate the advanced features. Keep a directory of scripts the user might need, but explain that going into detail on each of them is beyond the scope of the document, and they should review the code (which should be heavily commented) to understand it further.

**Q4. How do we handle the two large external datasets? PARTLY RESOLVED
2026-08-08 by the Phase 2 audits: LANL is settled, Elliptic is not.**

*LANL is CC0, public domain* (`cyber-graph-demo/README.md:154`, confirmed in the
T13 audit, KG Note 2221). A derived sampled subset may be redistributed in the
site repository with no permission needed, so the cyber lessons can ship data
and be container-verified. That half of this question is closed.

*The Elliptic licence remains unconfirmed.* The T12 audit (KG Note 2222) found
no licence statement anywhere in `GNN-test-and-improve`, and the dataset is
fetched with `kaggle datasets download -d ellipticco/elliptic-data-set`, which
needs an account and CLI credentials. **This still needs a human decision**
before `run-01` can ship any derived data. If redistribution is not permitted,
`run-01` becomes "here is how to get the data yourself" and its code is verified
against a synthetic graph of the same shape, 165 features included.

The original question and reasoning follow.

**Q4. How do we handle the two large external datasets?**
`run-01-fraud-elliptic` needs the Elliptic Bitcoin dataset, which requires
Kaggle credentials and is 203,769 nodes. The cyber lessons need LANL, whose
smallest documented download is about 180 MB. Neither can run in a clean
container without credentials or a long download, so neither can be verified in
the normal loop.
*Recommendation:* ship a deterministic sampled subset of each under `data/` in
the site repository, sized to run in under a minute (on the order of a few
thousand nodes), teach on that, and put the full-dataset instructions in an
appendix marked `verify: skip` with a stated reason. **This needs a licensing
decision:** please confirm that a derived sample of the Elliptic dataset and of
LANL may be redistributed. If the answer is no for either, that lesson becomes
"here is how to get the data yourself" and its code is verified against a
synthetic graph of the same shape instead.

*ANSWER* Explain how to get the data for the user. You may verify the code works on the data already existing locally today (the gnn-elliptinc data should be here: /Users/jimharris/Documents/gnn-elliptic-demo)

**Q5 RESOLVED 2026-08-09: Python-primary, with short "in R" sidebars.**

Walk and Run are written in Python. Where the R client has an equivalent
method, the lesson carries a short collapsible "in R" note rather than a whole
parallel lesson. `run-01-fraud-elliptic` stays Rust, because `astraea-gnn` has
no wire protocol and cannot be driven from any client. The landing page must say
this plainly, so an R reader is not surprised at the end of Crawl.

**Q5. Are Walk and Run Python-only, or do they need R parallel tracks too?**
CONCEPT.md specifies parallel Python and R tracks for Crawl and is silent about
the other two tiers. All four Walk and cyber source demos are Python, and
`run-01-fraud-elliptic` must be Rust because `astraea-gnn` has no wire protocol,
so it cannot be done from any client.
*Recommendation:* Walk and Run are **Python-primary**. Where the R client
already has the equivalent method, add a short collapsible "in R" sidebar rather
than a whole parallel lesson. State this on the landing page so an R reader is
not surprised at the end of Crawl. Building full R versions of twelve lessons
roughly doubles the writing and the verification cost for material whose source
demos are all Python.

*ANSWER* Go with your recommendation for now

**Q6. Where does the site live? RESOLVED 2026-08-07: a new public
`AstraeaDB/getting-started`.**
The options were a new public repository published from `main` and `/docs`, or a
`gh-pages` branch of `AstraeaDB-Official`.
*Answer:* a new public repository, `AstraeaDB/getting-started`, published from
`/docs` on `main`. It gives the site its own issue tracker, keeps roughly 20
pages of generated HTML out of the database repository, and needs no GitHub
Action to publish. The site URL is
**`https://astraeadb.github.io/getting-started/`**, and every internal link,
canonical URL, and asset path in `site/build.py` should be built against that
base.

**T1 and T30 are unblocked, so Phase 0 can start.**

*Two sub-questions were not answered and are deliberately left open, because
neither blocks Phase 0.* Whether a custom domain such as `docs.astraeadb.dev`
should front the site: assume no for now, and note that adding one later is a
`CNAME` file plus a DNS record, so the only real cost of deferring is that
already-published absolute URLs would need a sweep. Keep absolute URLs out of
the content and confined to `build.py` so that sweep stays cheap. And whether
`AstraeaDB-Official`'s README should link the site as its primary entry point:
that is a T30 launch decision, not a build-time one.

**Q7. Is Medium still a publication target? RESOLVED 2026-08-07: no.**
The five existing 635 KB HTML files were self-contained pandoc exports built for
pasting into Medium. Three posts had no export, and two of the R exports were
stale relative to the 2026-08-05 editorial rewrite.
*Answer:* the user confirmed these came out of RStudio and are not important.
All five were deleted in commit `e0a1332`, along with a stray `DESIGN.html`.
Medium is not a publication target. **T7 is dropped**, there is no `just medium`
recipe, and section 8 needs no dual-output path. The paired `.md` files remain
the canonical sources and the site is the only HTML output.

**Q8 RESOLVED 2026-08-09: read `OLLAMA_URL` from the environment, defaulting to
`http://localhost:11434`.**

Neither option this question originally posed. Lesson code reads the URL from
the environment with `http://localhost:11434` as its default, so **the published
code is exactly the code that runs**: a reader gets the default, and the harness
injects `http://192.168.64.1:11434` after starting the host's Ollama with
`OLLAMA_HOST=0.0.0.0`. The divergence moves out of the source and into an
environment variable. `data_lake_demo` and `astraea-graphrag-demo` already work
this way, so the lessons match their sources. Installing Ollama into the image
was rejected because it means a multi-gigabyte model pull per image build.

**Q8. Ollama during verification: expose the host, or install it in the image?**
The host's `ollama` binds `127.0.0.1:11434`, so containers on `192.168.64.0/24`
cannot reach it. The host already has `embeddinggemma` and `qwen3:32b` pulled.
*Recommendation:* run `OLLAMA_HOST=0.0.0.0 ollama serve` on the host during
verification and inject `OLLAMA_URL=http://192.168.64.1:11434` into the
container, while the published lesson tells the reader `http://localhost:11434`.
This means the tested URL and the published URL differ by exactly one hostname.
Installing Ollama into the image is the pure alternative, but it means a
multi-gigabyte model pull per image build. Is the one-hostname divergence
acceptable? If it is not, we accept much slower image builds.

**Q9. Does the site standardize on 128-dimensional embeddings everywhere?
RESOLVED 2026-08-07: no. The site uses 768, the model's native width.**
The blogs and `tools/embeddings/embed.py` use `embeddinggemma` truncated to 128
dimensions. The original recommendation here was to keep 128 site-wide. That was
wrong, and it was wrong for a reason worth recording.

*Investigation, 2026-08-07.* The 128-dimension convention was a workaround for a
bug, not a design constraint, and the bug is fixed:

- There is **no dimension ceiling in the code**. No `MAX_DIM`, no
  `MAX_DIMENSION`, no `dim > N` guard anywhere in `crates/`.
- 768 is **explicitly tested**, not merely tolerated:
  `test_non_128_dimension_insert_and_search_768` and
  `test_round_trip_preserves_non_128_dimension_768` in `astraea-vector`.
- Decisively, `crates/astraea-vector/src/hnsw.rs:1176` is a full-scale acceptance
  guard at N=10k and dim 768, described in its own doc comment as "the a-llama
  regime", asserting `recall@10 >= 0.95`. Somebody committed to keeping 768
  working.
- The limit was **issue #25**, the HNSW recall collapse, which `CHANGELOG.md:175`
  records as resolved. The demos were written while it was open.

*Answer:* use `embeddinggemma` at its native 768 dimensions everywhere. Beyond
correctness, this **removes a teaching burden**: at 128 every lesson carries an
unexplained "now slice the vector" step that needs a Matryoshka-truncation
digression to justify. At the corpus sizes these lessons use, the six-times
storage cost is irrelevant.

*Two things this does not change.* A store's dimension is still pinned on first
insert, so one server still cannot mix widths, and that remains a good teaching
moment. And `run-01-fraud-elliptic` stays at 165, which is the Elliptic dataset's
native feature count and unrelated to the embedding decision.

*Consequence:* the Crawl lessons inherited from `blogs/` currently specify 128 and
must be changed as part of T5. `tools/embeddings/embed.py` truncates to 128 and
needs the same treatment. Any fixture or sample vector data generated at 128 is
regenerated at 768.

**Q10. How deep should the Eunomia and a-llama lessons go?**
Both are substantial projects with their own documentation.
*Recommendation:* for version one, each is a single "introduce and link" lesson
of roughly 1,200 words: what problem it solves, how to install it, one worked
example, and where to read more. Expanding either into a multi-part series is a
follow-up once the twenty-lesson path is live. Confirm that this is the right
depth, or say which of the two deserves more.


---

## 11. Risks

- **The three oldest demos may not run.** `astraeadb-embeddings-demo`,
  `GNN-test-and-improve`, and `cyber-graph-demo` were last pushed four to five
  months before AstraeaDB 0.3.1. Phase 2 exists to find out early. If an audit
  finds a real server regression, it goes to `astraeadb-issues.md` and the
  affected lesson is deferred rather than published unverified.
- **Verification wall time.** Twenty lessons times a container start plus a
  server start is minutes, and `--mode install` is much worse because it
  compiles the server. The two-mode split in section 7.2 is the mitigation, and
  T29 records the real number so the cost of a release is known rather than
  guessed.
- **Prose drift between the tracks.** The `_shared/` fragment rule with a
  build-time check on language fences is the mitigation. Without the check the
  rule will erode within a few edits.
- **Scope.** Twenty lessons is a lot. The tiers are independently shippable, so
  if the schedule slips, Crawl plus Walk is a coherent release on its own and
  Run follows.

---

## 12. Knowledge-graph record

The architecture chosen here is recorded as a `Decision` node in the
`getting-started` project namespace, together with one `Decision` node per open
question in section 10 so they survive the session. Audit notes from Phase 2
become `Note` nodes, audited commit shas become `Fixture` nodes, and
verification failures become `Issue` nodes, per the tester agent's normal
workflow.
