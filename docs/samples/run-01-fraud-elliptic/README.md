# Fraud detection with an in-database GNN

The finished program from [Finding Fraud: Classifying Bitcoin Transactions with
an In-Database GNN](https://astraeadb.github.io/getting-started/run/01-fraud-elliptic.html).
It builds a transaction graph, trains a two-layer graph neural network on it
inside AstraeaDB, and then scores the result honestly.

`Cargo.toml` and `src/main.rs` are **generated from the lesson** by
`site/sync_samples.py`, and `just build` fails if they fall out of step. What
you run here is exactly what the page shows you, and it is the same code the
verification harness executes in a clean container.

## Running it

```bash
cargo run --release
```

Nothing else is needed: no server, no dataset, no API key. The graph is built
in process, and the model trains against it in memory.

The first build compiles AstraeaDB from source and takes several minutes. Later
runs take about a second. `--release` is not optional in spirit — a debug build
trains perhaps twenty times slower.

## What you should see

Exactly this, every time:

```
graph: 400 nodes, 198 labelled
first loss 1.9072  last loss 0.0000  accuracy 0.975
always-licit baseline accuracy: 0.904
illicit class: precision 1.000  recall 0.737  (tp=14 fp=0 fn=5)
```

The last two lines are the interesting ones, and the lesson spends most of its
length on why. An accuracy of 0.975 sounds excellent until you notice that
answering "licit" every single time scores 0.904 on this data.

"Every time" is worth dwelling on. The program calls
`train_node_classification_with_rng` and hands it the same seeded `StdRng` that
built the graph. The shorter `train_node_classification` initializes the model's
weights from `rand::thread_rng()` instead, so seeding your own generator buys
you nothing: five runs of an identical binary produced recall from 0.632 to
1.000. If you change this program and the output starts moving, check that the
seeded generator is still reaching the trainer.

## Changing it

A few constants near the top of `src/main.rs` are worth moving:

| Constant | Effect |
| --- | --- |
| `SIGNAL_FEATURES` | How many of the 165 features carry any signal. Raise it and the task becomes trivial; drop it to 2 and watch recall collapse. |
| `SEPARATION` | How far apart the two classes sit. This is the difficulty dial. |
| `n` in `main` | Graph size. 400 nodes trains in about a second. |
| `layers` in `TrainingConfig` | Set it to 1 to see how much the second hop of neighbours is worth. |

Setting `hidden_dim` to `None` is a bigger change than it looks: it selects an
older code path in `astraea-gnn` that nudges edge weights by finite differences
instead of learning weight matrices by backpropagation.

## Using the real Elliptic dataset

This program generates a graph with the same *shape* as the Elliptic Bitcoin
dataset rather than shipping it. The dataset is licensed CC BY-NC-ND 4.0, and
NoDerivatives makes redistributing a sampled subset legally doubtful. Fetch it
yourself under its own licence:

```bash
kaggle datasets download -d ellipticco/elliptic-data-set
```

Then replace the node-creation loop with a reader over
`elliptic_txs_features.csv`, keeping **165** feature columns — the file has 167,
of which the first two are a transaction id and a time step — and take labels
from `elliptic_txs_classes.csv`, where `1` is illicit, `2` is licit and
`unknown` is unlabelled. Edges come from `elliptic_txs_edgelist.csv`. Everything
from `TrainingConfig` onwards stays as it is.

Expect a much smaller gap between the model and the always-licit baseline than
you see here. On real data that gap is the entire result.
