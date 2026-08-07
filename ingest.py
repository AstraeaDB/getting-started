#!/usr/bin/env python3
"""Embed every markdown file under corpus/ and insert it into AstraeaDB.

Each file is split into ~500-char chunks at paragraph boundaries. Every
chunk becomes one DocChunk node with an embedding. Connect-to-astraea
details (host, port) come from the CLI or from the INSTANCE_ADDR env var.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embed")
MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "embeddinggemma")
# Matryoshka truncation: embeddinggemma is 768-dim natively; we store 128.
TARGET_DIMS = int(os.environ.get("EMBED_DIMS", "128"))


def _truncate_normalize(vec: list[float], dims: int = TARGET_DIMS) -> list[float]:
    v = vec[:dims]
    n = math.sqrt(sum(x * x for x in v))
    return v if n == 0 else [x / n for x in v]


def embed_batch(texts: list[str]) -> list[list[float]]:
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps({"model": MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.load(r)["embeddings"]
    return [_truncate_normalize(v) for v in raw]


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


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split on blank-line paragraph boundaries, then concatenate up to max_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if not current:
            current = p
        elif len(current) + len(p) + 2 <= max_chars:
            current += "\n\n" + p
        else:
            chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr", default=os.environ.get("INSTANCE_ADDR", "127.0.0.1:50100"))
    ap.add_argument("--corpus", default=str(CORPUS))
    args = ap.parse_args()

    corpus = Path(args.corpus)
    if not corpus.exists():
        print(f"no corpus at {corpus}", file=sys.stderr)
        return 1

    files = sorted(corpus.glob("*.md"))
    if not files:
        print("no *.md files in corpus/", file=sys.stderr)
        return 1

    host, port = args.addr.split(":")
    sock = socket.create_connection((host, int(port)))
    try:
        total_chunks = 0
        for path in files:
            text = path.read_text()
            chunks = chunk_text(text)
            if not chunks:
                continue
            vectors = embed_batch(chunks)
            for text_chunk, vec in zip(chunks, vectors):
                resp = send(
                    sock,
                    {
                        "type": "CreateNode",
                        "labels": ["DocChunk"],
                        "properties": {
                            "source": path.name,
                            "text": text_chunk,
                        },
                        "embedding": vec,
                    },
                )
                if resp.get("status") != "ok":
                    print(f"  error inserting chunk: {resp}", file=sys.stderr)
                    continue
                total_chunks += 1
            print(f"{path.name}: {len(chunks)} chunks")
        print(f"\ningested {total_chunks} chunks across {len(files)} files")
        return 0
    finally:
        sock.close()


if __name__ == "__main__":
    sys.exit(main())
