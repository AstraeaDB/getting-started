<!-- SEO subtitle (meta description): Turn a graph investigation into a written report where every sentence traces to a query, and see why asking a model to cite its own sources does not work. -->

# Explaining an Investigation: GraphRAG for Audit-Grade Reports

*Write the incident up so that every sentence can be traced to something you can re-run.*

You have five compromised accounts, a foothold, a pivot and a timeline. Now somebody wants it in writing, and that written version will be read by people who were not there, possibly months later, possibly by an auditor whose job is to disbelieve it.

A language model will write you a fluent paragraph in a second. The problem is not fluency. The problem is that a fluent paragraph is indistinguishable from an accurate one, and the difference matters more here than anywhere else in this site.

## The obvious approach, and why it fails

The natural idea is to give the model the subgraph and ask it to cite its sources: produce findings, and for each one, name the nodes it rests on. Then check the citations.

It is worth actually trying, because the way it fails is instructive. Given the incident subgraph and asked for findings with citations, a small local model produced claims resting on `192.168.1.100`, `10.0.0.5` and `172.16.0.20`. There are no IP addresses anywhere in this graph. It had invented plausible-looking infrastructure. Another attempt cited a node called `Unknown`, which is a placeholder leaking into the output, and a larger model emitted the literal string `<node>` from the instructions.

Asked a question the data cannot answer, "what was stolen and where was it sent", it asserted exfiltration to `external_server`, and cited relationships called `EXFILTRATED` and `RECEIVED` that do not exist in the schema.

A citation check catches all of that, and you should build one. But notice what it does not catch. Early on, before checking relationships and not only names, the claim *"data was stolen from C17693 and sent to C17155"* passed, because both machines are real nodes. The nouns were genuine and the sentence was invented. **Verifying that cited entities exist is necessary and nowhere near sufficient**, because a hallucination that reuses real names looks exactly like a fact.

You can keep hardening the checker, and you should, but you are then in a race with a system whose whole talent is producing plausible text.

## The approach that works: do not let it cite

Turn the problem around. Instead of letting the model choose what to assert and then auditing it, **query the graph yourself, and give the model only the answers**. Its job stops being research and becomes rewriting.

Every fact then traces to a query you wrote, which is the thing an auditor actually wants: not a citation the model produced, but a command they can run again.

```python
import csv
import json
import os
import re
import urllib.request

from astraeadb import AstraeaClient

auth = list(csv.reader(open("data/lanl/auth.csv")))
redteam = list(csv.reader(open("data/lanl/redteam.csv")))
attack_start = min(int(row[0]) for row in redteam)

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()

nodes = {}
def node(label, name):
    if (label, name) not in nodes:
        nodes[(label, name)] = client.create_node([label], {"name": name})
    return nodes[(label, name)]

for time, user, source, dest in auth:
    client.create_edge(node("User", user), node("Computer", source),
                       "AUTH_FROM", valid_from=int(time))
    client.create_edge(node("User", user), node("Computer", dest),
                       "AUTH_TO", valid_from=int(time))


def names_of(hops):
    return sorted({client.get_node(h["node_id"])["properties"]["name"] for h in hops})


FOOTHOLD = "C17693"
facts = []

accounts = names_of(client.neighbors(
    node("Computer", FOOTHOLD), direction="incoming", edge_type="AUTH_FROM"))
facts.append(f"{len(accounts)} accounts authenticated from {FOOTHOLD}: "
             f"{', '.join(accounts)}.")

for account in accounts:
    before = names_of(client.neighbors_at(
        node("User", account), "outgoing", attack_start - 1, "AUTH_FROM"))
    facts.append(f"Before t={attack_start}, {account} authenticated only from "
                 f"{', '.join(before) or 'nowhere'}.")

for fact in facts:
    print("-", fact)
```

Each of those lines is the output of one query. Nothing was summarised, inferred or chosen by a model. If an auditor disputes the second bullet, you re-run `neighbors_at` for that account and the argument is over.

## Letting the model write

Now the model gets a task it is genuinely good at, which is turning a list into readable English:

```python
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma3:4b")

prompt = (
    "Write a short incident summary of at most 5 sentences for a security report.\n"
    "Use ONLY these facts. Do not add machines, accounts, IP addresses, times or\n"
    "conclusions that are not stated. Do not speculate about motive or data loss.\n\n"
    "Facts:\n" + "\n".join(f"- {f}" for f in facts)
)

request = urllib.request.Request(
    f"{OLLAMA_URL}/api/generate",
    data=json.dumps({"model": CHAT_MODEL, "prompt": prompt, "stream": False}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=300) as resp:
    report = json.load(resp)["response"].strip()

print(report)
```

Two instructions are doing the work. Naming the categories it must not invent, machines and accounts and addresses and times, is more effective than a general plea for accuracy. And forbidding speculation about motive matters because that is exactly where an incident report goes wrong: the facts support "this account appeared somewhere new" and not "an attacker exfiltrated data", and a model asked to write about a security incident will reach for the second.

## The check that is still worth running

Constraining the input makes invention much less likely. It does not make it impossible, so verify anyway. Because you know every name that legitimately exists, anything else in the text is an addition:

```python
allowed = {name for _, name in nodes}
cited = set(re.findall(r"\b(?:C\d+|U\d+@DOM1)\b", report))
invented = sorted(cited - allowed)

print(f"{len(cited)} identifiers in the report; invented: {invented or 'none'}")
```

This should report none. That is not proof the report is correct, and it is worth being precise about what it does prove: no identifier appears that is not in the graph. A sentence can still misdescribe a real relationship between real machines. What the check gives you is the guarantee that the report is about your network and nothing else, which is the failure the earlier attempt produced repeatedly.

For the residual risk, the answer is not more automation. It is that the fact list is short, written by queries, and can be read by a person in under a minute.

```python
client.close()
```

## What audit-grade actually means here

Three properties, none of which require trusting the model.

Every sentence derives from a fact in a list you can read. Every fact in that list is the output of a query you can re-run against the graph. And the identifiers in the prose are checked against the graph mechanically, so the report cannot quietly acquire a machine that does not exist.

The model contributed the English. That is the correct division of labour, and it is worth defending against the temptation to let it do more, because the moment it decides what is worth saying you are back to auditing prose instead of re-running queries.

## What's next

This tier has one lesson left, and it is the most computational. In **[Finding Fraud: Classifying Bitcoin Transactions with an In-Database GNN](./01-fraud-elliptic.md)** the graph stops being something you query and becomes something you train a model on, inside the database.
