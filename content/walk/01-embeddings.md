<!-- SEO subtitle (meta description): Learn what an embedding is and how to make one with Ollama and embeddinggemma, then measure meaning with cosine distance in plain Python. -->

# What an Embedding Is, and How to Make One

*Turn a sentence into a list of numbers that captures what it means, then measure how close two meanings are.*

In the Crawl posts you stored embeddings and searched with them, but the vectors themselves were hand-written: four numbers you chose to stand for science fiction, action, romance, and drama. That was enough to show the mechanics. It is not how a real system works, because nobody writes those numbers by hand. In this post you will make real ones from real text, look at what they contain, and measure the distance between two meanings yourself before handing any of it to a database.

## What an embedding actually is

An [embedding](../glossary.html#embedding) is a list of numbers that represents the meaning of a piece of text as a position in space. That sentence is short and does a lot of work, so it is worth unpacking.

Think of a map. A town's position is two numbers, a latitude and a longitude, and two towns near each other on the map have positions that are numerically close. You can measure how far apart they are without knowing anything about the towns themselves, just from the numbers. An embedding does the same thing for meaning instead of geography. Each piece of text gets a position, and texts that mean similar things land near each other.

The difference is the number of directions. A map needs two numbers because it has two directions, north and east. Meaning has far more than two directions, so an embedding uses many more numbers. The model this site uses produces 768 of them for every piece of text. You cannot picture 768 directions, and you do not need to. Everything you do with an embedding is arithmetic that works the same whether there are two numbers or seven hundred.

The numbers themselves are not meaningful one at a time. There is no single number in the list that means "is about sailing". The meaning lives in the whole list at once, in the pattern of all 768 values together. This is why you never read an embedding, and why the hand-written vectors in the Crawl posts were a teaching device rather than a real example.

## Getting a model running

<!-- include: _shared/ollama-setup.md -->

## Making your first embedding

Ollama exposes a web address that takes text and returns its embedding. You can call it with nothing but Python's standard library, so there is no package to install:

```python
import json
import os
import urllib.request

# The lesson uses your local Ollama. OLLAMA_URL is here so the same code runs
# unchanged in automated checks, where Ollama lives at a different address.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def embed(texts):
    """Return one embedding per input string, in the same order."""
    payload = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


vec = embed(["A hacker discovers reality is a simulation."])[0]
print(len(vec), "numbers")
print([round(x, 4) for x in vec[:6]], "...")
```

The first line of output is the length, and it is the number to pay attention to:

<!-- verify: expect-output -->
```python
print(len(vec))
```

```text
768
```

Every embedding this model produces has exactly 768 numbers, whether you give it three words or three paragraphs. That fixed length is the whole point. It is what lets you compare any two pieces of text, however different their lengths, by comparing two lists of the same size.

Notice that the function takes a list and returns a list. Sending several texts in one call is much faster than calling once per text, because the cost is dominated by loading the model rather than by the work on any single input.

## Measuring how close two meanings are

Now for the part that makes embeddings useful. Given two embeddings, you can calculate a single number saying how similar their meanings are. The usual measure is [cosine distance](../glossary.html#cosine-distance), which compares the *direction* two lists point in rather than their magnitude. Identical direction gives a distance of 0, and completely unrelated directions give a distance near 1.

You do not need a library for this:

```python
import math


def cosine_distance(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return 1.0 - dot / (norm_a * norm_b)
```

Try it on sentences whose relationships you already know:

```python
sentences = [
    "A hacker discovers reality is a simulation.",
    "A programmer learns the world is a computer program.",
    "A retired hitman comes back for revenge.",
    "The recipe calls for three tablespoons of butter.",
]
vectors = embed(sentences)

base = vectors[0]
for text, vec in zip(sentences[1:], vectors[1:]):
    print(f"{cosine_distance(base, vec):.3f}  {text}")
```

The first sentence and the second say nearly the same thing in different words, and they share no important vocabulary: one says hacker and simulation, the other says programmer and computer program. A keyword search would find nothing in common. The embedding puts them close together anyway, and that is the property the rest of the Walk tier is built on. The revenge sentence is further away, and the butter sentence is further still.

Run it and read the three distances in order. They should increase down the list, which is the result worth remembering: distance tracks meaning, not shared words.

## Why 768, and why you should not trim it

Some models, this one included, are built so that you can keep only the first part of the list and still get a usable, lower-quality embedding. Cutting 768 numbers down to 128 makes storage smaller and comparisons faster.

This site does not do that, and it is worth saying why, because you will see truncated vectors in older AstraeaDB examples. Trimming was a workaround for a problem in an earlier version of the vector index that has since been fixed. Keeping all 768 numbers means better results, and one less step to explain.

It matters more than it looks, because of a rule you will meet in the next post. A store fixes its embedding width the first time you insert one. Insert a 768-number embedding and every later one must also have 768 numbers, or the server rejects it. So the width is a decision you make once, at the start, for everything you are going to store together.

<details>
<summary>The same idea in R</summary>

The R client does not wrap Ollama, so you call it the same way, with `httr2` or `curl`. The structure is identical: post a model name and a list of strings to `/api/embed`, read back a list of vectors of length 768, and compare two of them with cosine distance. Everything later in this tier assumes the Python version, so if you are following the R track, read on for the concepts and treat the code as illustrative.

</details>

## What's next

You can now turn text into a position in space and measure the distance between two positions. That is the whole mechanism behind searching by meaning.

In the next post, **[Searching a Graph by Meaning, Not by Keyword](./02-semantic-search.md)**, you will stop comparing sentences by hand and let AstraeaDB do it across a whole graph: choosing what text to embed for each kind of node, storing the vectors alongside your data, and tuning how much a search leans on meaning versus on connections.
