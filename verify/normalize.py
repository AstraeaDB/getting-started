#!/usr/bin/env python3
"""Mask the parts of program output that legitimately vary between runs.

Without this, every expect-output comparison fails on the second run because a
node id moved or a query took a different number of milliseconds. The masks are
deliberately narrow: anything broader starts hiding real regressions, which is
the failure mode that makes a verification suite worthless (DESIGN.md 7.3).
"""

import re
import sys

RULES = [
    # ISO-8601 timestamps, with or without a zone.
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
     "<TIMESTAMP>"),
    # Bare dates.
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "<DATE>"),
    # Durations: "in 12ms", "took 1.4s", "elapsed 220 us".
    (re.compile(r"\b\d+(?:\.\d+)?\s*(?:ns|us|µs|ms|s|sec|secs|seconds)\b"), "<DURATION>"),
    # Node and edge ids as the clients print them.
    (re.compile(r"\b(node|edge|Node|Edge)[ _]?(?:id|Id|ID)[ =:]+\d+"), r"\1_id=<ID>"),
    (re.compile(r"\bNodeId\((\d+)\)"), "NodeId(<ID>)"),
    (re.compile(r"\bEdgeId\((\d+)\)"), "EdgeId(<ID>)"),
    # Hex object addresses, e.g. <object at 0x10f3c2e50>.
    (re.compile(r"0x[0-9a-fA-F]{6,}"), "0x<ADDR>"),
    # Temp paths.
    (re.compile(r"/tmp/[A-Za-z0-9_.-]+"), "/tmp/<TMP>"),
    # pid noise.
    (re.compile(r"\bpid[ =:]+\d+", re.I), "pid=<PID>"),
]

# Floats past the fourth decimal place. Distances and scores wobble in the last
# bits across builds and architectures; the first four places are the claim a
# lesson is actually making.
FLOAT = re.compile(r"\b(\d+\.\d{4})\d+\b")


def normalize(text):
    out = text.replace("\r\n", "\n")
    for pattern, repl in RULES:
        out = pattern.sub(repl, out)
    out = FLOAT.sub(r"\1", out)
    # Trailing whitespace and a trailing blank line are never the point.
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    return out.strip()


def matches(actual, expected):
    return normalize(actual) == normalize(expected)


def main():
    text = sys.stdin.read()
    sys.stdout.write(normalize(text) + "\n")


if __name__ == "__main__":
    main()
