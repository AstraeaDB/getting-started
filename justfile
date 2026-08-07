set shell := ["bash", "-euo", "pipefail", "-c"]

instance := env_var_or_default("INSTANCE_NAME", "rag-template-demo")

default:
    @just --list

# Start the AstraeaDB instance that backs this project.
up:
    astraea-launcher start --profile single-node-server --name {{instance}} >/dev/null || true
    astraea-launcher status | python3 -c "import sys,json; \
        [print(f\"{i['name']} running on tcp={i['tcp_port']}\") for i in json.load(sys.stdin) if i['name']=='{{instance}}']"

# Stop the instance (data persists).
down:
    astraea-launcher stop --name {{instance}} || true

# Ingest every markdown file under corpus/ into DocChunk nodes with embeddings.
ingest:
    #!/usr/bin/env bash
    set -euo pipefail
    TCP=$(astraea-launcher status 2>/dev/null | python3 -c "
    import sys, json
    for i in json.load(sys.stdin):
        if i['name']=='{{instance}}' and i['running']:
            print(i['tcp_port']); break")
    [[ -z "$TCP" ]] && { echo "instance not running — run 'just up'"; exit 1; }
    INSTANCE_ADDR=127.0.0.1:$TCP python3 ingest.py

# Ask a natural-language question; retrieval-only (phase 3 scope).
query QUESTION:
    #!/usr/bin/env bash
    set -euo pipefail
    TCP=$(astraea-launcher status 2>/dev/null | python3 -c "
    import sys, json
    for i in json.load(sys.stdin):
        if i['name']=='{{instance}}' and i['running']:
            print(i['tcp_port']); break")
    [[ -z "$TCP" ]] && { echo "instance not running — run 'just up'"; exit 1; }
    INSTANCE_ADDR=127.0.0.1:$TCP python3 query.py "{{QUESTION}}"

# End-to-end smoke: up + ingest + one canned question.
smoke: up
    just ingest
    just query "what is a knowledge graph"

clean:
    rm -rf __pycache__ */__pycache__

test: smoke
