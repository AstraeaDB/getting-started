<!-- SEO subtitle (meta description): Turn real security telemetry into an AstraeaDB graph, then run PageRank and Louvain over it and learn why centrality finds your servers rather than your intruder. -->

# Building a Network Graph From Security Telemetry

*Turn a flat log of network events into a graph, then find out what the graph is actually good at telling you.*

Security telemetry arrives as lines in a file. One line per event, each one small and complete and telling you nothing about the others. The questions people actually ask are about relationships: which machines talk to each other, which account is behaving unlike its peers, what did this host do just before it did that.

Those are graph questions asked of a table. This post builds the graph.

## The data

The lessons in this tier use a slice of the Los Alamos National Laboratory dataset of real network events, captured from their internal network over 58 days. It is released under CC0, a public domain dedication, which is why a sample of it ships in this repository under `data/lanl/`.

Two files, and the second is the interesting one:

```python
import csv
import collections

dns = list(csv.reader(open("data/lanl/dns.csv")))
redteam = list(csv.reader(open("data/lanl/redteam.csv")))

print(f"{len(dns)} DNS lookups, {len(redteam)} known red-team events")
print("dns row:    ", dns[0], "  (time, source, resolved)")
print("redteam row:", redteam[0], "  (time, user, source, destination)")
```

`dns.csv` is ordinary activity: one row each time a machine looked up another machine's name. `redteam.csv` is **ground truth**. Those 25 events are authentications the dataset's authors have labelled as a red team acting like an intruder. Having them means this tier can say whether a hunt found the right thing, instead of producing a plausible story nobody can check.

## Building the graph

The graph is deliberately simple: machines are nodes, a lookup is an edge. The one refinement is collapsing repeats into a weight, because the same pair resolving four hundred times is one relationship, not four hundred:

```python
from astraeadb import AstraeaClient

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

pairs = collections.Counter((src, dst) for _, src, dst in dns)

computers = {}
def computer(name):
    if name not in computers:
        computers[name] = client.create_node(["Computer"], {"name": name})
    return computers[name]

for (src, dst), count in pairs.items():
    client.create_edge(computer(src), computer(dst), "RESOLVED", {"count": count})

print(f"{len(computers)} computers, {len(pairs)} distinct resolutions")
```

Around a thousand machines and three thousand relationships, from eight thousand raw events, in well under a second. Note there are no embeddings here at all. This post is about structure, and structure does not need them.

## What shape is this network?

Before asking clever questions, ask dull ones. `graph_stats` and connected components tell you whether you are looking at one network or several:

```python
stats = client.graph_stats()
print("nodes:", stats["total_nodes"], "edges:", stats["total_edges"])

components = client.run_connected_components()
sizes = sorted((len(c) for c in components["components"]), reverse=True)
print(f'{components["count"]} connected components, largest {sizes[0]}, then {sizes[1:6]}')
```

You should find one enormous component and a tail of tiny ones. That is the normal shape of a corporate network seen through DNS: nearly everything reaches the same shared infrastructure, plus a scattering of pairs that only ever talk to each other. The small components are worth a glance in real work, because a machine that talks to nothing else is either unimportant or interesting.

## Centrality, and the mistake it invites

Now the part everyone wants: run PageRank, find the important machines.

```python
scores = client.run_pagerank()
top = sorted(scores.items(), key=lambda kv: -kv[1])[:5]

for node_id, score in top:
    name = client.get_node(int(node_id))["properties"]["name"]
    incoming = len(client.neighbors(int(node_id), direction="incoming"))
    outgoing = len(client.neighbors(int(node_id), direction="outgoing"))
    print(f"{name:8} {score:.5f}  in={incoming:4} out={outgoing}")
```

Look at the `out` column. Every one of the top-ranked machines has substantial incoming edges and **zero outgoing**. They are never the machine doing a lookup, always the machine being looked up. They are servers.

That is what centrality measures here, and it is worth being blunt about it: **PageRank has found your infrastructure, not your intruder.** It is genuinely useful, because knowing which five machines everything depends on matters for resilience and for prioritising patching. It is simply not a way to find an attacker.

## Checking that against the ground truth

We can do better than assert it, because we have the labels:

```python
compromised = {row[2] for row in redteam} | {row[3] for row in redteam}

print("machines named in the red-team events, and their DNS activity:")
for name in sorted(compromised):
    if name not in computers:
        continue
    nid = computers[name]
    incoming = len(client.neighbors(nid, direction="incoming"))
    outgoing = len(client.neighbors(nid, direction="outgoing"))
    print(f"  {name:8} in={incoming:4} out={outgoing}")
```

Most of the machines involved in the intrusion have a degree in the low single figures. They are among the quietest nodes in the graph. One of them is an exception with a large incoming count, and it is an exception for a boring reason: it is a server, which is why an intruder wanted it, and its high rank comes from everyone else's ordinary use of it rather than from anything the intruder did.

So the ground truth agrees. Ranking machines by importance surfaces the machines everyone uses. An intruder using a stolen credential looks, structurally, like a quiet machine doing very little.

This is the honest result, and it sets up the rest of the tier. Structure tells you what your network **is**. Finding someone who should not be there needs behaviour and time, which is the next post.

## Communities

One more structural view worth knowing. Louvain community detection groups machines that talk to each other far more than to everything else:

```python
louvain = client.run_louvain()
sizes = collections.Counter(louvain["communities"].values())
print(f'{louvain["num_communities"]} communities; '
      f'largest five: {[n for _, n in sizes.most_common(5)]}')
```

In a corporate network these tend to line up with something real: a department, a subnet, a cluster of machines running the same service. They are useful as a baseline, because "this machine started talking to a community it has never touched" is a much sharper signal than "this machine sent some traffic".

```python
client.close()
```

## What you have

A graph of a real network, built from raw events, with ground truth attached so claims can be checked. You have also seen the first real lesson of investigative graph work, which is that the obvious measure answers a different question than the one you asked.

## What's next

In **[Hunting Lateral Movement With Embeddings and Time Travel](./03-cyber-hunt.md)**, you will stop looking at structure and start looking at behaviour: describing what each machine normally does, finding the ones that stop matching their own description, and using time-travel queries to see the graph as it was at the moment of the intrusion rather than as it is now.
