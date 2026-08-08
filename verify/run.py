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
import shlex
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import extract  # noqa: E402
from normalize import matches, normalize  # noqa: E402

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


def build_container_script(lesson, groups, extra_files):
    """One shell script that boots the server and runs every language group."""
    s = [
        "set -u",
        "mkdir -p /tmp/astraea/data /tmp/astraea/wal",
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


def parse_output(text):
    """Split the interleaved container output back into per-block segments."""
    segs, cur, order = {}, None, []
    exits, server_up = {}, False
    for line in text.splitlines():
        if line.startswith(MARK + " START "):
            cur = int(line.rsplit(" ", 1)[1])
            segs.setdefault(cur, [])
            order.append(cur)
            continue
        if line.startswith(MARK + " EXIT "):
            parts = line.split()
            exits[int(parts[2])] = int(parts[3])
            cur = None
            continue
        if line.startswith(MARK + " SERVERUP"):
            server_up = True
            continue
        if line.startswith(MARK + " SERVERFAIL"):
            server_up = False
            continue
        if line.startswith(MARK + " DONE"):
            continue
        if cur is not None:
            segs[cur].append(line)
    return {k: "\n".join(v) for k, v in segs.items()}, exits, server_up


def run_lesson(lesson, manifest, keep_going=False, timeout=900):
    lid = lesson["id"]
    # A self-test fixture carries an absolute path; a real lesson is relative
    # to content/.
    src = Path(lesson["file"])
    if not src.is_absolute():
        src = CONTENT / src
    blocks, errors = extract(src)
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
