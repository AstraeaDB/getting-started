# Manual checklist: `crawl-08-ui`

`crawl-08-ui` drives a browser, so it cannot run in the container harness
(DESIGN.md 7.4). This checklist is run by a human before each release, and
`/status.html` shows the lesson as manually checked with the date below rather
than as green.

**Last run: 2026-08-08**
**Result: toolchain and claims verified; browser interaction steps not yet driven**
**Against: astraea-ui `30df7a6`, AstraeaDB 0.3.1, cargo-leptos 0.3.5, rustc 1.95.0**

---

## Part 1: prerequisites and build (automated this run)

| # | Step | Result |
| --- | --- | --- |
| 1 | `https://github.com/AstraeaDB/astraea-ui` is public and clonable | **PASS**, HTTP 200, cloned at `30df7a6` |
| 2 | `rustup target add wasm32-unknown-unknown` | **PASS**, already installed |
| 3 | `cargo install cargo-leptos --version 0.3.5` | **PASS**, 0.3.5 installed and on crates.io |
| 4 | `npm install` | **NOT NEEDED**, see finding 1 |
| 5 | `npm install -g @tailwindcss/cli` | **NOT NEEDED**, see finding 1 |
| 6 | `cargo leptos build --release` completes | **PASS**, exit 0 in about 80 seconds total |
| 7 | Tailwind CSS is produced | **PASS**, `target/site/pkg/astraea-ui.css` is 34,326 bytes |
| 8 | Dashboard starts and serves | **PASS**, HTTP 200 at `http://127.0.0.1:3100/`, title "AstraeaDB Dashboard" |
| 9 | Stylesheet is served | **PASS**, HTTP 200, 34,326 bytes |
| 10 | Port matches the lesson | **PASS**, `Cargo.toml` sets `site-addr = "127.0.0.1:3100"` |
| 11 | `ASTRAEA_HOST` / `ASTRAEA_PORT` honoured, defaulting to 127.0.0.1:7687 | **PASS**, `src/server/config.rs:14` |

## Part 2: features the lesson names (source-verified this run)

Each was confirmed present in `astraea-ui/src`, but not yet exercised through a
browser.

| Claim | Evidence |
| --- | --- |
| Query Console | present, 4 files |
| Graph Explorer | present, 4 files |
| Graph Algorithms panel | present |
| "Find by Label" quick action | present, 2 files |
| PageRank overlay | present, 4 files |
| Louvain community detection | present, 4 files |
| Force layout | present, 3 files |
| Shortest path highlight | present in `app.rs`, `pages/graph.rs`, `shared/protocol.rs` |
| Export as PNG and JSON | `export_png` and `export_json` in `src/graph/bridge.rs`, with an "Export PNG" button at `pages/graph.rs:396` |
| Roles Reader, Writer, Admin | all three present in source |

## Part 3: browser steps still to be driven by a human

These need a person at a keyboard and are **not** done. Run them against a
server holding the movie graph from `crawl-py-01` or `crawl-r-01`.

- [ ] Log in with any key while authentication is off, and confirm Admin access.
- [ ] Run the co-star GQL query from the lesson and confirm a drawing appears
      rather than a table, given that it returns whole nodes and relationships.
- [ ] Use "Find by Label" to get a `Person` id, enter it as the Graph Explorer
      centre with depth 2, and confirm the second ring appears.
- [ ] Switch to the Force layout and confirm clusters separate.
- [ ] Filter by label and by edge type.
- [ ] Run PageRank and confirm high-scoring nodes are drawn larger.
- [ ] Run Louvain and confirm each community gets its own colour.
- [ ] Run shortest path between two actors from different franchises.
- [ ] Export a PNG and a JSON file, and reload the JSON.

---

## Findings

### 1. The lesson's Node.js prerequisite is unnecessary

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

This is worth fixing in the lesson, because it removes an entire toolchain from
the prerequisites for a reader who only wants to look at their graph. Suggested
change: drop the Node.js bullet and the `npm install` line, and note that
cargo-leptos fetches Tailwind on first build.

### 2. Two pinned versions are behind, though both still work

- `cargo-leptos`: the lesson pins **0.3.5**; the current release is **0.3.7**.
  0.3.5 is still on crates.io and installs cleanly, so the instruction works as
  written. Either bump the pin or drop the `--version` flag.
- Tailwind: cargo-leptos 0.3.5 requests **v4.1.10** and reports that **v4.3.3**
  is available, overridable with `LEPTOS_TAILWIND_VERSION`. Cosmetic, since the
  lesson does not name a Tailwind version.

A third version notice appears during the build: wasm-opt `version_123` is
requested while `version_131` exists, overridable with
`LEPTOS_WASM_OPT_VERSION`. Also cosmetic.

### 3. Build time is understated but not wrongly

The lesson says the first `cargo leptos watch` "takes a few minutes". A release
build here took about 80 seconds of compilation on an already-warm cargo
registry. A reader starting cold will be slower, so the claim is safe.

## How to re-run part 1

```bash
git clone https://github.com/AstraeaDB/astraea-ui.git
cd astraea-ui
cargo leptos build --release
LEPTOS_SITE_ROOT=target/site LEPTOS_SITE_ADDR=127.0.0.1:3100 ./target/release/astraea-ui
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/
```
