#!/usr/bin/env python3
"""Pull runnable code blocks out of a lesson's markdown.

A directive is an HTML comment on the line immediately before the fence.
HTML comments are invisible in the rendered page, so a directive never leaks
into the reader's view (DESIGN.md 7.3).

    <!-- verify: skip reason="needs a Kaggle account" -->
    <!-- verify: expect-output -->
    <!-- verify: setup -->
    <!-- verify: continues -->
    <!-- verify: expect-error -->

Run directly to see what would execute:

    python3 verify/extract.py content/crawl/py-01-getting-started.md
"""

import json
import re
import shlex
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Languages we actually execute. Anything else (toml, json, text, output
# samples) is illustrative and is not run.
RUNNABLE = {"bash": "bash", "sh": "bash", "python": "python", "py": "python", "r": "r",
            "rust": "rust"}

FENCE_OPEN = re.compile(r"^([ \t]*)(`{3,}|~{3,})[ \t]*([A-Za-z0-9_+-]*)[ \t]*$")
DIRECTIVE = re.compile(r"^[ \t]*<!--[ \t]*verify:[ \t]*(.*?)[ \t]*-->[ \t]*$")


@dataclass
class Block:
    index: int
    lang: str
    code: str
    line: int
    skip: bool = False
    reason: str = ""
    expect_output: bool = False
    expected: str = ""
    setup: bool = False
    continues: bool = False
    expect_error: bool = False
    runnable: bool = True

    def to_json(self):
        return asdict(self)


def parse_directive(text):
    """`skip reason="..."` -> {"skip": True, "reason": "..."}"""
    out = {}
    try:
        parts = shlex.split(text)
    except ValueError:
        parts = text.split()
    for p in parts:
        if "=" in p:
            k, _, v = p.partition("=")
            out[k.strip().replace("-", "_")] = v.strip()
        elif p:
            out[p.strip().replace("-", "_")] = True
    return out


def extract(path):
    """Return (blocks, errors). Errors are directive misuse, not code failures."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    blocks, errors = [], []
    pending = {}
    pending_line = 0
    i, idx = 0, 0

    while i < len(lines):
        line = lines[i]

        d = DIRECTIVE.match(line)
        if d:
            pending = parse_directive(d.group(1))
            pending_line = i + 1
            i += 1
            continue

        m = FENCE_OPEN.match(line)
        if not m:
            # A directive must sit immediately before a fence. A blank line is
            # tolerated; anything else means the author expected it to apply to
            # something it will not apply to, which is worth saying out loud.
            if pending and line.strip():
                errors.append(
                    f"{path}:{pending_line}: verify directive is not immediately "
                    f"before a code fence (found {line.strip()[:40]!r})"
                )
                pending = {}
            i += 1
            continue

        indent, fence, lang = m.group(1), m.group(2), (m.group(3) or "").lower()
        body, j = [], i + 1
        closer = re.compile(r"^[ \t]*" + fence[0] + "{" + str(len(fence)) + r",}[ \t]*$")
        while j < len(lines) and not closer.match(lines[j]):
            body.append(lines[j])
            j += 1
        code = "\n".join(body)

        norm = RUNNABLE.get(lang)
        blk = Block(
            index=idx, lang=norm or lang, code=code, line=i + 1,
            runnable=norm is not None,
        )
        if pending:
            blk.skip = bool(pending.get("skip"))
            blk.reason = pending.get("reason", "") if isinstance(pending.get("reason"), str) else ""
            blk.expect_output = bool(pending.get("expect_output"))
            blk.setup = bool(pending.get("setup"))
            blk.continues = bool(pending.get("continues"))
            blk.expect_error = bool(pending.get("expect_error"))
            if blk.skip and not blk.reason:
                # Enforced here so a silent skip cannot reach the status page.
                errors.append(
                    f"{path}:{blk.line}: `verify: skip` requires reason=\"...\". "
                    "Skipping must be visible on /status.html, not silent."
                )
            pending = {}

        # An expect-output block is followed by the text block holding what it
        # should print. Consume that block so it is not treated as code.
        if blk.expect_output:
            k = j + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            m2 = FENCE_OPEN.match(lines[k]) if k < len(lines) else None
            if not m2:
                errors.append(
                    f"{path}:{blk.line}: `verify: expect-output` must be followed by "
                    "a fenced block holding the expected output."
                )
            else:
                f2 = m2.group(2)
                closer2 = re.compile(r"^[ \t]*" + f2[0] + "{" + str(len(f2)) + r",}[ \t]*$")
                exp, n = [], k + 1
                while n < len(lines) and not closer2.match(lines[n]):
                    exp.append(lines[n])
                    n += 1
                blk.expected = "\n".join(exp)
                j = n

        if blk.runnable:
            blocks.append(blk)
            idx += 1
        i = j + 1

    if pending:
        errors.append(f"{path}:{pending_line}: verify directive at end of file with no code fence")
    return blocks, errors


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    blocks, errors = extract(sys.argv[1])
    for e in errors:
        print(f"extract: error: {e}", file=sys.stderr)
    print(json.dumps([b.to_json() for b in blocks], indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
