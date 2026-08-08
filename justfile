set shell := ["bash", "-euo", "pipefail", "-c"]

# pandoc is not on the default PATH in this environment, and the system python3
# is 3.10, which predates tomllib. Both are resolved explicitly so a missing
# tool fails with a clear message instead of a confusing one (DESIGN.md 8).
pandoc := env_var_or_default("PANDOC", "/opt/homebrew/bin/pandoc")
python := env_var_or_default("PYTHON", "/opt/homebrew/bin/python3")
astraeadb := env_var_or_default("ASTRAEADB", "/Users/jimharris/Documents/astraeadb/target/release/astraeadb")

default:
    @just --list

# Render content/ into docs/. This is what GitHub Pages serves.
build:
    PANDOC={{pandoc}} {{python}} site/build.py

# Preview the built site at http://127.0.0.1:8000 (does not rebuild).
serve: build
    @echo "serving docs/ at http://127.0.0.1:8000 — ctrl-c to stop"
    @{{python}} -m http.server 8000 --directory docs

# Verify one lesson's code blocks in a container. `just verify crawl-py-01`
verify LESSON:
    {{python}} verify/run.py {{LESSON}}

# Verify every lesson whose lessons.toml entry says verify = "required".
verify-all:
    {{python}} verify/run.py --all

# Build the four verification container images. MODE is "fast" or "install".
images MODE="fast":
    # --mode install rebuilds from scratch, running the exact apt-get and
    # cargo install lines the Crawl lessons print. Building the image IS the
    # test of the install instructions (DESIGN.md 7.2).
    {{python}} verify/build_images.py --mode {{MODE}}

# Start the authoring AstraeaDB server on 127.0.0.1:7687 (768-dim).
up:
    #!/usr/bin/env bash
    # Runs astraeadb directly rather than through astraea-launcher: the
    # launcher writes its own config with only [server] and [storage], so a
    # launcher-managed instance cannot serve the 768 dimensions the site
    # teaches. 7687 is the port the lessons print. See astraea-config/.
    set -euo pipefail
    mkdir -p .astraea/data .astraea/wal
    if [[ -f .astraea/pid ]] && kill -0 "$(cat .astraea/pid)" 2>/dev/null; then
        echo "authoring server already running (pid $(cat .astraea/pid))"; exit 0
    fi
    nohup {{astraeadb}} serve --config astraea-config/default.toml \
        >>.astraea/server.log 2>&1 &
    echo $! > .astraea/pid
    sleep 2
    if ! kill -0 "$(cat .astraea/pid)" 2>/dev/null; then
        rm -f .astraea/pid; echo "failed to start; see .astraea/server.log" >&2; exit 1
    fi
    echo "authoring server up on 127.0.0.1:7687 (pid $(cat .astraea/pid))"

# Stop the authoring instance (data persists under .astraea/).
down:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -f .astraea/pid ]]; then
        kill "$(cat .astraea/pid)" 2>/dev/null || true
        rm -f .astraea/pid
        echo "authoring server stopped"
    else
        echo "not running"
    fi

# Remove generated output. docs/ is committed, so re-run `just build` after.
clean:
    rm -rf docs/* __pycache__ */__pycache__ verify/report.json
