<!-- SEO subtitle (meta description): a-llama is an Ollama-compatible LLM server with AstraeaDB and Eunomia compiled in, so what it learns persists. Install it and point your existing code at it. -->

# a-llama: A Local LLM Server That Remembers

*One binary that speaks Ollama's API, with a graph database and a semantic cache inside it rather than beside it.*

This closes the Walk tier. Every post in it has assembled the same parts by hand: a model for embeddings, a graph for structure, a cache for what is currently relevant, and code to move data between them. [a-llama](https://github.com/AstraeaDB/a-llama) is what happens when somebody puts those parts in one process.

## What it is

a-llama is a local language model server that speaks the same HTTP API as Ollama, with AstraeaDB and Eunomia compiled into the binary. Not connected to over a network. Compiled in. There is no graph server to start, no cache to configure, and no ports to allocate for them.

The reason to do that is continual learning. An ordinary model server is stateless: it answers, and forgets. a-llama keeps what passes through it, in the embedded graph and cache, and feeds relevant pieces back into later prompts using the GraphRAG loop from earlier in this tier. The claim is not that the model improves, because the weights never change. The claim is that the system around the model accumulates, so the same question asked next week can be answered with what it learned this week.

That is the same division of labour as the previous post, moved inside a single process. The graph holds what is true, the cache holds what is currently relevant, and now neither is something you deploy.

## Installing it

<!-- verify: skip reason="proven by the container image build, which runs this exact line from scratch in --mode install" -->
```bash
cargo install a-llama
```

The package and the binary are both called `a-llama`, which after `astraea-cli` giving you `astraeadb` and `eunomia-server` giving you `eunomia` is a small mercy.

Start it:

<!-- verify: skip reason="run.py starts the daemon before the lesson body so the later blocks have something to talk to; a second one would fail on the port" -->
```bash
a-llama
```

It listens on `127.0.0.1:11434`. That is Ollama's port, chosen deliberately, and it is the whole point of the next section. Override it with `A_LLAMA_ADDR` if you have Ollama running and want both.

## Pointing your existing code at it

Every Python example in this tier read its model address from an environment variable:

<!-- verify: skip reason="a one-line quotation of code from the earlier posts, shown to make a point about the environment variable; it is not a runnable snippet on its own" -->
```python
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
```

That was not an accident. Because a-llama serves the same routes on the same port, the code you have already written works against it with nothing changed but that value:

```python
import json
import os
import urllib.request

A_LLAMA = os.environ.get("A_LLAMA_URL", "http://127.0.0.1:11434")


def get(path):
    with urllib.request.urlopen(f"{A_LLAMA}{path}", timeout=30) as resp:
        return json.load(resp)


print("version:", get("/api/version"))
print("models: ", [m["name"] for m in get("/api/tags").get("models", [])])
```

Those are the same two endpoints an Ollama client calls to discover what it is talking to, answered by a completely different program. The routes a-llama serves are `/api/generate`, `/api/chat`, `/api/embed`, `/api/embeddings`, `/api/tags`, and `/api/version`, which is the set an Ollama-compatible client expects.

```python
def post(path, body):
    req = urllib.request.Request(
        f"{A_LLAMA}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


reply = post("/api/generate", {"prompt": "What is a knowledge graph?", "stream": False})
print("response:", str(reply.get("response"))[:120])
```

## A word about what you just ran

The default build ships a deterministic stand-in engine rather than a real model, which is why the install above needed no multi-gigabyte download and why the answer you got is not a thoughtful one. That is a sensible default for a project whose interesting part is the memory rather than the inference, and it is what makes this lesson runnable at all.

For real answers you build with the inference backend turned on:

<!-- verify: skip reason="a real GGUF backend pulls a multi-gigabyte model, which is not something a verification run should download" -->
```bash
cargo install a-llama --features mistralrs-engine
```

That compiles in a real engine and loads a GGUF model file, at which point the same endpoints you just called return real completions, and the memory layer you did not have to configure starts accumulating something worth keeping.

## What is actually stored

Two things, matching the two components.

Interactions go into the embedded Eunomia cache, keyed by an embedding of the prompt, so a semantically similar question later can be recognised as one already answered. Facts extracted from those interactions go into the embedded AstraeaDB graph, where they are retrieved with the same `graph_rag` machinery you used in walk-04.

One implementation detail is worth knowing if you go reading the source. The embedded graph uses an exact, brute-force vector index rather than an approximate one, which gives perfect recall at the cost of scanning everything. That choice was made when AstraeaDB's HNSW index had a recall problem at scale, which has since been fixed, so it is a decision the project may revisit rather than a permanent statement about which index is better.

## When this shape is the right one

Embedding a database into an application is unusual, and it is worth being clear about when it helps.

It suits a single-process tool that should work without setup: a desktop assistant, a command-line utility, something a colleague can install and run without being told to start three services first. The whole dependency graph is one `cargo install`.

It suits work that must stay on one machine, because nothing crosses a network boundary at any point. There is no port to firewall and no credential to rotate.

It stops suiting you the moment two processes need the same memory. Embedded storage belongs to the process that opened it, so a second a-llama does not see the first one's graph. That is when you go back to the arrangement from earlier in this tier, with AstraeaDB and Eunomia as services that several clients share. The techniques do not change; only where the storage lives does.

## Where to read more

The [a-llama repository](https://github.com/AstraeaDB/a-llama) covers the parts this introduction skips: how extraction decides what is worth keeping, how the augmentation loop assembles a prompt from retrieved context, the `durable` feature that moves the embedded graph from memory onto disk, and the state of the real inference backend.

## What's next

That is the Walk tier. You can make embeddings, search a graph by meaning, build a graph out of prose, answer questions from it with the evidence attached, describe a data lake so it can answer questions about itself, and you have met the two projects that package these ideas up.

The Run tier takes the same techniques to work where the stakes are higher: finding fraud in a network of Bitcoin transactions, hunting an intruder across security telemetry, and giving a coding assistant a memory of your codebase.
