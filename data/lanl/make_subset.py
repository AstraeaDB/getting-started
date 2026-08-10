#!/usr/bin/env python3
"""Cut the shipped LANL slice from the full dataset. Deterministic.

The Los Alamos National Laboratory "Comprehensive Multi-Source Cyber-Security
Events" dataset is released into the public domain under CC0, so a derived
subset may be redistributed. This script records exactly how the shipped files
were produced, so the slice is reproducible rather than a mystery blob.

Source:  https://csr.lanl.gov/data/cyber1/
Licence: CC0 1.0 Universal (public domain dedication)

Usage:
    python3 make_subset.py <full_dns.csv> <full_redteam.csv> <outdir>

The window brackets the whole red-team campaign rather than selecting by host,
so the slice is an honest span of time and not a set of events chosen because
they are interesting.
"""
import csv
import pathlib
import sys

WINDOW = (140_000, 245_000)   # seconds from the start of the capture


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    dns_in, rt_in, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    lo, hi = WINDOW

    kept = 0
    with open(dns_in) as fh, (outdir / "dns.csv").open("w", newline="") as out:
        w = csv.writer(out)
        for row in csv.reader(fh):
            if row and lo <= int(row[0]) <= hi:
                w.writerow(row)
                kept += 1

    rt = 0
    with open(rt_in) as fh, (outdir / "redteam.csv").open("w", newline="") as out:
        w = csv.writer(out)
        for row in csv.reader(fh):
            if row and lo <= int(row[0]) <= hi:
                w.writerow(row)
                rt += 1

    print(f"window {lo}..{hi}: {kept} dns rows, {rt} redteam rows -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
