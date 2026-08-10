<!-- SEO subtitle (meta description): Build a GraphRAG pipeline on AstraeaDB: retrieve an anchor, extract a subgraph, linearize it to text, and answer a question grounded in nodes you can inspect. -->

# GraphRAG End to End: Retrieve, Extract, Linearize, Answer

*Find the right corner of the graph, turn it into text, and get an answer where every claim traces back to something you can look at.*

You have a graph built from prose, with a trail from every entity back to the passage it came from. Now you will use it to answer a question. The pipeline has four stages, and it is worth naming them, because each one can be inspected and each one can be the thing that is wrong.

**Retrieve** a starting node. **Extract** the neighbourhood around it. **Linearize** that neighbourhood into plain text. **Answer** the question using only that text.

## Building a slightly larger graph

Three passages give the graph enough to be interesting. This is the same extraction loop from the previous post, with one addition explained shortly:

```python
import json
import os
import urllib.request

from astraeadb import AstraeaClient

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma3:4b")


def post(path, body):
    req = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.load(resp)


def embed(texts):
    return post("/api/embed", {"model": "embeddinggemma", "input": texts})["embeddings"]


def chat(prompt, fmt=None):
    body = {"model": CHAT_MODEL, "prompt": prompt, "stream": False}
    if fmt:
        body["format"] = fmt
    return post("/api/generate", body)["response"]


PASSAGES = [
    ("mail coach", "“There is nothing to apprehend. I belong to Tellson’s Bank. You must know Tellson’s Bank in London. I am going to Paris on business. Jerry, say that my answer was, RECALLED TO LIFE.”"),
    ("Dover hotel", "Mr. Lorry made his formal bow to Miss Manette at the hotel in Dover. “Miss Manette, I am a man of business. I have a business charge to acquit myself of. I will relate to you the story of one of our customers at Tellson’s Bank.”"),
    ("wine shop", "Monsieur Defarge kept a wine shop in the Saint Antoine quarter of Paris. Madame Defarge, his wife, sat in the shop behind the counter, a stout woman with a watchful eye and great composure of manner."),
]

PROMPT = """Extract named entities. Return ONLY JSON:
{"characters":[{"name":"...","description":"..."}],"locations":[{"name":"...","description":"..."}]}
A character is a person. A location is a place or named organisation.
Use only what the passage states. Do not invent anything.

Passage:
"""

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

entities = {}
passages = []
for label, text in PASSAGES:
    pid = client.create_node(
        ["Passage"], {"text": text, "label": label}, embedding=embed([text])[0])
    passages.append(pid)
    found = json.loads(chat(PROMPT + text, fmt="json"))
    for kind, key in (("Character", "characters"), ("Location", "locations")):
        items = found.get(key) or []
        if not items:
            continue
        texts = [f'{i["name"]}. {i.get("description", "")}'.strip() for i in items]
        for item, vec in zip(items, embed(texts)):
            name = item["name"]
            if name not in entities:           # the same name across passages
                entities[name] = client.create_node(   # is one node, not three
                    [kind], {"name": name, "description": item.get("description", "")},
                    embedding=vec)
            client.create_edge(entities[name], pid, "MENTIONED_IN")

print(len(entities), "entities:", sorted(entities))
```

Two things to notice in the output. Names repeated across passages become a single node, which is why Tellson's Bank appears once even though two passages mention it. And the list probably contains an entity called `I`, extracted from a first-person sentence. That is a genuine extraction mistake, it is the sort of thing a bigger model or a better prompt reduces but never eliminates, and it is exactly what the provenance edges let you find and fix.

## Retrieve, and look at what you got

The first stage picks a starting point. Use [vector search](../glossary.html#vector-search), because the reader's question is text and your nodes carry embeddings:

```python
QUESTION = "What is Tellson's Bank, and which people and places is it connected to?"

anchor = client.vector_search(embed([QUESTION])[0], k=1)[0]["node_id"]
print("anchor:", client.get_node(anchor)["properties"].get("name"))
```

The second stage takes the neighbourhood around that anchor and flattens it into text. `extract_subgraph` does both the extraction and the [linearization](../glossary.html#linearization) in one call:

```python
sub = client.extract_subgraph(anchor, hops=2, format="structured")
print(sub["nodes_count"], "nodes,", sub["edges_count"], "edges,",
      sub["estimated_tokens"], "estimated tokens")
```

Read those numbers before you read anything else. On the graph as built so far you get **3 nodes and 2 edges**, which is Tellson's Bank and the two passages that mention it, and nothing else. The answer to a question about which people it connects to is not in there.

## Why the retrieval was thin

This is worth slowing down for, because it is the most common way a GraphRAG system disappoints.

Every edge you created points from an entity to a passage. Traversal follows edges in the direction they point. So from Tellson's Bank you reach its passages in one hop, and then you stop, because no edge leads out of a passage. The other entities in those passages, Mr. Lorry and Jerry and London, are one step away in the text and unreachable in the graph.

Provenance needed only one direction. Retrieval needs the other one too. Add it:

```python
for name, nid in entities.items():
    for hop in client.neighbors(nid, direction="outgoing", edge_type="MENTIONED_IN"):
        client.create_edge(hop["node_id"], nid, "MENTIONS")

sub = client.extract_subgraph(anchor, hops=2, format="structured")
print(sub["nodes_count"], "nodes,", sub["edges_count"], "edges,",
      sub["estimated_tokens"], "estimated tokens")
```

That should now report roughly **10 nodes and 18 edges**, about a thousand tokens. The same anchor, the same hop count, the same question: the only thing that changed is that a passage can now lead somewhere. The shape of your edges decides what retrieval can see.

## Look at the context before you trust the answer

The third stage has already happened, inside `extract_subgraph`. Its `text` field is the linearized subgraph, and it is worth printing at least once:

```python
print(sub["text"][:600])
```

You will see nodes with their properties and the edges between them, written out as indented lines. This is exactly what the model is about to be given. Nothing else reaches it. If an answer later looks wrong, this is the first place to look, because the fault is usually here rather than in the model.

## Answer, with the context and without it

The fourth stage is an ordinary language model call, with two instructions that matter: use only the context, and admit when the context is silent.

```python
GROUNDED = (
    "Answer using ONLY the context below. "
    "If the context does not contain the answer, reply exactly: "
    "the context does not say.\n\nContext:\n{context}\n\nQuestion: {question}"
)

print("--- with the graph ---")
print(chat(GROUNDED.format(context=sub["text"], question=QUESTION)))

print("--- without the graph ---")
print(chat(GROUNDED.format(context="(none)", question=QUESTION)))
```

With the subgraph, you get an answer naming Tellson's Bank, London, and the people the passages connect it to. Without it, the same model with the same instructions replies that the context does not say.

That second result is the one to think about. The model has almost certainly read *A Tale of Two Cities* during training and could produce a fluent paragraph about Tellson's Bank from memory. The grounding instruction stops it, and that is the point. An ungrounded answer might be right, might be invented, and you cannot tell which. A grounded answer can be checked, because every claim in it came from a node, and every node came from a passage you can read.

## A note on `graph_rag`

AstraeaDB has a `graph_rag` method that packages retrieval and linearization together:

```python
result = client.graph_rag(question=QUESTION, anchor=anchor, hops=2)
print(result["nodes_in_context"], "nodes,", result["estimated_tokens"], "tokens")
print(result["note"])

client.close()
```

It returns the assembled context, the counts, and a `note`. Writing the final answer needs a language model configured on the server, which this lesson does not assume, so the note tells you to use the context with your own model. That is what the four stages above do by hand, and doing it by hand is worth it once, because each stage is then something you can inspect rather than a single call that either works or does not.

## What's next

You have a complete pipeline: a question in, a grounded answer out, and an inspectable artefact at every stage.

In the next post, **[A Metadata Graph Over a Messy Data Lake](./05-data-lake.md)**, the source material stops being prose. You will build a graph that describes files rather than sentences, and use it to work out which of a pile of comma-separated, JSON, and Parquet files can answer a question at all.
