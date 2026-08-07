# Vector similarity search

Vector search finds items most similar to a query in embedding space. An
embedding model maps text, images, or audio to a fixed-dimensional
vector, and cosine similarity (or Euclidean distance) between vectors
approximates semantic similarity between the original items.

Approximate nearest-neighbour indexes such as HNSW trade exact search
for logarithmic-time lookup, which matters when the corpus grows past a
few hundred thousand items.

Combining a knowledge graph with vector search gives you the best of both
worlds: follow relationships when they exist, and fall back to semantic
similarity when they do not.
