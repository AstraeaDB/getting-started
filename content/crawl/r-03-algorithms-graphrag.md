<!-- SEO subtitle (Medium meta description): Advanced AstraeaDB in R: PageRank and Louvain graph algorithms, temporal time-travel queries, and GraphRAG for LLM-grounded answers over your own graph data. -->

# Graph Algorithms, Time-Travel, and GraphRAG with AstraeaDB in R

*Rank the most influential nodes, uncover hidden communities, rewind the graph to an earlier date, and let it answer questions in plain language, all from R.*

In [Getting Started with AstraeaDB in R](./r-01-getting-started.md) we built a small movie knowledge graph, a network of nodes joined by labeled links, and explored it with [breadth-first search](../glossary.html#breadth-first-search-bfs) (BFS, which fans out level by level from a starting node) and shortest paths. In [Vector and Hybrid Search with AstraeaDB in R](./r-02-vector-search.md) we added embeddings, which are numeric fingerprints of each item, and turned the graph into a recommender. This third and final post puts a graph database to fuller use. We will rank nodes by influence, group them into communities, query the graph as it existed on a past date, and close with [GraphRAG](../glossary.html#graphrag). GraphRAG hands a small connected slice of the graph (a [subgraph](../glossary.html#subgraph)) to a large language model ([LLM](../glossary.html#large-language-model-llm)), the kind of system behind chat assistants, so it can answer questions using your own data. There are no new dependencies to install, and everything runs against a local copy of the database started with `astraeadb serve`.

## Where we left off

If you worked through the first post, you already have this graph. If not, the block below rebuilds it from scratch. AstraeaDB is what its authors call a Vector-Property Graph. That means it stores labeled nodes and edges, each able to carry named properties (small pieces of data such as a title or a year), alongside a vector index for similarity search, all inside a single Rust program. Later, in the time-travel section, we will add `User` nodes and `RATED` edges.

```r
library(AstraeaDB)
if (!astraea_server_available()) stop("start `astraeadb serve` first")
client <- astraea_connect()   # host = "127.0.0.1", port = 7687L

add_movie  <- function(t, y) client$create_node("Movie",  list(title = t, year = y))
add_person <- function(n)    client$create_node("Person", list(name = n))
add_genre  <- function(n)    client$create_node("Genre",  list(name = n))
edge <- function(s, t, type) client$create_edge(s, t, edge_type = type)

m <- list(
  matrix    = add_movie("The Matrix", 1999L),
  reloaded  = add_movie("The Matrix Reloaded", 2003L),
  wick      = add_movie("John Wick", 2014L),
  inception = add_movie("Inception", 2010L),
  knight    = add_movie("The Dark Knight", 2008L),
  inter     = add_movie("Interstellar", 2014L))

p <- list(
  keanu = add_person("Keanu Reeves"),  lana  = add_person("Lana Wachowski"),
  nolan = add_person("Christopher Nolan"), leo = add_person("Leonardo DiCaprio"),
  bale  = add_person("Christian Bale"))

g <- list(scifi = add_genre("Sci-Fi"), action = add_genre("Action"),
          thriller = add_genre("Thriller"))

edge(p$keanu, m$matrix, "ACTED_IN"); edge(p$keanu, m$reloaded, "ACTED_IN")
edge(p$keanu, m$wick, "ACTED_IN");   edge(p$leo, m$inception, "ACTED_IN")
edge(p$bale, m$knight, "ACTED_IN")

edge(p$lana, m$matrix, "DIRECTED");  edge(p$lana, m$reloaded, "DIRECTED")
edge(p$nolan, m$inception, "DIRECTED"); edge(p$nolan, m$knight, "DIRECTED")
edge(p$nolan, m$inter, "DIRECTED")

edge(m$matrix, g$scifi, "IN_GENRE");    edge(m$reloaded, g$scifi, "IN_GENRE")
edge(m$inception, g$scifi, "IN_GENRE"); edge(m$inter, g$scifi, "IN_GENRE")
edge(m$matrix, g$action, "IN_GENRE");   edge(m$wick, g$action, "IN_GENRE")
edge(m$knight, g$action, "IN_GENRE");   edge(m$inception, g$thriller, "IN_GENRE")
edge(m$knight, g$thriller, "IN_GENRE")
```

We will print readable names often, so it helps to define one small helper first. `get_node()` returns a list with `labels` and `properties`, and each of our nodes carries either a `title` (for movies) or a `name` (for people and genres).

```r
label_of <- function(nid) {
  props <- client$get_node(as.integer(nid))$properties
  if (!is.null(props$title)) props$title else props$name
}
```

## Ranking influence with PageRank

PageRank is an algorithm that scores each node by how many important nodes point to it, and how important those pointing nodes are in turn. It is the same idea that once helped Google rank web pages: a page linked from many respected pages is judged important, and that importance flows along the links. In our movie graph, a film that many well-connected actors and directors touch, or a genre that ties lots of films together, rises to the top. The `run_pagerank()` method computes these scores inside the database and returns a named mapping from each node's id to its score.

```r
pr     <- client$run_pagerank()               # damping = 0.85 by default
scores <- sort(unlist(pr), decreasing = TRUE) # named numeric, high to low

for (nid in names(head(scores, 5))) {
  cat(sprintf("%-22s %.4f\n", label_of(nid), scores[[nid]]))
}
```

The most connected nodes lead the ranking, because many edges converge on them. Expect the `Sci-Fi` genre, `The Matrix`, and busy people such as Christopher Nolan near the top. You can tune the calculation with the `damping`, `max_iterations`, and `tolerance` arguments, though the defaults work well for a graph this small.

## Finding communities with Louvain

Where PageRank ranks individual nodes, Louvain community detection looks for groups. It is a method that splits the graph into clusters, called communities, whose members link to each other far more than they link to everything else. On a movie graph, those clusters tend to line up with genres and creative teams. The `run_louvain()` method returns the number of communities it found, along with a mapping from each node's id to the id of its community.

```r
lv   <- client$run_louvain()
cat("Communities found:", lv$num_communities, "\n")

comm   <- unlist(lv$communities)          # node_id -> community_id
groups <- split(names(comm), comm)        # community_id -> vector of node ids

for (cid in names(groups)) {
  members <- vapply(groups[[cid]], label_of, character(1))
  cat(sprintf("Community %s: %s\n", cid, paste(members, collapse = ", ")))
}
```

You can expect roughly a "Keanu / Matrix / John Wick" cluster and a "Nolan / Inception / Dark Knight" cluster, with each genre pulled toward whichever side it connects to most. You never had to tell the database which nodes belonged together, because the groupings emerged from the edges alone. That is one of the strengths of modeling data as a graph. To cluster only part of the graph, pass a vector of node ids through the `nodes` argument.

## Finding the bridges with betweenness centrality

Influence can mean more than one thing. Betweenness centrality measures how often a node sits on the [shortest path](../glossary.html#shortest-path) between two other nodes. Centrality here simply means a numeric score for how central, or well-placed, a node is within the network. A node with high betweenness acts as a bridge: a person who worked across two otherwise separate clusters, or a genre shared by rival franchises, can score high even when its PageRank is modest.

```r
bc <- client$run_betweenness_centrality()
for (nid in names(head(sort(unlist(bc), decreasing = TRUE), 3))) {
  cat(sprintf("%-22s %.4f\n", label_of(nid), unlist(bc)[[nid]]))
}
```

AstraeaDB includes several related measures. The `run_degree_centrality()` method counts each node's raw number of connections and accepts a `direction` argument, while `run_connected_components()` reports which separate islands of nodes exist. Use degree centrality when you care about sheer popularity, and betweenness when you care about which nodes hold the network together.

## Time travel: the graph as of a past date

This is a feature that most databases lack. Every edge can carry a `valid_from` timestamp, recorded as epoch milliseconds (the number of milliseconds since the start of 1970, a common way to store a date as a plain number). Because each edge remembers when it became valid, AstraeaDB can answer a query as if you were standing at any chosen moment in the past. This ability to ask historical questions is often called a temporal, or time-travel, query. To try it, we add a few users and ratings that happened on specific dates.

```r
u <- list(alice = client$create_node("User", list(name = "Alice")),
          bob   = client$create_node("User", list(name = "Bob")))

# convert a date to epoch-milliseconds
ts <- function(date) as.numeric(as.POSIXct(date, tz = "UTC")) * 1000

client$create_edge(u$alice, m$matrix,    edge_type = "RATED",
                   properties = list(rating = 5L), valid_from = ts("2023-01-10"))
client$create_edge(u$alice, m$inception, edge_type = "RATED",
                   properties = list(rating = 4L), valid_from = ts("2024-06-01"))
client$create_edge(u$bob,   m$wick,      edge_type = "RATED",
                   properties = list(rating = 5L), valid_from = ts("2024-02-15"))
```

Now we can ask what Alice had rated as of New Year's Day 2024. Her `Inception` rating is dated June 2024, so at that cutoff it should not exist yet, because an edge with a `valid_from` timestamp only comes into being from that moment onward.

```r
cutoff <- ts("2024-01-01")

client$neighbors_at(u$alice, "outgoing", cutoff)   # only the Matrix rating
client$bfs_at(u$alice, max_depth = 2L, timestamp = cutoff)
```

The `neighbors_at` method returns only the `RATED` edge to `The Matrix`, because the `Inception` rating has not happened yet at that timestamp. The `bfs_at` method applies the same historical snapshot but walks several hops outward from Alice, where a hop means one step along an edge, instead of stopping at her immediate neighbors. This is genuinely useful in practice: you can reproduce a recommendation exactly as a user saw it last quarter, or check what the graph knew before a particular event. The `dfs_at` and `shortest_path_at` methods complete the set of time-aware traversals.

## Zooming in with subgraphs and statistics

Before handing any data to a language model, it helps to look at the neighborhood we are working with. A subgraph is simply a smaller piece cut out of the full graph: a chosen node plus the nodes and edges around it. The `graph_stats()` method gives a high-level count of everything in the store, and `get_subgraph()` pulls out a bounded region centered on one node.

```r
stats <- client$graph_stats()
cat("Nodes:", stats$total_nodes, "Edges:", stats$total_edges, "\n")

sub <- client$get_subgraph(m$matrix, hops = 2L, max_nodes = 25L)
cat("Subgraph:", length(sub$nodes), "nodes,", length(sub$edges), "edges\n")
```

Reaching two hops out from `The Matrix` gathers its cast, its directors, its genres, and the sibling movies that those genres connect to. The result is a tidy, self-contained slice of the graph.

## GraphRAG: from subgraph to answer

GraphRAG is a form of retrieval-augmented generation, usually shortened to [RAG](../glossary.html#retrieval-augmented-generation-rag). In ordinary RAG, a program first retrieves some relevant documents and then asks a language model to write an answer using them, so the answer is grounded in real source material rather than the model's memory. GraphRAG follows the same recipe, except the retrieved material is a subgraph rather than loose chunks of text. AstraeaDB splits the work into two steps, and the first needs no language model at all. The `extract_subgraph()` method turns a neighborhood into plain, readable text that you can inspect, log, or store for reuse.

```r
context <- client$extract_subgraph(m$matrix, hops = 2L, max_nodes = 25L,
                                   format = "structured")
# The call returns a list: nodes_count, edges_count, estimated_tokens, text.
cat(context$nodes_count, "nodes,", context$edges_count, "edges\n")
cat(context$text)   # human-readable context, no model required
```

That text is exactly what the model will be given: the nodes, their properties, and the edges between them, written out as prose. Being able to read it is a real advantage when debugging, since plain vector-based RAG usually hides the material it retrieved.

The second step, `graph_rag()`, does the same retrieval and packages it together with your question, returning a list of `question`, `context`, `nodes_in_context`, `edges_in_context`, `estimated_tokens`, `anchor_node_id`, and `note`. Writing the final answer needs a language model, and that has to be configured on the server, for example a local [Ollama](https://ollama.com) instance or an API key set in the server's environment. Until you configure one the call still succeeds and still does the retrieval, and `note` tells you that completion is unavailable. Once a provider is configured, the same call also returns the generated answer.

```r
answer <- client$graph_rag(
  question  = "Who directed The Matrix, and what genres is it in?",
  anchor    = m$matrix,
  hops      = 2L,
  max_nodes = 25L)
cat(answer$nodes_in_context, "nodes in context,",
    answer$estimated_tokens, "estimated tokens\n")
cat(answer$note, "\n")
```

Because the answer is built from a retrieved subgraph rather than the model's own memory, it stays faithful to your data, and you can always point to the exact `extract_subgraph()` text that produced it.

```r
client$disconnect()
```

## Wrapping up the series

Across three posts, you have gone from an empty database to a capable graph application written entirely in R. The first post covered the fundamentals: connecting, modeling nodes and edges, and traversing them. The second added embeddings for vector and [hybrid search](../glossary.html#hybrid-search), turning the graph into a recommender. This post added the analysis and reasoning layer: PageRank and Louvain for structure, betweenness centrality for the bridge nodes, time-travel queries for point-in-time answers, and GraphRAG to turn all of it into plain-language responses.

The common thread is that AstraeaDB keeps graph structure, vector similarity, temporal history, and language-model grounding in a single store, all reachable through a few `client$...` calls. You can swap the small movie dataset for your own domain, whether that is customers and orders, papers and citations, or services and their dependencies, and the same handful of methods still apply. From here, you might generate real embeddings with a dedicated model, connect a language-model provider so that `graph_rag()` works, and explore the `query()` interface, which accepts [GQL](../glossary.html#graph-query-language-gql) (Graph Query Language, an emerging standard for querying graphs) for anything the R6 methods do not cover. Everything shown here has an equivalent in the parallel Python series.
