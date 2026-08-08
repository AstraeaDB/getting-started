# Fixture lesson

A four-block fixture that proves the harness works. Never published; it is
registered in lessons.toml only while T3 is being exercised.

## One: bash runs

```bash
echo "server check"
```

## Two: python talks to the in-container server

```python
from astraeadb import AstraeaClient

client = AstraeaClient(host="127.0.0.1", port=7687)
client.connect()
nid = client.create_node(["Fixture"], {"name": "alpha"})
print("created")
```

## Three: state persists into the next block

<!-- verify: expect-output -->
```python
print(client.find_by_label("Fixture") == [nid])
```

```text
True
```

## Four: a skipped block must carry a reason

<!-- verify: skip reason="needs a Kaggle account, so it cannot run in a clean container" -->
```python
raise SystemExit("this must never run")
```
