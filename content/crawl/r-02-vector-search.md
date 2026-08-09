<!-- SEO subtitle (Medium meta description): Add embeddings to your graph in R with AstraeaDB. Run vector similarity search, hybrid graph and vector queries, and semantic traversals to build a recommender. -->

# Vector and Hybrid Search with AstraeaDB in R

*Turn a movie graph into a recommender using embeddings, distance, and a blend of graph and vector search.*

In the first post, [Getting Started with AstraeaDB in R](./r-01-getting-started.md), we built a small movie knowledge graph made of actors, directors, genres, and the films that connect them. We walked that graph with [breadth-first search](../glossary.html#breadth-first-search-bfs) (a way of exploring outward one step at a time), shortest paths, and a little [GQL](../glossary.html#graph-query-language-gql) (Graph Query Language, a way of asking how nodes connect). That covered the *graph* half of AstraeaDB. This post covers the other half, which is vectors. A vector is simply a list of numbers, and an [embedding](../glossary.html#embedding) is a vector that places the meaning or "feel" of something at a point in space, so that similar things sit close together. Every node in AstraeaDB can carry an embedding, and the server keeps those embeddings in an [HNSW](../glossary.html#hierarchical-navigable-small-world-hnsw) index (short for Hierarchical Navigable Small World, a structure that finds nearby points quickly) right next to the graph. Because the two live together, we can ask which movies feel similar and which films are both close in the graph and close in meaning. Those two questions sit at the heart of a recommender.

## Reconnecting and rebuilding the graph, now with embeddings

If you followed the first post, you already have most of this code. The only new part is the `embedding` argument on `create_node`. First, make sure the server is running by launching `astraeadb serve` in another terminal, then connect:

```r
library(AstraeaDB)

if (!astraea_server_available()) stop("start `astraeadb serve` first")
client <- astraea_connect()   # host = "127.0.0.1", port = 7687L
```

Now we can add the movies. Each film gets a small four-number `plot` embedding. You can think of the four slots as rough "vibe" dials for action, science fiction, romance, and crime, in that order, so a cerebral science fiction film scores high on the second slot and a mob drama scores high on the fourth. In a real system you would never write these numbers by hand. Instead, you would run each plot summary through an embedding model, a program that reads text and returns a vector describing its meaning. That vector might be 384 or 1,536 numbers long, and every vector you later search with must have exactly the same number of slots, called its dimensions. These toy vectors let us run the examples without a model.

```r
movies <- list(
  matrix      = list(title = "The Matrix",    year = 1999L, plot = c(0.9, 0.8, 0.1, 0.2)),
  johnwick    = list(title = "John Wick",     year = 2014L, plot = c(0.9, 0.1, 0.1, 0.7)),
  inception   = list(title = "Inception",     year = 2010L, plot = c(0.7, 0.9, 0.2, 0.2)),
  bladerunner = list(title = "Blade Runner",  year = 1982L, plot = c(0.5, 0.9, 0.3, 0.4)),
  notebook    = list(title = "The Notebook",  year = 2004L, plot = c(0.1, 0.0, 0.9, 0.1)),
  godfather   = list(title = "The Godfather", year = 1972L, plot = c(0.2, 0.0, 0.3, 0.9))
)

ids <- list()
for (key in names(movies)) {
  m <- movies[[key]]
  ids[[key]] <- client$create_node(
    labels     = c("Movie"),
    properties = list(title = m$title, year = m$year),
    embedding  = m$plot          # <- the vector lives on the node
  )
}
```

A couple of actors and a genre give the graph some shape to traverse later:

```r
keanu <- client$create_node(c("Person"), list(name = "Keanu Reeves"))
leo   <- client$create_node(c("Person"), list(name = "Leonardo DiCaprio"))

client$create_edge(keanu, ids$matrix,   "ACTED_IN")
client$create_edge(keanu, ids$johnwick, "ACTED_IN")
client$create_edge(leo,   ids$inception, "ACTED_IN")

scifi <- client$create_node(c("Genre"), list(name = "Sci-Fi"))
client$create_edge(ids$matrix,      scifi, "IN_GENRE")
client$create_edge(ids$inception,   scifi, "IN_GENRE")
client$create_edge(ids$bladerunner, scifi, "IN_GENRE")
```

We also add one small helper that turns node IDs back into titles, so the results read nicely:

```r
title_of <- function(id) client$get_node(id)$properties$title
```

## Finding similar movies with `vector_search`

We are now ready to search. The `vector_search` method takes a query vector and returns the `k` nodes whose embeddings sit closest to it. Let us describe a mood, something like "cerebral, science fiction, a bit of action," as a vector with the same four slots, and ask for the closest films:

```r
cerebral_scifi <- c(0.7, 0.9, 0.15, 0.2)

hits <- client$vector_search(cerebral_scifi, k = 4L)
for (h in hits) {
  cat(sprintf("  %-14s  distance = %.3f\n", title_of(h$node_id), h$distance))
}
#>   Inception       distance = 0.005
#>   Blade Runner    distance = 0.034
#>   The Matrix      distance = 0.041
#>   John Wick       distance = 0.212
```

Each hit is a list holding a `node_id`, a `distance`, and a `score`. The field that matters most is `distance`, and the rule is simple: a smaller distance means a closer match. Distance here measures how far apart two vectors point rather than how far apart they sit, a method often called [cosine distance](../glossary.html#cosine-distance). A movie whose vector points the same way as the query lands near zero, while an unrelated one, such as a pure romance, sits much farther out. *Inception* and *Blade Runner* rise to the top because their vectors lean hardest on the science fiction slot, which is exactly the mood we asked for.

You will also see a `score` field on every hit. It is a legacy alias of `distance`, the same value under an older name, so do not read it as "higher is better." Prefer `distance`, and remember that a value closer to zero wins.

This is already a content-based recommender, one that suggests items by comparing their content rather than by watching what other people liked. You pick a movie a user enjoyed, feed its `plot` vector back in as the query, and the closest results become your "more like this" list.

## Blending graph and vector: `hybrid_search`

[Vector search](../glossary.html#vector-search) on its own ignores everything the graph knows, yet the fact that you watched a Keanu Reeves film is a useful signal too. [Hybrid search](../glossary.html#hybrid-search) combines both by weighing how similar the vectors are alongside how the nodes connect in the graph. The `hybrid_search` method starts from an anchor node, the node you begin from, explores the graph outward up to `max_hops` steps, and ranks the nodes it finds by a mix of graph proximity (how close they are to the anchor) and vector similarity (how close they are to a query vector). The `alpha` setting controls the blend:

- `alpha = 0.0` uses the graph only, ranking the anchor's nearest neighbors and ignoring embeddings.
- `alpha = 1.0` uses vectors only, which behaves essentially like `vector_search` and ignores the anchor.
- `alpha = 0.5` gives an even split between the two.

Let us anchor on Keanu Reeves and search with our cerebral science fiction vector. We want films that are both connected to Keanu's corner of the graph and a good match for the mood:

```r
recs <- client$hybrid_search(
  anchor       = keanu,
  query_vector = cerebral_scifi,
  max_hops     = 3L,
  k            = 4L,
  alpha        = 0.5
)
for (r in recs) {
  cat(sprintf("  %-14s  score = %.3f\n", title_of(r$node_id), r$score))
}
```

Hybrid results come back as pairs of `node_id` and `score`, where a higher `score` reflects a better combined match. With `alpha = 0.5`, *The Matrix* and *Inception* tend to lead, because they sit a couple of steps from Keanu (Keanu, then The Matrix, then Sci-Fi, then Inception) and they also match the query. If you nudge `alpha` toward `0.2`, the graph dominates, surfacing whatever is closest to Keanu regardless of mood. If you nudge it toward `0.8`, the vectors win, pulling in science fiction films Keanu never appeared in. This single setting is how you tune a recommender between "because you watched this" and "because it feels like this."

## Following a concept: `semantic_neighbors` and `semantic_walk`

Sometimes you do not have a full query vector in mind, only a general direction you want to move in. AstraeaDB lets you traverse the graph, meaning move from node to node along its edges, while steering toward a concept vector, an embedding that stands for the theme you care about. The `semantic_neighbors` method takes a starting node and a concept, then ranks that node's neighbors by how close they sit to the concept:

```r
near <- client$semantic_neighbors(
  node_id   = keanu,
  concept   = cerebral_scifi,
  direction = "outgoing",
  k         = 3L
)
for (n in near) {
  cat(sprintf("  %-14s  distance = %.3f\n", title_of(n$node_id), n$distance))
}
```

Keanu's outgoing neighbors are the films he acted in, and ranking them toward `cerebral_scifi` puts *The Matrix* ahead of *John Wick*. The results share the same `node_id` and `distance` shape as `vector_search`, and they follow the same rule, where a smaller distance means a closer match to the concept.

The `semantic_walk` method goes further. Instead of looking only one step out, it walks across the graph, hopping at each step toward whichever reachable node best matches the concept, up to `max_hops` steps. It follows a greedy path toward a theme, taking the best-looking choice at each step without planning further ahead:

```r
walk <- client$semantic_walk(
  start    = keanu,
  concept  = cerebral_scifi,
  max_hops = 3L
)
str(walk)   # the ordered path the walk took, steering toward the concept
```

Starting at Keanu and steering toward cerebral science fiction, the walk moves from Keanu into *The Matrix*, across the Sci-Fi genre, and on toward films like *Inception* or *Blade Runner*. These are nodes it would never reach in a single step, yet a concept-guided path connects them naturally. This is a recommender that explores: you give it a user's taste as a concept vector and let it wander the graph toward films that match.

When you're done, close the connection:

```r
client$disconnect()
```

## What's next

In a handful of calls, we have built the core of a recommender: content-based similarity with `vector_search`, a tunable blend of graph and vectors with `hybrid_search`, and concept-steered [traversal](../glossary.html#traversal) with `semantic_neighbors` and `semantic_walk`. Every one of these runs against the same store, with no separate vector database required.

In the final post, [Graph Algorithms, Time-Travel, and GraphRAG with AstraeaDB in R](./r-03-algorithms-graphrag.md), we will rank the most influential people and films with PageRank (an algorithm that scores a node by how many important nodes point to it), discover genre-like communities with Louvain (a method that groups tightly connected nodes together), add timestamped `RATED` edges so we can query the graph as it stood on a past date, and finish by connecting the graph to a [GraphRAG](../glossary.html#graphrag) pipeline, an approach that feeds graph results to a language model so it can answer questions with grounded facts. That post builds directly on the recommender we started here.
