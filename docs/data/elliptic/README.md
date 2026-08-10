# Elliptic: why there is no data here

`run-01` teaches graph neural network classification on transaction data. It
ships **no data**, deliberately.

The [Elliptic Bitcoin dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set)
is distributed under **CC BY-NC-ND 4.0**. Two clauses rule out shipping a
sample:

- **NoDerivatives.** A sampled subset is plausibly "adapted material" under
  CC 4.0, and ND forbids distributing adapted material.
- **NonCommercial.** This is documentation for a commercial database.

Contrast `data/lanl/`, which is CC0 and therefore ships freely. Two public
research datasets, opposite answers about what you may pass on.

## What run-01 does instead

The lesson generates a synthetic graph with the same *shape* as Elliptic and
trains on that. The numbers are invented; the structure is not:

| Property | Value | Why it matters |
| --- | --- | --- |
| Features per node | **165** | Kaggle documents 166, but the CSV has 167 columns: an id, a time step, and 165 values. The vector index must match. |
| Classes | 3 | licit, illicit, unknown |
| Class balance | heavily skewed | most nodes are unlabelled, which is what makes the real problem hard |
| Time steps | 49 | transactions arrive in discrete batches |
| Edges | directed | money flows one way |

Code written against the synthetic graph runs unchanged against the real one.

`make_synthetic.py` here is a reference implementation in Python. The lesson
itself generates its graph in Rust, in-process, so there is no file to parse and
nothing to download.

## Using the real dataset

Fetch it yourself, under its own licence:

```bash
kaggle datasets download -d ellipticco/elliptic-data-set -p data/ --unzip
```

Attribution, which CC BY requires of any use: Elliptic, *Elliptic Data Set*,
via Kaggle.
