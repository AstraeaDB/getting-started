# Manual checklist: `crawl-08-ui`

`crawl-08-ui` drives a browser, so it cannot run in the container harness
(DESIGN.md 7.4). This checklist is run by a human before each release, and
`/status.html` shows the lesson as manually checked with the date below rather
than as green.

**Last run: 2026-08-11**
**Result: browser run found four broken algorithm overlays; fixed in astraea-ui `da2409a`; re-run of the browser steps still owed**
**Against: astraea-ui `72a93b9`, AstraeaDB `61eef42` (0.3.1), cargo-leptos 0.3.5 and 0.3.7, rustc 1.95.0**

---

## Part 1: prerequisites and build (automated this run)

| # | Step | Result |
| --- | --- | --- |
| 1 | `https://github.com/AstraeaDB/astraea-ui` is public and clonable | **PASS**, HTTP 200, cloned at `30df7a6` |
| 2 | `rustup target add wasm32-unknown-unknown` | **PASS**, already installed |
| 3 | `cargo install cargo-leptos --locked` | **PASS**, 0.3.7 installs and builds the dashboard; see finding 2 |
| 4 | `npm install` | **NOT NEEDED**, see finding 1 |
| 5 | `npm install -g @tailwindcss/cli` | **NOT NEEDED**, see finding 1 |
| 6 | `cargo leptos build --release` completes | **PASS**, exit 0 in about 80 seconds total |
| 7 | Tailwind CSS is produced | **PASS**, `target/site/pkg/astraea-ui.css` is 34,326 bytes |
| 8 | Dashboard starts and serves | **PASS**, HTTP 200 at `http://127.0.0.1:3100/`, title "AstraeaDB Dashboard" |
| 9 | Stylesheet is served | **PASS**, HTTP 200, 34,326 bytes |
| 10 | Port matches the lesson | **PASS**, `Cargo.toml` sets `site-addr = "127.0.0.1:3100"` |
| 11 | `ASTRAEA_HOST` / `ASTRAEA_PORT` honoured, defaulting to 127.0.0.1:7687 | **PASS**, `src/server/config.rs:14` |

## Part 2: features the lesson names

> **This section used to list "present in `astraea-ui/src`" as evidence, and
> that is how four broken features passed a review.** Presence in source says a
> button exists, not that pressing it does anything. Every row below now names
> the behaviour to observe, and a row is only ticked by someone who watched it
> happen. See finding 4.

| Claim | How to check it | Last observed |
| --- | --- | --- |
| Query Console runs GQL | a query returns rows or a drawing | 2026-08-11, works |
| Graph Explorer walks outward | centre + depth 2 draws a second ring | not re-run |
| "Find by Label" quick action | returns node ids for `Person` | not re-run |
| Algorithms on Graph Explorer | status line names a node count | fixed, not re-run |
| Algorithms on Query Console | row appears above the result graph | new, not re-run |
| PageRank overlay | high scorers are visibly larger | **was broken**, fixed |
| Degree centrality overlay | node sizes change | **was broken**, fixed |
| Louvain overlay | groups take distinct colours | **was broken**, fixed |
| Connected components overlay | status says "one connected component" | **was broken**, fixed |
| Shortest path highlight | route between two ids lights up | 2026-08-11, works |
| Force layout | clusters separate | not re-run |
| Export as PNG and JSON | files download and the JSON reloads | not re-run |
| Roles Reader, Writer, Admin | log in and observe available actions | not re-run |

## Part 3: browser steps still to be driven by a human

These need a person at a keyboard. Run them against a server holding the movie
graph from `crawl-py-01` or `crawl-r-01`. Node ids on that graph: 575 Keanu
Reeves, 576 Carrie-Anne Moss, 577 Laurence Fishburne, 578 Sandra Bullock,
579 Lana Wachowski, 580 Chad Stahelski, 581 The Matrix, 582 The Matrix
Reloaded, 583 John Wick, 584 Speed, 585 Science Fiction, 586 Action.

- [X] Log in with any key while authentication is off, and confirm Admin access.
- [X] Run the co-star GQL query from the lesson and confirm a drawing appears
      rather than a table, given that it returns whole nodes and relationships.
- [X] Use "Find by Label" to get a `Person` id, enter it as the Graph Explorer
      centre with depth 2, and confirm the second ring appears.
- [X] Switch to the Force layout and confirm clusters separate.
- [X] Filter by label and by edge type.
- [X] Export a PNG and a JSON file, and reload the JSON.

### Algorithms — the part that was broken

Run each of these **twice**: once in the Graph Explorer sidebar, once in the
Algorithms row above the Query Console's graph tab. Check the status line every
time; a silent overlay is the failure this section exists to catch.

Expected results on the twelve-node movie graph, taken from the server on
2026-08-11 so a plausible-looking overlay can be told from a correct one.

- [ ] **PageRank.** Sizes visibly differ; status names a node count. Largest
      first: Action (0.267), Science Fiction (0.125), then The Matrix and
      The Matrix Reloaded (0.100 each). The genres win because every film
      points at them.
- [ ] **Degree centrality.** Sizes change, and the order is *different* from
      PageRank: Keanu Reeves (0.364) is the largest, then a four-way tie at
      0.182. If this looks identical to PageRank, one of the two is not being
      applied.
- [ ] **Louvain.** Four colours: {Keanu Reeves, Sandra Bullock, Speed},
      {Carrie-Anne Moss, Science Fiction, The Matrix Reloaded},
      {Lana Wachowski, Laurence Fishburne, The Matrix},
      {Action, Chad Stahelski, John Wick}.
- [ ] **Connected components.** One colour **and** a status line reading
      "All 12 nodes are in one connected component". One colour with no such
      message means the overlay silently failed again. Note this ignores edge
      direction, which is why it can report one component while shortest path
      below finds no route between two of its members.
- [ ] **Scoping.** Run PageRank in the Query Console on the co-star query, then
      in the Graph Explorer over the whole database, and confirm the two give
      different sizes. If they match, the Query Console is not scoping to its
      result and the `nodes` field is being dropped.
- [ ] **Shortest path** (Graph Explorer only). Edges are directed, so pick
      ends the arrows can actually connect: **575 -> 586** (Keanu Reeves to
      Action) lights up Keanu Reeves → The Matrix → Action, 2 hops. Two actors
      never work — 577 -> 578 correctly reports no path, because nothing leads
      back down from a genre to a person. An earlier version of this checklist
      asked for exactly that and would have read as a bug.
- [ ] **Reset.** Clears sizes and colours and empties the status line.

---

## Findings

### 1. The lesson's Node.js prerequisite is unnecessary  *(fixed in `f579fb4`)*

The lesson asks the reader to install Node.js 18 or newer, run `npm install`,
and run `npm install -g @tailwindcss/cli`. **None of that is needed.** This
machine has no Node and no npm at all, and the build still succeeded with a
fully styled 34 KB stylesheet.

cargo-leptos handles it. The build log warns

    'node_modules' folder not found, please install the required packages first
    continuing without using 'node_modules'

and then downloads a standalone Tailwind binary to
`~/Library/Caches/cargo-leptos/tailwindcss-v4.1.10` and runs it directly. The
`tailwindcss` entry in the repository's `package.json` is therefore optional.

This removed an entire toolchain from the prerequisites for a reader who only
wants to look at their graph. Applied in `f579fb4`: the Node.js bullet and both
`npm install` lines are gone, and the "What you need" list now ends with
"Nothing else … so you do not need Node.js or npm".

### 2. The `cargo-leptos` pin was hiding a broken install line  *(fixed 2026-08-11)*

Recorded originally as cosmetic: the lesson pinned **0.3.5** while **0.3.7** was
current, and 0.3.5 still installs cleanly. The suggested fix was to bump the pin
or drop `--version`.

**Dropping `--version` would have shipped an instruction that fails.** Tested on
this machine (rustc 1.95.0), `cargo install cargo-leptos --version 0.3.7` errors:

    rustc 1.95.0 is not supported by the following package:
      kstring@2.0.4 requires rustc 1.96.0
    Try re-running `cargo install` with `--locked`

Without `--locked`, cargo re-resolves the whole dependency tree to newest, and a
transitive dependency has raised its minimum Rust past what the reader has. A
pinned cargo-leptos version does not protect against this, because the pin
constrains cargo-leptos and not its dependencies — 0.3.5 will hit the same wall
as its own dependencies move.

The lesson now says `cargo install cargo-leptos --locked` with no version pin,
and explains why, quoting the error. `--locked` uses the lockfile the
maintainers published, so the reader gets the dependency versions cargo-leptos
was actually built against. No pin means the line does not go stale.

Verified end to end, without disturbing the installed 0.3.5:

    cargo install cargo-leptos --version 0.3.7 --locked --root <scratch>
    <scratch>/bin/cargo-leptos build --release      # Finished in 1m 04s
    # binary serves 200 on /, /query and /graph

**Watch out when repeating this.** `site-root = "target/site"` in `Cargo.toml`
is project-relative, so `CARGO_TARGET_DIR` moves the compiled binary but *not*
the generated WASM and CSS. A scratch build still overwrites `target/site/pkg/`
and therefore what a already-running dashboard serves. Rebuild with the normal
toolchain and restart the dashboard afterwards.

Two remaining version notices are genuinely cosmetic: cargo-leptos 0.3.5
requests Tailwind v4.1.10 while v4.3.3 exists (`LEPTOS_TAILWIND_VERSION`), and
wasm-opt `version_123` is requested while `version_131` exists
(`LEPTOS_WASM_OPT_VERSION`). The lesson names neither version.

### 3. Build time is understated but not wrongly

The lesson says the first `cargo leptos watch` "takes a few minutes". A release
build here took about 80 seconds of compilation on an already-warm cargo
registry. A reader starting cold will be slower, so the claim is safe.

### 4. Four of the five algorithms did nothing, and said they had  *(fixed)*

Found by clicking the buttons, which no previous run had done. Pressing
"Connected Components" showed the banner *"Components applied (node color =
component)"* above a graph where every node kept its original colour.

The page parsed every algorithm response as a bare `{nodeId: value}` map. The
server does not send that. It wraps each result in a named field, and the field
differs per algorithm — captured live from AstraeaDB `61eef42`:

```text
RunPageRank            {"scores": {"575": 0.04, ...}}
RunDegreeCentrality    {"scores": {"575": 0.36, ...}}
RunLouvain             {"communities": {...}, "num_communities": 4}
RunConnectedComponents {"components": [[575, 581, ...]], "count": 1}
ShortestPath           {"path": [575, 581, 586], "length": 2}
```

PageRank and degree centrality matched nothing and returned early. Louvain and
components matched only the sibling scalar, so the page styled nodes literally
named `num_communities` and `count`, which do not exist. Only shortest path
worked, because its response happens to have the `path` key the code expected.

The status bar reported success either way, which is what kept this invisible.

Fixed in astraea-ui `da2409a`: parsing moved to `graph::overlays` with tests
pinned to the captured JSON above, and every handler now reports the node count
it actually styled. Connected components on a fully connected graph now says
"All 12 nodes are in one connected component" instead of leaving one colour to
speak for itself.

**Why the earlier review missed it.** Part 2 of this checklist accepted
"present in `astraea-ui/src`, 4 files" as evidence for "PageRank overlay". Every
one of those files was real. `grep` cannot tell a wired-up feature from a
disconnected one, and a check that cannot fail is not a check. Part 2 now names
an observable behaviour per row.

### 5. The lesson implied algorithms were on the Query Console  *(fixed both sides)*

The lesson described "three main areas: a Query Console, a Graph Explorer, and a
panel of graph algorithms", which reads as though the panel is available
wherever you are. It was in the Graph Explorer sidebar only, and a reader who
ran a query and got a picture had no way to analyse it.

Both halves changed. astraea-ui `da2409a` adds the four algorithms to the Query
Console, scoped via the protocol's `nodes` field to the ids the query returned —
the right question for that page, since ranking a result's nodes against the
whole database answers something else. The lesson now names two pages rather
than three areas and says which scope each one uses.

### 6. A stale browser cache breaks every server call after a rebuild  *(fixed in astraea-ui `72a93b9`)*

Symptom, seen on the login page right after the dashboard was rebuilt:

    error deserializing server function results: Could not deserialize error
    "Request did not meet this resource's requirements."

Nothing was wrong with the server. Leptos routes each server function at a path
made of its snake-case name **plus a hash**, and that hash is not per-function.
Measured across the two commits either side of the overlay fix, altering four
signatures moved **all fourteen** paths, including the ten that were not
touched. A comment-only change, tested separately, moves none — so it is a
signature change anywhere in the crate that invalidates every path, not merely
editing the file:

    30df7a6  /api/login17300062197879492894
    da2409a  /api/login11596859232311602335

The browser had cached `pkg/astraea-ui.wasm` from before the rebuild, so it kept
POSTing to the old path. Nothing serves that path any more, so the request falls
through to the `Files` service, which allows only GET and answers `405 Method
Not Allowed` with the plain-text body above. The client then fails to parse that
plain text as a serialized `ServerFnError`, which produces the doubly-confusing
"could not deserialize the error" wording.

Reproduced exactly against the running server:

    POST /api/login17300062197879492894  ->  405, "Request did not meet ..."
    POST /api/login11596859232311602335  ->  200, {"authenticated":true,...}

**Fix for a reader: hard reload** (Cmd-Shift-R). The bundle is served from
`target/site/pkg` under fixed filenames with no `Cache-Control` and no content
hash in the name, so an ordinary reload can reuse the stale WASM.

This is a real trap for anyone following the lesson, because `cargo leptos
watch` rebuilds on every file change. Its live-reload usually refreshes the page
for you; when the dashboard is restarted by hand instead, nothing tells the
browser its bundle is stale.

**Fixed upstream** in astraea-ui `72a93b9`: `/pkg` is now served with
`Cache-Control: no-cache`, so the browser revalidates before reuse. Unchanged
bundles still answer 304 from their ETag, so the cost is one conditional
request per load. Verified by caching a bundle's ETag, rebuilding, and
confirming the conditional request now returns 200 with fresh bytes.

Content-hashed filenames were considered and rejected. `hash-files` is read at
runtime from `LEPTOS_HASH_FILES`, but `main.rs` calls `get_configuration(None)`,
which is env-driven; a build with hashing enabled that is then run as a bare
`./astraea-ui` would serve HTML pointing at filenames that do not exist. That
is a worse failure than the one being fixed, and it is exactly the standalone
invocation this checklist uses.

**Check before blaming the browser:** compare what the two halves expect.

    strings target/release/astraea-ui | grep -oE '/api/[a-z_]+[0-9]{8,}' | sort -u
    curl -s localhost:3100/pkg/astraea-ui.wasm | strings \
      | grep -oE '/api/[a-z_]+[0-9]{8,}' | sort -u

Those two lists must be identical. If they are, the server is fine and the
browser is stale.

## How to re-run part 1

```bash
git clone https://github.com/AstraeaDB/astraea-ui.git
cd astraea-ui
cargo install cargo-leptos --locked   # --locked is load-bearing; see finding 2
cargo leptos build --release
LEPTOS_SITE_ROOT=target/site LEPTOS_SITE_ADDR=127.0.0.1:3100 ./target/release/astraea-ui
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/
```
