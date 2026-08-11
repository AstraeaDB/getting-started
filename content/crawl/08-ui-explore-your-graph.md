<!-- SEO subtitle (Medium meta description): Install the Astraea UI dashboard for AstraeaDB and explore your graph visually: run GQL queries, lay out subgraphs, and overlay PageRank and Louvain. -->

# See Your Graph: Visual Exploration with the Astraea UI

*Install the AstraeaDB dashboard and explore your movie graph with queries, visual layouts, and graph algorithms.*

In the earlier posts you built a movie knowledge graph and explored it with code. Code is precise, but a picture makes structure obvious at a glance. The Astraea UI is a web dashboard for AstraeaDB that draws your graph in the browser and lets you query it, arrange it, and run graph algorithms with a few clicks. This post installs the dashboard and uses it to explore the same movie graph you already built.

## What the dashboard is

The Astraea UI is a small web application that runs in your browser and talks to your AstraeaDB server. It has two main pages: a **Query Console** for running queries and drawing their results, and a **Graph Explorer** for walking outward from a node you choose. Both can run graph algorithms over what they are showing. The application is written in Rust and compiled to WebAssembly, usually shortened to WASM, which is a format that lets compiled code run inside a web page. You do not need to know Rust to use the dashboard. You only need Rust's tools to build it once.

## What you need

Because the dashboard is a Rust program, you need Rust's tools plus a couple of extras. Install the following:

- Rust itself, from [rustup.rs](https://rustup.rs), together with the WebAssembly build target, which you add with `rustup target add wasm32-unknown-unknown`.
- `cargo-leptos`, the build tool for Leptos (the Rust web framework the dashboard is built on). Install it with `cargo install cargo-leptos --locked`.

  The `--locked` matters. Without it, cargo re-resolves cargo-leptos's dependencies to their newest versions, and one of those may demand a newer Rust than you have. That is not hypothetical: on Rust 1.95, installing the current cargo-leptos without `--locked` fails with *"rustc 1.95.0 is not supported by the following package: kstring@2.0.4 requires rustc 1.96.0"*. With `--locked` you get the dependency versions the maintainers actually built and tested against, which is what you want for a tool you are only using to compile something else.
- Nothing else. The pages are styled with Tailwind CSS, and `cargo-leptos` downloads the Tailwind tool for you the first time you build, so you do not need Node.js or npm.

## Install and run it

Clone the repository, install its local dependencies, and start it in watch mode:

```bash
git clone https://github.com/AstraeaDB/astraea-ui.git
cd astraea-ui
cargo leptos watch
```

The first `cargo leptos watch` compiles the dashboard, which takes a few minutes. It also downloads the Tailwind tool on that first run, so expect a short pause before compilation starts. After that it serves the dashboard at `http://localhost:3100` and rebuilds automatically whenever you change a file.

If you ever rebuild the dashboard and then get an error like *"Could not deserialize error: Request did not meet this resource's requirements"* when you log in or run a query, **hard reload the page** (Cmd-Shift-R, or Ctrl-Shift-R). The browser is holding a cached copy of the old WebAssembly bundle, and it is calling server addresses the freshly built server no longer answers on. A hard reload fetches the new bundle and the error goes away. Make sure your AstraeaDB server is already running, using the `astraeadb serve` step from the getting-started posts. The dashboard connects to `127.0.0.1:7687` by default. If your server runs somewhere else, set the `ASTRAEA_HOST` and `ASTRAEA_PORT` environment variables before you start it.

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

The Graph Explorer draws a neighborhood of the graph starting from one node. It asks for a center node's ID and a depth, where depth is how many steps outward to follow. To find an ID, use the "Find by Label" quick action and choose `Person` or `Movie`, or read one from a query result, since every node the console returns includes its `id`. Enter that ID as the center and set the depth to 2. A depth of 1 shows only the immediate neighbors, while a depth of 2 brings in the next ring.

## Which way do the arrows point?

Next to the depth is a control labelled **Follow edges**, offering *either way*, *outgoing* and *incoming*. It looks like a minor setting and it is the most important control on the page, because on a directed graph it decides what you are even able to see.

Your movie graph runs one way. A person points at a film they acted in; a film points at its genres; nothing points back. So set **Outgoing**, start at Keanu Reeves, and ask for depth 2:

- You get seven of the twelve nodes: Keanu, his four films, and their two genres.
- You never see a co-star, no matter how large you make the depth. There is no arrow from a film back to a person, so there is no route.
- Raising the depth to 3, or 10, changes nothing at all. Two hops is as deep as this graph goes in that direction.

Now switch to **Incoming** and explore the same node. You get exactly one node: Keanu himself. Nothing in the database points at a person, so walking backwards from one is a dead end.

Switch to **Either way** and the picture opens up: all twelve nodes and all eighteen relationships. Ignoring direction, you can get from any node to any other, so a single starting point reaches everything.

The most telling test is to start somewhere that looks useless. Enter the ID of the `Action` genre and explore **Outgoing**: you get one node, because a genre is where every path ends. Nothing flows out of it. Switch that same node to **Either way** and the entire graph appears around it.

None of that is a defect. It is what direction *means*, and it is the difference between two genuinely different questions: "what does this thing point at" and "what is this thing connected to". Most exploration wants the second, which is why the control defaults to either way. But when you are tracing influence, or provenance, or the flow of money — anywhere the arrow carries meaning — the first is the only honest question, and following edges backwards would invent connections that do not exist.

This is the same distinction you will meet again in the algorithms below, where connected components will report that all twelve nodes are one piece while shortest path insists there is no route between two of them.

Once the graph is on screen, try the layout options. A Force layout lets connected nodes pull together while unrelated ones drift apart, which makes clusters easy to see. You can also filter by label or by edge type to hide everything except, for example, movies and the genres they belong to.

## Run graph algorithms

Algorithms run on the server and paint their result on top of the picture. They appear in two places, and the difference between them is not cosmetic:

- **In the Graph Explorer**, the Algorithms panel sits in the left sidebar and runs over **the whole database**.
- **In the Query Console**, an Algorithms row appears above the graph once a result is drawn, and runs over **only the nodes that query returned**.

Prefer the Query Console version when you have a question about a particular slice of the graph. Ranking Keanu's co-stars among themselves is a different question from ranking them against every node in the database, and on a large graph the second answer will tell you almost nothing about the first.

Whichever you use, a status line reports what happened: how many nodes were styled, how many groups were found, or that the algorithm returned nothing it could draw. Read it. A graph that looks unchanged after running an algorithm usually has a reason, and the status line is where the reason is.

- PageRank scores each node by how much it is pointed to by other important nodes, and how important those nodes are in turn. It is the idea that once ranked web pages. In a movie graph, prolific actors and widely shared genres score high, and the dashboard draws those nodes larger.
- Degree centrality is the blunter cousin: it counts connections without caring how important they are. Comparing the two is instructive, because a node can have many unimportant neighbours or few important ones.
- Louvain community detection groups nodes that connect to each other far more than they connect to the rest of the graph. On a movie graph those groups tend to line up with franchises and genres, and the dashboard gives each group its own color.
- Connected components asks a simpler question: which nodes can reach each other at all? On the movie graph the honest answer is "all of them", and the status line says so rather than leaving you staring at a single colour wondering whether the button worked. Components earn their keep on data that arrives in disconnected islands.
- [Shortest path](../glossary.html#shortest-path) highlights the fewest steps between two nodes you choose, and lives in the Graph Explorer only, because it needs two specific node IDs rather than a set. **Follow the arrows when you pick the two ends.** Your edges run one way, from a person to a film and from a film to a genre, so an actor can reach a genre — Keanu Reeves to Action lights up Keanu Reeves → The Matrix → Action — but one actor cannot reach another, and asking for that reports no path.

That last point is worth sitting with, because it looks like a contradiction. Connected components just told you all twelve nodes are in one piece, and yet there is no route from Laurence Fishburne to Sandra Bullock. Both answers are right: components ignores direction and asks "is this all one lump of graph", while shortest path obeys it and asks "can I walk from here to there". A graph can be a single connected lump that you still cannot traverse, and which question you are asking decides which answer you get.

## Save a picture

When a view looks the way you want, the Export button saves the current graph as a PNG image or as a JSON file. The image is handy for slides and documentation, and the JSON lets you reload the same view later or process it in another tool.

## Where this fits

You now have a visual way to explore the same graph you built with code. The Query Console answers precise questions and can run algorithms over the answer; the Graph Explorer reveals structure at a glance and runs them over everything. Between them the overlays surface the influence and the communities that you would otherwise have to compute by hand. If you have not built the movie graph yet, start with [Getting Started with AstraeaDB in R](./r-01-getting-started.md) or [Getting Started with AstraeaDB in Python](./py-01-getting-started.md), then come back here to see what you made.
