<!-- SEO subtitle (meta description): Eunomia is a Rust semantic cache for AI agents. Install it, store a working memory, and recall it with a differently worded question. -->

# Eunomia: A Semantic Cache in Front of Your Graph

*Give an agent a scratchpad it can search by meaning, so it stops forgetting what you told it.*

This post and the next are shorter than the rest of this tier. Each introduces a project built on AstraeaDB, shows one worked example, and points you at where to read more.

[Eunomia](https://github.com/AstraeaDB/eunomia) is a small server that holds things an agent needs to remember for a while, and lets it find them again by meaning rather than by key. It is written in Rust, it keeps everything in memory by default, and it exists because a graph database is the wrong shape for one particular job.

## The job it does

An agent working through a long task learns things as it goes. A user says early on that they want answers in metric units. Forty exchanges later, that instruction has fallen out of the context window, and the agent starts quoting inches.

You could write every such fact into AstraeaDB. It would work, and it would be the wrong instrument. Those facts are not permanent, they are not related to each other in ways worth traversing, and they are written and read constantly during a session and then never again. Putting them in a graph means paying for durability and structure you will not use.

Eunomia is the other half of that pair. AstraeaDB holds what is true; Eunomia holds what is currently relevant. The dividing line is roughly whether you would care if it vanished when the process stopped.

## Installing and starting it

It is published on crates.io alongside the AstraeaDB crates:

<!-- verify: skip reason="proven by the container image build, which runs this exact line from scratch in --mode install" -->
```bash
# The package is eunomia-server; the program it installs is called `eunomia`.
cargo install eunomia-server
```

That package-and-binary mismatch is the same one you met installing `astraea-cli` and getting `astraeadb`. It is worth a moment's attention, because typing the name you expect will not work.

Start the REST gateway:

<!-- verify: skip reason="run.py starts the gateway before the lesson body so the later blocks have something to talk to; starting a second one here would fail on the port" -->
```bash
eunomia rest
```

With no configuration file, it starts with a sensible demo setup: one namespace called `default`, an embedding width of 768 to match the rest of this site, an API key of `dev-key`, and a listener on `127.0.0.1:8080`. A real deployment gets a TOML file with its own namespaces and keys; the defaults exist so you can try it in one command.

## Storing a memory

A memory has an identifier, a JSON value of whatever shape you like, and an embedding of the text you would search for later. The embedding is the interesting part, because it is what makes recall work when the question is worded differently:

```python
import json
import os
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EUNOMIA = os.environ.get("EUNOMIA_URL", "http://127.0.0.1:8080")


def embed(texts):
    body = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


def eunomia(path, body):
    req = urllib.request.Request(
        f"{EUNOMIA}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-api-key": "dev-key"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


MEMORIES = {
    "pref-units": "The user prefers metric units.",
    "pref-tone": "The user wants concise answers without preamble.",
}

for (mid, text), vec in zip(MEMORIES.items(), embed(list(MEMORIES.values()))):
    eunomia("/v1/memory", {"id": mid, "embedding": vec, "value": {"note": text}})

print("stored", len(MEMORIES), "memories")
```

## Recalling it by meaning

Now ask questions that share no words with what you stored:

```python
QUESTIONS = [
    "what measurement system should I use?",
    "how long should my replies be?",
    "what is the capital of Peru?",
]

for question in QUESTIONS:
    hits = eunomia("/v1/recall", {"embedding": embed([question])[0], "k": 2})
    ranked = [(h["entry"]["key"]["id"], round(h["score"], 3)) for h in hits]
    print(f"{question:38} {ranked}")
```

Three things to read in that output.

The right memory comes first each time, and no question shares a significant word with the memory it matches. "Measurement system" finds the metric preference; "how long should my replies be" finds the one about concise answers.

The scores separate cleanly. The correct memory scores well above the other, and the question about Peru, which matches nothing you stored, scores low against both. That gap is what you would threshold on in a real agent: below some value, treat it as no memory rather than as a weak one.

And note the direction. Eunomia returns a **`score`, where higher is better**. AstraeaDB's vector search returns a **`distance`, where lower is better**. The two conventions are opposite, and moving between them is an easy way to sort your results backwards.

## Forgetting, on purpose

A cache that never forgets is a database with extra steps. Two mechanisms handle that. A memory can carry `ttl_secs`, after which a background sweeper removes it, and it can carry `tags`, which recall can filter on so a session's memories do not leak into another's.

```python
eunomia("/v1/memory", {
    "id": "scratch-1",
    "embedding": embed(["The current file being edited is report.md."])[0],
    "value": {"note": "editing report.md"},
    "ttl_secs": 300,
    "tags": ["session-42"],
})
print("stored a memory that expires in five minutes")
```

## Promoting a memory into the graph

Sometimes a scratchpad note turns out to matter. Eunomia has an endpoint for exactly that, `POST /v1/memory/{id}/promote`, which hands the memory to AstraeaDB for permanent storage when the server is built with the AstraeaDB bridge enabled. The example above runs in standalone mode, where there is no graph to promote into, so the call is not shown running here.

The pattern is worth knowing even so, because it is the answer to "which of these two should I use". You do not choose once. Things start in working memory, and the few that earn it are promoted to the graph.

## Where to read more

The [Eunomia repository](https://github.com/AstraeaDB/eunomia) documents the full surface: the gRPC and Model Context Protocol gateways as well as REST, namespace configuration, hybrid search that combines semantic proximity with tag filters, and the AstraeaDB tiering options. The Model Context Protocol gateway is the one to look at if you are building an agent, because it lets the agent manage its own memory as a tool call rather than through code you write.

## What's next

In the last post of this tier, **[a-llama: A Local LLM Server That Remembers](./07-a-llama.md)**, you will meet a project that puts the two halves together: a language model server with AstraeaDB and Eunomia compiled into it, so the memory is not a service it calls but part of what it is.
