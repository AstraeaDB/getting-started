#!/usr/bin/env python3
"""Run a lesson's code blocks inside a fresh container and record the result.

    python3 verify/run.py crawl-py-01
    python3 verify/run.py --all
    python3 verify/run.py crawl-py-01 --keep-going

Every lesson gets its own container and its own AstraeaDB server, started
inside that container on the port the lesson text names. Nothing is shared
between lessons, so a lesson cannot pass by depending on state another lesson
left behind (DESIGN.md 7.3).

Blocks of the same language run in ONE interpreter session, in document order,
because that is how a reader follows a tutorial: a variable bound in one block
is still bound in the next. Each block is exec'd separately inside that shared
session, so a syntax error or exception is attributed to the block that caused
it rather than killing the whole file.
"""

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "site"))
from extract import extract  # noqa: E402
from normalize import matches, normalize  # noqa: E402
# Shared fragments are spliced in at build time. Verification has to splice them
# the same way, or runnable code inside a fragment is published without ever
# having been executed.
from build import expand_includes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "verify"
CONTENT = ROOT / "content"
REPORT = VERIFY / "report.json"

IMAGE_FOR = {
    "py": "astraea-verify-py",
    "both": "astraea-verify-py",
    "r": "astraea-verify-r",
    "rust": "astraea-verify-rust",
}

# stderr patterns that mean a block failed even though it exited zero
# (DESIGN.md 7.4 rule 5). A block that is demonstrating an error opts out with
# <!-- verify: expect-error -->.
STDERR_BAD = ("error", "panic", "traceback", "error in ")

MARK = "@@ASTRAEA"

# Q8: lessons read OLLAMA_URL from the environment, defaulting to
# http://localhost:11434, so the published code is exactly the code that runs.
# A container cannot reach a host Ollama bound to 127.0.0.1, so the harness
# injects the bridge address instead. The host side is NOT changed automatically:
# exposing an unauthenticated model server is the operator's call, not the test
# harness's.
CONTAINER_GATEWAY = "192.168.64.1"
# Override with VERIFY_OLLAMA_URL. That lets an operator front the containers
# with a second Ollama bound to the bridge, on its own port, rather than
# rebinding the one already serving 127.0.0.1 to host tools.
OLLAMA_CONTAINER_URL = os.environ.get(
    "VERIFY_OLLAMA_URL", f"http://{CONTAINER_GATEWAY}:11434"
)


def die(msg):
    print(f"verify: error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_manifest():
    with (ROOT / "lessons.toml").open("rb") as fh:
        return tomllib.load(fh)


# ------------------------------------------------------------- driver scripts


def bash_driver(blocks):
    parts = ["set +e", "cd /work"]
    for b in blocks:
        parts.append(f'echo "{MARK} START {b.index}"')
        parts.append(b.code)
        parts.append(f'echo "{MARK} EXIT {b.index} $?"')
    return "\n".join(parts) + "\n"


def python_driver(blocks):
    payload = json.dumps([[b.index, b.code] for b in blocks])
    return f'''
import sys, json, traceback
BLOCKS = json.loads({payload!r})
G = {{"__name__": "__main__"}}
for idx, code in BLOCKS:
    print("{MARK} START %d" % idx, flush=True)
    rc = 0
    try:
        exec(compile(code, "<block %d>" % idx, "exec"), G)
    except SystemExit as e:
        rc = int(e.code or 0)
    except BaseException:
        traceback.print_exc()
        rc = 1
    sys.stdout.flush(); sys.stderr.flush()
    print("{MARK} EXIT %d %d" % (idx, rc), flush=True)
'''


def r_driver(blocks):
    """Base R has no base64 decoder and no reliable way to embed arbitrary code
    as a string literal, so each block is written to its own file (see
    r_block_files) and sourced into globalenv() so state persists across
    blocks, exactly as it would for a reader working down the page."""
    lines = ["options(warn = 1)"]
    for b in blocks:
        lines.append(f'cat("{MARK} START {b.index}\\n")')
        lines.append("rc <- 0")
        lines.append(
            f'tryCatch(source("/tmp/blk_{b.index}.R", echo = FALSE, local = globalenv()), '
            f'error = function(e) {{ message(conditionMessage(e)); rc <<- 1 }})'
        )
        lines.append("flush(stdout()); flush(stderr())")
        lines.append(f'cat(sprintf("{MARK} EXIT {b.index} %d\\n", rc))')
    return "\n".join(lines) + "\n"


def r_block_files(blocks):
    return {f"/tmp/blk_{b.index}.R": b.code for b in blocks}


# --------------------------------------------------------------- orchestration


SERVER_TOML = """[server]
bind_address = "127.0.0.1"
port = 7687

[storage]
data_dir = "/tmp/astraea/data"
wal_dir = "/tmp/astraea/wal"
buffer_pool_size = 1024

[vector]
dimension = {dim}
metric = "cosine"
"""


def build_container_script(lesson, groups, extra_files):
    """One shell script that boots the server and runs every language group."""
    # A store pins its embedding dimension on first insert, so the server has
    # to match what the lesson teaches. Most lessons use embeddinggemma's
    # native 768, but the Crawl vector lessons deliberately use short
    # hand-written vectors so a beginner can see what an embedding is without
    # running a model, and run-01 uses the Elliptic dataset's 165 features.
    dim = int(lesson.get("vector_dim", 768))
    cfg = base64.b64encode(SERVER_TOML.format(dim=dim).encode()).decode()
    s = [
        "set -u",
        "mkdir -p /tmp/astraea/data /tmp/astraea/wal",
        f"echo {cfg} | base64 -d > /etc/astraeadb/server.toml",
        # Start the server the lesson will talk to, inside the container.
        "astraeadb serve --config /etc/astraeadb/server.toml >/tmp/server.log 2>&1 &",
        "SRV=$!",
        # Wait for it rather than sleeping a fixed amount.
        'for i in $(seq 1 60); do',
        '  if (exec 3<>/dev/tcp/127.0.0.1/7687) 2>/dev/null; then exec 3>&-; break; fi',
        '  sleep 0.5',
        'done',
        'if ! kill -0 "$SRV" 2>/dev/null; then',
        f'  echo "{MARK} SERVERFAIL"; cat /tmp/server.log; exit 97',
        'fi',
        f'echo "{MARK} SERVERUP"',
    ]
    # walk-06 talks to Eunomia, the semantic cache. Start its REST gateway the
    # same way the AstraeaDB server is started: inside the container, on the
    # address the lesson text names, so the snippet under test is the real one.
    if lesson.get("needs_a_llama"):
        # a-llama binds Ollama's own port by default, which is the point of the
        # lesson. It takes no flags; A_LLAMA_ADDR is the only knob.
        s += [
            "a-llama >/tmp/a-llama.log 2>&1 &",
            'for i in $(seq 1 60); do',
            '  if (exec 3<>/dev/tcp/127.0.0.1/11434) 2>/dev/null; then exec 3>&-; break; fi',
            '  sleep 0.5',
            'done',
        ]
    if lesson.get("needs_eunomia"):
        s += [
            "eunomia rest >/tmp/eunomia.log 2>&1 &",
            'for i in $(seq 1 60); do',
            '  if (exec 3<>/dev/tcp/127.0.0.1/8080) 2>/dev/null; then exec 3>&-; break; fi',
            '  sleep 0.5',
            'done',
        ]
    for path, content in extra_files.items():
        fb64 = base64.b64encode(content.encode()).decode()
        s.append(f'echo {fb64} | base64 -d > {path}')
    for lang, script in groups.items():
        b64 = base64.b64encode(script.encode()).decode()
        # 2>&1 so a traceback lands inside its own block's segment. Without
        # it stderr arrives after every marker and the failure detail cannot be
        # attributed to the block that caused it.
        if lang == "bash":
            s += [f'echo {b64} | base64 -d > /tmp/run.sh', "bash /tmp/run.sh 2>&1"]
        elif lang == "python":
            s += [f'echo {b64} | base64 -d > /tmp/run.py', "python3 /tmp/run.py 2>&1"]
        elif lang == "r":
            s += [f'echo {b64} | base64 -d > /tmp/run.R', "Rscript /tmp/run.R 2>&1"]
    s += [f'echo "{MARK} DONE"', 'kill "$SRV" 2>/dev/null || true']
    return "\n".join(s) + "\n"


MARKER_RE = re.compile(
    r"@@ASTRAEA (START (\d+)|EXIT (\d+) (-?\d+)|SERVERUP|SERVERFAIL|DONE)"
)


def parse_output(text):
    """Split the interleaved container output back into per-block segments.

    Markers are matched ANYWHERE in the stream, not just at the start of a
    line. A block whose last write has no trailing newline (R's `cat` on a
    string is the common case) leaves its EXIT marker glued to the end of that
    line, and a line-anchored parser silently loses the exit code and reports
    the block as never completed.
    """
    segs, exits, server_up = {}, {}, False
    cur, pos = None, 0
    for m in MARKER_RE.finditer(text):
        if cur is not None:
            segs.setdefault(cur, []).append(text[pos:m.start()])
        kind = m.group(1)
        if kind.startswith("START"):
            cur = int(m.group(2))
            segs.setdefault(cur, [])
        elif kind.startswith("EXIT"):
            exits[int(m.group(3))] = int(m.group(4))
            cur = None
        elif kind == "SERVERUP":
            server_up = True
        elif kind == "SERVERFAIL":
            server_up = False
        pos = m.end()
    return ({k: "".join(v).strip("\n") for k, v in segs.items()}, exits, server_up)


def ollama_unreachable(image):
    """Return a reason string if the container cannot reach Ollama, else None.

    Ollama binds 127.0.0.1 by default, which a container cannot reach. Rather
    than rebinding the host's model server behind the operator's back, say
    plainly what is wrong and how to fix it.
    """
    # Must be an HTTP request against Ollama's own API, not a bare TCP connect.
    # A connect to the bridge gateway succeeds even with nothing listening
    # behind it, so /dev/tcp reports success and the guard never fires.
    probe = (
        f"curl -sf -m 5 {OLLAMA_CONTAINER_URL}/api/tags "
        f"| grep -q '\"models\"' && echo REACHABLE || echo UNREACHABLE"
    )
    out = subprocess.run(["container", "run", "--rm", image, "bash", "-c", probe],
                         capture_output=True, text=True, timeout=120)
    # Compare the whole token: "REACHABLE" is a substring of "UNREACHABLE", so a
    # containment test here silently reports success for the failure case.
    verdict = out.stdout.split()[-1] if out.stdout.split() else ""
    if verdict == "REACHABLE":
        return None
    return (
        f"this lesson needs Ollama, and the container cannot reach it at "
        f"{OLLAMA_CONTAINER_URL}. Ollama binds 127.0.0.1 by default. To expose it "
        f"to the container bridge for the duration of a verification run:\n"
        f"      OLLAMA_HOST={CONTAINER_GATEWAY}:11434 ollama serve\n"
        f"    That binds only the container bridge rather than 0.0.0.0, so the "
        f"model server is not offered to the wider network. Note it also stops "
        f"127.0.0.1:11434 working for host tools while it runs."
    )


def run_lesson(lesson, manifest, keep_going=False, timeout=900):
    lid = lesson["id"]
    # A self-test fixture carries an absolute path; a real lesson is relative
    # to content/.
    src = Path(lesson["file"])
    if not src.is_absolute():
        src = CONTENT / src

    # Expand includes into a temporary file so fragment code is extracted and
    # run exactly as a reader will see it on the page.
    expanded = expand_includes(src.read_text(encoding="utf-8"), src)
    tmp = VERIFY / f".expanded-{lid}.md"
    tmp.write_text(expanded, encoding="utf-8")
    try:
        blocks, errors = extract(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    if errors:
        for e in errors:
            print(f"verify: error: {e}", file=sys.stderr)
        return {"lesson": lid, "green": False, "failure": "; ".join(errors)}

    active = [b for b in blocks if not b.skip]
    skipped = [{"block": b.index, "lang": b.lang, "reason": b.reason}
               for b in blocks if b.skip]

    if not active:
        return {"lesson": lid, "green": True, "blocks": 0, "skipped": skipped,
                "note": "no runnable blocks"}

    groups, extra_files = {}, {}
    for lang in ("bash", "python", "r"):
        got = [b for b in active if b.lang == lang]
        if not got:
            continue
        groups[lang] = {"bash": bash_driver, "python": python_driver,
                        "r": r_driver}[lang](got)
        if lang == "r":
            extra_files.update(r_block_files(got))

    unsupported = sorted({b.lang for b in active} - {"bash", "python", "r"})
    if unsupported:
        print(f"verify: warning: {lid}: {unsupported} blocks are not executed yet",
              file=sys.stderr)

    image = IMAGE_FOR.get(lesson["track"], "astraea-verify-py")
    script = build_container_script(lesson, groups, extra_files)

    cname = f"verify-{lid}"
    subprocess.run(["container", "rm", "-f", cname], capture_output=True)
    argv = ["container", "run", "--rm", "-i", "--name", cname]

    if lesson.get("needs_ollama"):
        why = ollama_unreachable(image)
        if why:
            return {"lesson": lid, "green": False, "skipped": skipped,
                    "failure": why}
        argv += ["-e", f"OLLAMA_URL={OLLAMA_CONTAINER_URL}"]
    sample = ROOT / "samples" / lid
    if sample.is_dir():
        argv += ["--mount", f"type=bind,source={sample},target=/work/samples,readonly"]
    data = ROOT / "data"
    if data.is_dir() and any(data.iterdir()):
        argv += ["--mount", f"type=bind,source={data},target=/work/data,readonly"]
    argv += [image, "bash", "-s"]

    # A lesson that hangs must fail, not stall the run forever. A closed
    # client socket blocking on recv is enough to do it, and without a
    # deadline that hangs CI rather than reporting anything.
    try:
        proc = subprocess.run(argv, input=script, text=True, capture_output=True,
                              timeout=timeout)
        combined = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        timed_out = False
    except subprocess.TimeoutExpired as e:
        combined = (e.stdout or "") + "\n" + (e.stderr or "")
        timed_out = True
        subprocess.run(["container", "kill", cname], capture_output=True)
    segs, exits, server_up = parse_output(combined)

    if timed_out:
        done = sorted(exits)
        stuck = next((b for b in active if b.index not in exits), None)
        where = (f"block {stuck.index} ({stuck.lang}, line {stuck.line})"
                 if stuck else "an unknown block")
        return {"lesson": lid, "green": False, "skipped": skipped,
                "failure": f"timed out after {timeout}s; {where} never finished "
                           f"({len(done)} of {len(active)} blocks completed)",
                "detail": combined[-2000:]}

    if not server_up:
        return {"lesson": lid, "green": False, "skipped": skipped,
                "failure": "AstraeaDB did not start inside the container",
                "detail": combined[-2000:]}

    failures = []
    for b in active:
        rc = exits.get(b.index)
        out = segs.get(b.index, "")
        if rc is None:
            failures.append(f"block {b.index} ({b.lang}, line {b.line}) never completed")
            continue
        if rc != 0 and not b.expect_error:
            first = (out.strip().splitlines() or [""])[-1][:200]
            failures.append(f"block {b.index} ({b.lang}, line {b.line}) exited {rc}: {first}")
            continue
        if rc == 0 and b.expect_error:
            failures.append(f"block {b.index} (line {b.line}) is marked expect-error but exited 0")
            continue
        low = out.lower()
        if not b.expect_error and any(p in low for p in STDERR_BAD):
            hit = next(p for p in STDERR_BAD if p in low)
            failures.append(
                f"block {b.index} (line {b.line}) exited 0 but its output contains {hit!r}"
            )
            continue
        if b.expect_output and not matches(out, b.expected):
            failures.append(
                f"block {b.index} (line {b.line}) output did not match after normalization\n"
                f"    expected: {normalize(b.expected)[:200]!r}\n"
                f"    actual:   {normalize(out)[:200]!r}"
            )

    rev = astraeadb_rev()
    rec = {
        "lesson": lid,
        "green": not failures,
        "blocks": len(active),
        "skipped": skipped,
        "rev": rev,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "image": image,
    }
    if failures:
        rec["failure"] = failures[0]
        rec["failures"] = failures
    return rec


def astraeadb_rev():
    try:
        out = subprocess.run(
            ["git", "-C", "/Users/jimharris/Documents/astraeadb", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_report(records):
    existing = {}
    if REPORT.is_file():
        try:
            existing = {r["lesson"]: r for r in json.loads(REPORT.read_text())["runs"]}
        except Exception:
            existing = {}
    for r in records:
        existing[r["lesson"]] = r
    REPORT.write_text(
        json.dumps({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "runs": sorted(existing.values(), key=lambda r: r["lesson"])}, indent=2),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lessons", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--keep-going", action="store_true")
    ap.add_argument("--timeout", type=int, default=900,
                    help="seconds before a lesson's container is killed (default 900)")
    ap.add_argument("--self-test", action="store_true",
                    help="run verify/fixtures/three-block.md to prove the harness "
                         "itself works. The fixture is deliberately NOT in "
                         "lessons.toml, so it never reaches the published site.")
    args = ap.parse_args()

    manifest = load_manifest()
    by_id = {L["id"]: L for L in manifest.get("lesson", [])}

    if args.self_test:
        fixture = VERIFY / "fixtures" / "three-block.md"
        if not fixture.is_file():
            die(f"missing self-test fixture at {fixture}")
        targets = [{"id": "self-test", "file": str(fixture), "track": "py",
                    "verify": "required"}]
    elif args.all:
        targets = [L for L in by_id.values() if L.get("verify") == "required"]
    elif args.lessons:
        unknown = [i for i in args.lessons if i not in by_id]
        if unknown:
            die(f"unknown lesson id(s): {unknown}")
        targets = [by_id[i] for i in args.lessons]
    else:
        die("give a lesson id or --all")

    records, failed = [], 0
    for L in targets:
        print(f"verify: {L['id']} ...", flush=True)
        rec = run_lesson(L, manifest, args.keep_going, timeout=args.timeout)
        records.append(rec)
        if rec["green"]:
            print(f"verify: {L['id']} GREEN ({rec.get('blocks', 0)} blocks, "
                  f"{len(rec.get('skipped') or [])} skipped)")
        else:
            failed += 1
            print(f"verify: {L['id']} RED", file=sys.stderr)
            for f in rec.get("failures", [rec.get("failure", "")]):
                print(f"    {f}", file=sys.stderr)
            if not args.keep_going and not args.all:
                break

    if args.self_test:
        print("verify: self-test only; report.json not updated")
    else:
        write_report(records)
        print(f"verify: wrote {REPORT.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
