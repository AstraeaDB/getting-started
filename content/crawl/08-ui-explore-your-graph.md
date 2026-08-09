<!-- SEO subtitle (Medium meta description): Install the Astraea UI dashboard for AstraeaDB and explore your graph visually: run GQL queries, lay out subgraphs, and overlay PageRank and Louvain. -->

# See Your Graph: Visual Exploration with the Astraea UI

*Install the AstraeaDB dashboard and explore your movie graph with queries, visual layouts, and graph algorithms.*

In the earlier posts you built a movie knowledge graph and explored it with code. Code is precise, but a picture makes structure obvious at a glance. The Astraea UI is a web dashboard for AstraeaDB that draws your graph in the browser and lets you query it, arrange it, and run graph algorithms with a few clicks. This post installs the dashboard and uses it to explore the same movie graph you already built.

## What the dashboard is

The Astraea UI is a small web application that runs in your browser and talks to your AstraeaDB server. It has three main areas: a Query Console for running queries, a Graph Explorer for seeing the graph as a picture, and a panel of graph algorithms. The application is written in Rust and compiled to WebAssembly, usually shortened to WASM, which is a format that lets compiled code run inside a web page. You do not need to know Rust to use the dashboard. You only need Rust's tools to build it once.

## What you need

Because the dashboard is a Rust program, you need Rust's tools plus a couple of extras. Install the following:

- Rust itself, from [rustup.rs](https://rustup.rs), together with the WebAssembly build target, which you add with `rustup target add wasm32-unknown-unknown`.
- `cargo-leptos`, the build tool for Leptos (the Rust web framework the dashboard is built on). Install it with `cargo install cargo-leptos --version 0.3.5`.
- Nothing else. The pages are styled with Tailwind CSS, and `cargo-leptos` downloads the Tailwind tool for you the first time you build, so you do not need Node.js or npm.

## Install and run it

Clone the repository, install its local dependencies, and start it in watch mode:

```bash
git clone https://github.com/AstraeaDB/astraea-ui.git
cd astraea-ui
cargo leptos watch
```

The first `cargo leptos watch` compiles the dashboard, which takes a few minutes. It also downloads the Tailwind tool on that first run, so expect a short pause before compilation starts. After that it serves the dashboard at `http://localhost:3100` and rebuilds automatically whenever you change a file. Make sure your AstraeaDB server is already running, using the `astraeadb serve` step from the getting-started posts. The dashboard connects to `127.0.0.1:7687` by default. If your server runs somewhere else, set the `ASTRAEA_HOST` and `ASTRAEA_PORT` environment variables before you start it.

## Log in

Open `http://localhost:3100` and you will see a login screen. If your server has authentication turned off, which is the default, type any value as the key and you will be signed in with full Admin access. When a server has authentication enabled instead, your key decides your role, which is one of Reader, Writer, or Admin.

## Run a query that draws a graph

The Query Console runs [GQL](../glossary.html#graph-query-language-gql), the graph query language you met in the earlier posts. One habit is worth learning here. To get a picture back rather than a table, return whole nodes and the relationships between them, not individual properties. Returning `p.name` gives you text in a table, while returning `p` hands the dashboard a full node it can draw. Try Keanu Reeves and his co-stars:

```
MATCH (keanu:Person {name: 'Keanu Reeves'})-[r1:ACTED_IN]->(m:Movie)<-[r2:ACTED_IN]-(costar:Person)
RETURN keanu, r1, m, r2, costar
```

This reads as a sentence: find Keanu, follow his `ACTED_IN` links to the movies he is in, then follow `ACTED_IN` links backward from those movies to everyone else who appeared in them. Returning the people, the movies, and the two relationships gives the dashboard a small connected graph with Keanu at the center, his films around him, and every co-star attached. If the console shows the result as a table or as raw data instead of a drawing, do not worry, because the same node and relationship data is what the Graph Explorer renders as a picture.

## Explore the graph by hand

The Graph Explorer draws a neighborhood of the graph starting from one node. It asks for a center node's ID and a depth, where depth is how many steps outward to follow. To find an ID, use the "Find by Label" quick action and choose `Person` or `Movie`, or read one from a query result, since every node the console returns includes its `id`. Enter that ID as the center and set the depth to 2. A depth of 1 shows only the immediate neighbors, while a depth of 2 brings in the next ring, so an actor expands into their films and then into those films' genres and co-stars.

Once the graph is on screen, try the layout options. A Force layout lets connected nodes pull together while unrelated ones drift apart, which makes clusters easy to see. You can also filter by label or by edge type to hide everything except, for example, movies and the genres they belong to.

## Run graph algorithms

The Graph Algorithms panel runs a calculation on the server and shows the result on top of the picture.

- PageRank scores each node by how much it is pointed to by other important nodes, and how important those nodes are in turn. It is the idea that once ranked web pages. In a movie graph, prolific actors and widely shared genres score high, and the dashboard draws those nodes larger.
- Louvain community detection groups nodes that connect to each other far more than they connect to the rest of the graph. On a movie graph those groups tend to line up with franchises and genres, and the dashboard gives each group its own color.
- [Shortest path](../glossary.html#shortest-path) highlights the fewest steps between two nodes you choose. Picking two actors from different franchises makes a good test, because the highlighted route shows how the whole graph is connected through the films they share.

## Save a picture

When a view looks the way you want, the Export button saves the current graph as a PNG image or as a JSON file. The image is handy for slides and documentation, and the JSON lets you reload the same view later or process it in another tool.

## Where this fits

You now have a visual way to explore the same graph you built with code. The Query Console answers precise questions, the Graph Explorer reveals structure at a glance, and the algorithm overlays surface the influence and the communities that you would otherwise have to compute by hand. If you have not built the movie graph yet, start with [Getting Started with AstraeaDB in R](./r-01-getting-started.md) or [Getting Started with AstraeaDB in Python](./py-01-getting-started.md), then come back here to see what you made.
