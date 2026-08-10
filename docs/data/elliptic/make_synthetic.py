#!/usr/bin/env python3
"""Generate a synthetic transaction graph shaped like the Elliptic dataset.

WHY THIS EXISTS. The Elliptic Bitcoin dataset is distributed under
CC BY-NC-ND 4.0. NoDerivatives means a sampled subset is plausibly adapted
material that may not be redistributed, and NonCommercial is awkward for
documentation of a commercial database. So this site ships no Elliptic data at
all. `run-01` teaches against a synthetic graph of the same shape, and tells
the reader how to fetch the real dataset for themselves.

WHAT "SAME SHAPE" MEANS, from the T12 audit of GNN-test-and-improve:

  165 features per node   Kaggle documents 166, but the CSV carries 167 columns:
                          a transaction id, a time step, and 165 feature values.
                          The vector index must be configured for 165.
  3 classes               licit, illicit, unknown. The real set is heavily
                          imbalanced and mostly unknown, which is reproduced.
  49 time steps           transactions arrive in discrete batches.
  directed edges          money flows one way, from input to output.

The numbers here are invented. The structure, the dimensionality and the class
imbalance are not, so code written against this runs unchanged against the real
thing.

Deterministic: seeded.

Usage:
    python3 make_synthetic.py [n_nodes]
"""
import csv
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent
SEED = 20260810
FEATURES = 165
TIME_STEPS = 49
# Roughly the real proportions: a small illicit minority, a larger licit
# minority, and a majority that was never labelled.
CLASS_MIX = [("illicit", 0.02), ("licit", 0.21), ("unknown", 0.77)]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    rng = random.Random(SEED)

    labels, cuts = [], []
    total = 0.0
    for name, share in CLASS_MIX:
        total += share
        cuts.append((total, name))

    def pick():
        r = rng.random()
        for cut, name in cuts:
            if r <= cut:
                return name
        return "unknown"

    nodes = []
    for i in range(1, n + 1):
        cls = pick()
        step = rng.randint(1, TIME_STEPS)
        # Illicit transactions sit slightly apart in feature space. Real
        # separation is subtler; this keeps the lesson's training run short.
        centre = 0.6 if cls == "illicit" else 0.0
        feats = [round(rng.gauss(centre, 1.0), 4) for _ in range(FEATURES)]
        nodes.append((i, step, cls, feats))
        labels.append(cls)

    # Money flows forward in time, and illicit funds move among themselves more
    # often than chance, which is the structure a graph model can exploit.
    by_step = {}
    for i, step, cls, _ in nodes:
        by_step.setdefault(step, []).append((i, cls))

    edges = []
    for i, step, cls, _ in nodes:
        for _ in range(rng.randint(1, 3)):
            nxt = min(step + rng.randint(0, 2), TIME_STEPS)
            pool = by_step.get(nxt) or by_step[step]
            if cls == "illicit":
                same = [t for t, c in pool if c == "illicit"]
                target = rng.choice(same) if same and rng.random() < 0.5 \
                    else rng.choice(pool)[0]
            else:
                target = rng.choice(pool)[0]
            if target != i:
                edges.append((i, target))

    with (HERE / "features.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        for i, step, cls, feats in nodes:
            w.writerow([i, step, cls, *feats])
    with (HERE / "edges.csv").open("w", newline="") as fh:
        csv.writer(fh).writerows(sorted(set(edges)))

    counts = {name: labels.count(name) for name, _ in CLASS_MIX}
    print(f"{len(nodes)} nodes ({FEATURES} features each), "
          f"{len(set(edges))} edges, classes {counts}")


if __name__ == "__main__":
    main()
