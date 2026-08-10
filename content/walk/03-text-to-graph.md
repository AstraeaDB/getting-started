<!-- SEO subtitle (meta description): Turn a passage of a novel into an AstraeaDB knowledge graph: extract entities with a local model, store them as nodes, and keep provenance edges back to the source text. -->

# Turning a Book Into a Knowledge Graph

*Read a passage, pull out the people and places, and store them as nodes that remember which sentence they came from.*

Everything so far assumed the graph already existed. Somebody decided that `Movie` and `Person` were the node types, and typed in the data. That does not scale past a demonstration, and it is not how you would handle a book, a pile of contracts, or a year of incident reports. In this post you will build a small graph out of raw prose, and keep a trail from every fact back to the words that produced it.

## Why a graph rather than chunks of text

The ordinary way to make documents searchable is to cut them into chunks, embed each chunk, and search the embeddings. You met the machinery for that in the last two posts and it works well for questions like "what does this text say about X".

It works badly for questions that span the document. "Which characters appear in the same place as Jerry" cannot be answered by finding one similar chunk, because the answer is assembled from facts scattered across many. A chunk knows its own text and nothing else. A node knows what it is connected to.

So you extract the things the text is about, store them as nodes, and connect them. The text does not go away. It becomes another kind of node, which is what makes the result trustworthy.

## The passage

Use the opening of *A Tale of Two Cities*, where a rider stops a mail coach on the Dover road. It is short, it is public domain, and it names several things worth extracting:

```python
PASSAGE = (
    "“There is nothing to apprehend. I belong to Tellson’s Bank. You must "
    "know Tellson’s Bank in London. I am going to Paris on business. A crown "
    "to drink. I may read this?” He opened it in the light of the coach-lamp "
    "on that side, and read—first to himself and then aloud: “‘Wait at Dover "
    "for Mam’selle.’ It’s not long, you see, guard. Jerry, say that my answer "
    "was, RECALLED TO LIFE.”"
)
```

## Asking a model to extract entities

You need a program that reads prose and returns structured data. A [large language model](../glossary.html#large-language-model-llm) does this well, and you already have one running locally from the earlier posts. Pull a small chat model alongside your embedding model:

<!-- verify: skip reason="the verification images use an Ollama already running on the host, which has this model; pulling it inside the container would download gigabytes on every run" -->
```bash
ollama pull gemma3:4b
```

Two things make the difference between this working and this being a nuisance.

The first is asking for JSON and meaning it. Ollama takes a `format` argument, and setting it to `"json"` constrains the model so its reply is a JSON object and nothing else. Without it you get a helpful sentence of preamble, a code fence, and a parsing problem.

The second is telling the model not to embellish. A model asked to describe Dickens will happily supply facts from the rest of the novel, or from its training, and you will not be able to tell which. The instruction to use only what the passage states is what keeps the graph honest:

```python
import json
import os
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma3:4b")

PROMPT = """Extract the named entities from this passage.

Return ONLY a JSON object, no other text, shaped exactly like this:
{"characters": [{"name": "...", "description": "..."}],
 "locations": [{"name": "...", "description": "..."}]}

A character is a person. A location is a place or a named organisation.
Use only what the passage states. Do not invent anything.

Passage:
""" + PASSAGE


def embed(texts):
    """Same helper as the previous two posts, repeated so this page stands alone."""
    body = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


def chat_json(prompt):
    body = json.dumps({
        "model": CHAT_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",      # constrain the reply to a JSON object
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(json.load(resp)["response"])


extracted = chat_json(PROMPT)
print("characters:", [c["name"] for c in extracted.get("characters", [])])
print("locations: ", [l["name"] for l in extracted.get("locations", [])])
```

You should see Jerry as a character, and Tellson's Bank, London, Paris, and Dover as locations. Do not expect the exact same answer every time. A model is not a parser, and a different model or a longer passage will give you a slightly different list. That variability is the reason for the next section.

## Storing the text as a node too

Here is the habit worth forming. Before you store a single extracted entity, store the passage itself:

```python
from astraeadb import AstraeaClient

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

passage_id = client.create_node(
    ["Passage"],
    {"text": PASSAGE, "work": "A Tale of Two Cities", "chapter": 2},
    embedding=embed([PASSAGE])[0],
)
print("passage stored as node", passage_id)
```

The passage node is the evidence. Every entity you extract from it gets an edge pointing back, so any claim the graph makes can be traced to the words behind it:

```python
def store(kind, items):
    """Create one node per extracted item, linked back to its source passage."""
    if not items:
        return []
    texts = [f'{i["name"]}. {i.get("description", "")}'.strip() for i in items]
    ids = []
    for item, vec in zip(items, embed(texts)):
        nid = client.create_node(
            [kind],
            {"name": item["name"], "description": item.get("description", "")},
            embedding=vec,
        )
        client.create_edge(nid, passage_id, "MENTIONED_IN")
        ids.append(nid)
    return ids


characters = store("Character", extracted.get("characters", []))
locations = store("Location", extracted.get("locations", []))
print(f"{len(characters)} characters and {len(locations)} locations, all linked to the passage")
```

Notice that each entity is embedded on a composed sentence of its name and description, which is the lesson from the previous post applied to generated data rather than to data you typed.

## Reading the evidence back

Provenance is only worth having if you can follow it. Given any entity, one hop gets you to the text it came from:

```python
for nid in characters + locations:
    name = client.get_node(nid)["properties"]["name"]
    for hop in client.neighbors(nid, direction="outgoing", edge_type="MENTIONED_IN"):
        source = client.get_node(hop["node_id"])["properties"]
        snippet = source["text"][:60].replace("\n", " ")
        print(f'{name:20} <- {source["work"]}, chapter {source["chapter"]}: "{snippet}..."')
```

That is the property that makes this approach defensible. When a graph tells you Jerry is connected to Dover, you are one hop from the sentence that says so, and you can judge for yourself whether the model read it correctly. A system that cannot show its evidence is asking you to trust an extraction you never saw.

It also gives you a repair path. When extraction gets something wrong, and it will, the passage node tells you exactly which text to re-run.

```python
client.close()
```

## Doing this to a whole book

One passage is a demonstration. A whole novel is the same three steps in a loop: split the text into passages, extract from each, and store the results with their provenance edges. Two things change at that scale. You have to decide when two mentions of a name are the same entity, so that Jerry in chapter two is the node you already made in chapter one. And you need a second pass to connect entities to each other, rather than only to their passages.

The [astraea-graphrag-demo](https://github.com/AstraeaDB/astraea-graphrag-demo) repository does exactly that for the full text of *A Tale of Two Cities*, producing 229 nodes and 317 edges across characters, locations, events, themes, chapters, and passages. It is worth reading once you have made the small version work.

## What's next

You now have a graph built from prose, where every node can point at the text that produced it.

In the next post, **[GraphRAG End to End: Retrieve, Extract, Linearize, Answer](./04-graphrag.md)**, you will use that structure to answer questions: finding the relevant corner of the graph, turning it into text a model can read, and getting an answer where every claim traces back to a node you can inspect.
