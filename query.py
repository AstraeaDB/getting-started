#!/usr/bin/env python3
"""Vector-only retrieval against AstraeaDB for a natural-language question."""
from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embed")
MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "embeddinggemma")
TARGET_DIMS = int(os.environ.get("EMBED_DIMS", "128"))


def embed(text: str) -> list[float]:
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps({"model": MODEL, "input": [text]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.load(r)["embeddings"][0]
    v = raw[:TARGET_DIMS]
    n = math.sqrt(sum(x * x for x in v))
    return v if n == 0 else [x / n for x in v]


def send(sock: socket.socket, req: dict) -> dict:
    sock.sendall((json.dumps(req) + "\n").encode())
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            raise RuntimeError("server closed connection")
        buf += chunk
    line, _ = buf.split(b"\n", 1)
    return json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--addr", default=os.environ.get("INSTANCE_ADDR", "127.0.0.1:50100"))
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    vec = embed(args.question)
    host, port = args.addr.split(":")
    sock = socket.create_connection((host, int(port)))
    try:
        hits = send(sock, {"type": "VectorSearch", "query": vec, "k": args.k})
        if hits.get("status") != "ok":
            print(f"search failed: {hits}", file=sys.stderr)
            return 1
        results = hits["data"]["results"]
        print(f"# '{args.question}'  ({len(results)} hits)\n")
        for r in results:
            nid = r["node_id"]
            score = r.get("distance", r.get("score", 0.0))
            node = send(sock, {"type": "GetNode", "id": nid})
            if node.get("status") != "ok":
                continue
            p = node["data"]["properties"]
            text = p.get("text", "")[:240]
            print(f"- [{score:.3f}] {p.get('source','?')}  (node_id={nid})")
            print(f"    {text}\n")
        return 0
    finally:
        sock.close()


if __name__ == "__main__":
    sys.exit(main())
