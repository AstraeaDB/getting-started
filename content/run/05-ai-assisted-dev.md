<!-- SEO subtitle (meta description): Give a coding assistant a persistent memory: ingest a directory into AstraeaDB, expose it over the Model Context Protocol, and let the assistant write notes back. -->

# Giving Your Coding Assistant a Memory

*Point an assistant at a graph of your own material, and let it write back what it works out.*

A coding assistant starts every session knowing nothing about your project except what fits in its context window. You explain the same architecture again on Monday that you explained on Friday. The obvious fix is to give it somewhere durable to look things up, and somewhere to write down what it concludes.

This post builds a small version of that, and then points at [adb-claude-kit](https://github.com/AstraeaDB/adb-claude-kit), which is the finished one.

## Two ways to put a directory into a graph

There is a real choice here, and it is worth understanding before you pick.

**Chunked ingestion** splits every file at paragraph boundaries, embeds each chunk, and stores it. It costs one embedding call per chunk and no reasoning at all, so it is fast and cheap over any volume of material. What you get back is similarity: it will find you the passage that mentions retry logic. It cannot tell you which function calls which.

**Typed ingestion** asks a model to read each file and emit a structured graph of the things in it, with real relationships, in the way walk-03 extracted characters from a novel. It costs a model call per file, which is orders of magnitude more expensive, and it gives you a graph you can traverse by structure rather than only search by similarity.

The kit supports both, and the honest advice is to start chunked. Similarity search over your own material is most of the value for a fraction of the cost, and you can always run typed ingestion later over the subset that turns out to matter.

## Chunked ingestion, in about thirty lines

Set the embedding width to match the rest of this site before anything else, since a store fixes it on first insert:

```python
import json
import os
import pathlib
import urllib.request

from astraeadb import AstraeaClient

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CORPUS = pathlib.Path("/tmp/corpus")
CORPUS.mkdir(exist_ok=True)

(CORPUS / "retry.md").write_text(
    "# Retry policy\n\n"
    "Outbound calls retry three times with exponential backoff. "
    "After the third failure the request is written to the dead letter queue.\n\n"
    "The backoff base is 200 milliseconds and doubles each attempt.\n")
(CORPUS / "auth.md").write_text(
    "# Authentication\n\n"
    "Service tokens are issued by the identity service and expire after one hour. "
    "A client that receives a 401 should refresh its token once and retry.\n\n"
    "Tokens are never written to logs.\n")


def embed(texts):
    body = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

source = client.create_node(["Source"], {"name": "corpus", "path": str(CORPUS)})

for path in sorted(CORPUS.glob("*.md")):
    file_id = client.create_node(["File"], {"name": path.name, "path": str(path)})
    client.create_edge(source, file_id, "CONTAINS")

    chunks = [c.strip() for c in path.read_text().split("\n\n") if c.strip()]
    previous = None
    for offset, (chunk, vec) in enumerate(zip(chunks, embed(chunks))):
        cid = client.create_node(
            ["Chunk"],
            {"text": chunk, "file": path.name, "offset": offset},
            embedding=vec)
        client.create_edge(file_id, cid, "CONTAINS")
        if previous is not None:
            client.create_edge(previous, cid, "NEXT_CHUNK")   # reading order
        previous = cid

print("ingested", len(list(CORPUS.glob("*.md"))), "files")
```

That is the shape the kit uses: `Source` contains `File` contains `Chunk`, with `NEXT_CHUNK` preserving reading order so a hit can be expanded to its neighbours. Only chunks carry embeddings, because only chunks are searched.

## Asking it something

```python
QUESTION = "what happens when a request keeps failing?"

for hit in client.vector_search(embed([QUESTION])[0], k=2):
    props = client.get_node(hit["node_id"])["properties"]
    print(f'{hit["distance"]:.3f}  {props["file"]}: {props["text"][:70]}...')
```

The chunk about the dead letter queue should come first. The question never says "retry", "backoff" or "dead letter", which is the part that matters: you found the paragraph by describing the situation rather than by guessing the vocabulary it was written in. This is the same vector search from Crawl, doing the thing it is actually good for, which is finding the paragraph you half-remember in material you wrote months ago.

## Writing back what the assistant works out

This is the half that makes it a memory rather than a search index. When the assistant concludes something, it stores it as a node of its own, next to the material it came from:

```python
note = ("The retry policy and the auth policy interact: a 401 triggers one token "
        "refresh and retry, which counts against the three-attempt budget.")

note_id = client.create_node(
    ["Note"], {"text": note, "author": "assistant"}, embedding=embed([note])[0])

for hit in client.vector_search(embed([note])[0], k=2):
    client.create_edge(note_id, hit["node_id"], "DERIVED_FROM")

print("stored a note derived from", 2, "chunks")
```

Two things about that. The note is embedded, so a later session searching for "how many retries does an expired token cost" finds the conclusion rather than rediscovering it. And it is linked to the chunks that prompted it, which is the same provenance habit from walk-03: a conclusion you cannot trace is a conclusion you cannot check.

The kit keeps three such types, `Note`, `Decision` and `Issue`, and its re-ingest step deletes and rebuilds `Source`, `File` and `Chunk` while never touching them. That asymmetry is deliberate. The material is derived from files and can be regenerated at any time; the conclusions cannot.

```python
client.close()
```

## Handing it to the assistant

Everything above is code you run. The last step gives the assistant direct access, using the Model Context Protocol, a standard way for a tool to expose functions an assistant can call.

AstraeaDB ships a server for it. `astraeadb mcp` speaks the protocol over standard input and output and proxies to a running database, exposing the whole tool registry: `vector_search`, `create_node`, `neighbors`, `query` and the rest, 29 tools in total.

Claude Code reads a file called `.mcp.json` in the directory you open it in:

<!-- verify: skip reason="an editor configuration file, consumed by a Claude Code session rather than by anything this harness can run" -->
```json
{
  "mcpServers": {
    "astraea": {
      "command": "astraeadb",
      "args": ["mcp", "--address", "127.0.0.1:7687"]
    }
  }
}
```

With that in place the assistant can search your graph and write notes into it without you pasting anything, because those are tool calls it makes directly. The difference in practice is that "what did we decide about token refresh" becomes a question it can answer instead of one you answer.

## Where to read more

[adb-claude-kit](https://github.com/AstraeaDB/adb-claude-kit) is the maintained version of everything here. It adds file-type extraction beyond plain text, an instance launcher that persists across restarts, the two ingestion subagents that do the typed extraction, and a set of commands for driving all of it from inside a session. Its core paths are standard library only, so there is nothing to install beyond `astraeadb`, Python and Ollama.

One difference to note if you compare the code. The kit defaults its embedding width to 128 for backward compatibility, and reads `EMBED_DIMS` from the environment. Set `EMBED_DIMS=768` to match this site and everything else you have built here.

## What's next

The remaining posts in this tier are investigations. In **[Building a Network Graph From Security Telemetry](./02-cyber-build.md)** you will take raw authentication and process events and turn them into a graph you can hunt through.
