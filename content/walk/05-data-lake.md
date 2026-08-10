<!-- SEO subtitle (meta description): Build an AstraeaDB metadata graph over a folder of mismatched CSV and JSON files, then let the graph work out which files and columns can answer a question. -->

# A Metadata Graph Over a Messy Data Lake

*Describe your files in a graph, then ask the graph which of them can answer your question.*

Every graph so far has described things written in prose. This one describes files. The problem it solves is one you have probably met: a folder with years of exports in it, where the same idea is called `cust_id` in one file, `customer_id` in the next, and `CustomerID` in a third, and nobody remembers which files still matter.

You cannot fix that by renaming things, because the files are already written. You can describe it, once, in a graph, and then let the graph answer "where does customer revenue live" instead of asking a colleague who has left.

## A small, realistic mess

Three files, standing in for three years of a system that changed underneath you:

```python
import csv
import json
import os
import pathlib

LAKE = pathlib.Path("/tmp/lake")
LAKE.mkdir(exist_ok=True)

# 2023: the original export, from a system since retired.
with (LAKE / "sales_2023.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["cust_id", "amt", "dt"])
    w.writerows([["C001", "120.50", "2023-03-04"],
                 ["C002", "89.00", "2023-07-19"],
                 ["C001", "310.25", "2023-11-02"]])

# 2024: same data, new platform, different column names.
with (LAKE / "sales_2024.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["customer_id", "amount", "order_date"])
    w.writerows([["C001", "205.00", "2024-02-11"],
                 ["C003", "45.75", "2024-06-30"]])

# A customer list, in a different format again.
(LAKE / "customers.json").write_text(json.dumps([
    {"CustomerID": "C001", "name": "Acme Ltd", "region": "north"},
    {"CustomerID": "C002", "name": "Borden Co", "region": "south"},
    {"CustomerID": "C003", "name": "Crane plc", "region": "north"},
]))

print(sorted(p.name for p in LAKE.iterdir()))
```

Three files, three spellings of a customer identifier, two spellings of a money column. Nothing about the files themselves says these are related.

## Describing the files as a graph

The metadata graph uses three kinds of node. A **DataSource** is a file. A **Field** is a column in one. A **Concept** is the business idea a field represents, and it is the piece that does the real work, because it is the only thing that knows `cust_id` and `CustomerID` mean the same thing.

```python
from astraeadb import AstraeaClient

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
import urllib.request


def embed(texts):
    body = json.dumps({"model": "embeddinggemma", "input": texts}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["embeddings"]


client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

CONCEPTS = {
    "Customer":     "The organisation that placed an order.",
    "Order amount": "The monetary value of a single order.",
    "Order date":   "The calendar date an order was placed.",
}
concepts = {}
for (name, desc), vec in zip(CONCEPTS.items(), embed(list(CONCEPTS.values()))):
    concepts[name] = client.create_node(
        ["Concept"], {"name": name, "description": desc}, embedding=vec)

SOURCES = {
    "sales_2023.csv": ("csv", [("cust_id", "Customer"), ("amt", "Order amount"),
                               ("dt", "Order date")]),
    "sales_2024.csv": ("csv", [("customer_id", "Customer"), ("amount", "Order amount"),
                               ("order_date", "Order date")]),
    "customers.json": ("json", [("CustomerID", "Customer")]),
}

sources, fields = {}, {}
for fname, (fmt, cols) in SOURCES.items():
    sources[fname] = client.create_node(
        ["DataSource"], {"name": fname, "format": fmt, "path": str(LAKE / fname)})
    for col, concept in cols:
        fid = client.create_node(["Field"], {"name": col, "source": fname})
        fields[(fname, col)] = fid
        client.create_edge(sources[fname], fid, "HAS_FIELD")
        client.create_edge(fid, concepts[concept], "MAPS_TO_CONCEPT")

print(len(sources), "sources,", len(fields), "fields,", len(concepts), "concepts")
```

Only the `Concept` nodes carry embeddings here. Fields and sources are found by walking edges, not by similarity, so there is nothing to gain from embedding them.

## Two edges that record what people remember

A schema registry would stop at the structure above. The part that usually lives in somebody's head is the history, and it fits naturally as two more edges.

`SUCCEEDED_BY` says one source replaced another. `SAME_ENTITY_AS` says two differently named fields hold the same real-world identifier, so a value from one can be joined to a value from the other:

```python
client.create_edge(sources["sales_2023.csv"], sources["sales_2024.csv"], "SUCCEEDED_BY")

for a, b in [(("sales_2023.csv", "cust_id"), ("sales_2024.csv", "customer_id")),
             (("sales_2024.csv", "customer_id"), ("customers.json", "CustomerID"))]:
    client.create_edge(fields[a], fields[b], "SAME_ENTITY_AS")
    client.create_edge(fields[b], fields[a], "SAME_ENTITY_AS")

print("history and identity recorded")
```

Note the two calls in that loop. Sameness runs both ways, and the previous post is the reason to be careful here: traversal follows edge direction, so a one-way `SAME_ENTITY_AS` would only be findable from one end.

## Asking the graph which files can answer a question

Now the payoff. A question arrives in ordinary words. Find the concept it is about, then walk back to the fields, then to the files:

```python
QUESTION = "How much has each customer spent in total?"

for hit in client.vector_search(embed([QUESTION])[0], k=3):
    name = client.get_node(hit["node_id"])["properties"]["name"]
    print(f'{hit["distance"]:.3f}  {name}')
```

Look at those three distances before going further, because they carry a warning. They come out close together, and `Customer` is likely to be **last**, even though the question says the word "customer" outright. Concept descriptions are one short sentence each, so there is little for the model to tell apart, and the ranking is nearly a tie.

The practical consequence is that a tight `k` will silently drop a concept you needed. Take a generous number of concepts and let the graph structure do the filtering, rather than trusting the embedding to be precise about a handful of near-identical sentences:

```python
hits = client.vector_search(embed([QUESTION])[0], k=len(CONCEPTS))

plan = {}
for h in hits:
    for f in client.neighbors(h["node_id"], direction="incoming",
                              edge_type="MAPS_TO_CONCEPT"):
        field = client.get_node(f["node_id"])["properties"]
        plan.setdefault(field["source"], []).append(field["name"])

for source, cols in sorted(plan.items()):
    print(f"  {source}: {sorted(cols)}")
```

The graph has now told you which files are relevant and which column in each one carries the idea you asked about, without you knowing any of their names. That is the whole point of the metadata layer: the question was about customers and spending, not about `amt` and `cust_id`.

## Running the query it planned

DuckDB reads comma-separated and JSON files directly, so the plan turns into a query without loading anything first:

```python
import duckdb

# Ask the graph which column in each file carries which concept, rather than
# hard-coding names the whole lesson has been arguing you should not need.
def column_for(source, concept):
    for f in client.neighbors(concepts[concept], direction="incoming",
                              edge_type="MAPS_TO_CONCEPT"):
        props = client.get_node(f["node_id"])["properties"]
        if props["source"] == source:
            return props["name"]
    return None


parts = []
for source in sorted(s for s in plan if s.startswith("sales_")):
    cust = column_for(source, "Customer")
    amt = column_for(source, "Order amount")
    parts.append(f"SELECT {cust} AS customer, {amt} AS amount "
                 f"FROM read_csv_auto('{LAKE / source}')")

sql = ("SELECT customer, ROUND(SUM(amount), 2) AS total "
       f"FROM ({' UNION ALL '.join(parts)}) GROUP BY customer ORDER BY customer")
print(duckdb.sql(sql))
```

Both years are included, with their different column names reconciled, because the graph said the two files describe the same concepts and their identifier fields are the same entity. Nobody had to remember that `amt` became `amount`.

## Where this stops being a toy

Three files fit on a page. A real lake has hundreds, and two things change.

The concept mapping has to be produced rather than typed. You would use the same technique as the previous posts: embed each column name together with a few sample values, and match it against the concept descriptions. That works well and it is wrong often enough that the mapping needs review, which is why the `MAPS_TO_CONCEPT` edge is worth storing rather than recomputing.

And the query planning gets handed to a model. The graph output above is small, structured, and factual, which makes it good context: you hand a model the relevant sources, their fields, and the concepts, and ask for SQL. The [data_lake_demo](https://github.com/AstraeaDB/data_lake_demo) repository does exactly that, over a larger and messier lake, with an agent that plans DuckDB queries from this same graph shape.

```python
client.close()
```

## What's next

You have used a graph to describe data rather than to hold it, which is a different use of the same tool and often the more valuable one.

The next two posts are shorter, and introduce two projects built on AstraeaDB. In **[Eunomia: A Semantic Cache in Front of Your Graph](./06-eunomia.md)**, you will see what happens when the same question gets asked twice.
