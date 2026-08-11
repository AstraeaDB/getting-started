# Getting Started with AstraeaDB

Source for the **Getting Started with AstraeaDB** site, published from `docs/`
to <https://astraeadb.github.io/getting-started/>.

Twenty lessons ordered **Crawl → Walk → Run**. Crawl gets a server running and
teaches the basics, with parallel Python and R tracks so a reader picks a
language once and stays in it. Walk covers embeddings, semantic search, and
GraphRAG. Run covers fraud and cyber investigation, and AI-assisted development.

Every code snippet on the site is executed in a container before publication.
Pages that are machine-checked say so in the footer, and `/status.html` shows
the full matrix including anything that was skipped and why.

## Build it

```bash
just build      # render content/ into docs/
just serve      # preview at http://127.0.0.1:8000
```

The build is [pandoc](https://pandoc.org) driven by `site/build.py`, which is
standard library only. There is no site generator and no JavaScript framework.
Two tools are resolved by absolute path because neither is reliably on `PATH`
here: pandoc at `/opt/homebrew/bin/pandoc`, and Python at
`/opt/homebrew/bin/python3` (the system `python3` is 3.10, which predates
`tomllib`). Override with `PANDOC=` and `PYTHON=` if yours live elsewhere.

## Verify it

```bash
just images           # build the four container images (first run is slow)
just verify crawl-py-01
just verify-all
```

Verification runs each lesson's code blocks inside a fresh container with its
own AstraeaDB server, so a lesson cannot pass by depending on state another
lesson left behind. `just images install` rebuilds from scratch, running the
exact `apt-get` and `cargo install` lines the lessons print, so building the
image *is* the test of the install instructions.

**Build one image at a time.** The Apple container builder defaults to 2 CPUs
and 2 GB, and two concurrent Rust builds will exhaust that and die with an
unhelpful signal (exit 133 or -5) rather than an out-of-memory message. If you
need more headroom:

```bash
container builder stop && container builder start --cpus 6 --memory 12g
```

Note the unit suffix on `--memory`. A bare number is parsed as zero bytes and
the builder refuses to start.

### Lessons that need Ollama

Walk lessons embed text, and a container cannot reach an Ollama bound to
`127.0.0.1`. The harness will not rebind yours, because an unauthenticated model
server should not be exposed on someone's behalf. Run a second instance on the
container bridge instead, which leaves `127.0.0.1:11434` working for your host
tools:

```bash
OLLAMA_HOST=192.168.64.1:11435 ollama serve &
VERIFY_OLLAMA_URL=http://192.168.64.1:11435 just verify walk-01-embeddings
```

Both instances share `~/.ollama`, so no model is downloaded twice. Without
`VERIFY_OLLAMA_URL` the harness looks at `http://192.168.64.1:11434` and, if
nothing answers, fails with these instructions rather than with a confusing
error from inside the lesson.

## Layout

```
lessons.toml        the manifest: every lesson's id, title, tier, track, order,
                    sibling, source, and verification policy
content/            lesson markdown, mirroring the published URL structure
  crawl/ walk/ run/
  _shared/          language-neutral fragments, included at build time
samples/            runnable code per lesson
data/               small redistributable sampled datasets
site/               build.py, pandoc templates, css and js
verify/             Dockerfiles and the extract/run/normalize harness
docs/               GENERATED. GitHub Pages serves this. Committed.
```

A lesson that is not in `lessons.toml` does not exist, and a lesson in
`lessons.toml` with no content file fails the build. That is what makes "every
lesson is reachable from the landing page" structurally true rather than
something a person has to remember.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. Prose follows five rules: no
em-dashes, no sentence fragments, warm but not familiar, no unexplained jargon,
and concepts explained before code appears. Those are acceptance criteria on
every content change, not suggestions. The accuracy rules matter more: use only
APIs that exist, verify every claimed number against a running server, and
never trust a check you have not watched fail.

Planning artifacts live alongside the source and are not published:
[`PROJECT.md`](PROJECT.md), [`CONCEPT.md`](CONCEPT.md) (the original brief), and
[`DESIGN.md`](DESIGN.md) (architecture, content inventory, task list, and the
open questions).

## Licence

The site, its code, and the harness are MIT licensed; see [`LICENSE`](LICENSE).

The sampled data under `data/` is not ours and carries its own terms. The LANL
slice is CC0, a public domain dedication, which is why it can ship here at all.
The Elliptic Bitcoin dataset is CC BY-NC-ND 4.0 and therefore is **not**
included: `run-01` generates a graph with the same shape instead, and
[`data/elliptic/README.md`](data/elliptic/README.md) explains how to fetch the
real thing under its own licence. Two public research datasets, opposite
answers about what you may pass on, which is worth checking every time rather
than assuming "public" means "yours to redistribute".
