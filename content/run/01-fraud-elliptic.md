<!-- SEO subtitle (meta description): Train a graph neural network inside AstraeaDB to classify transactions, in Rust, and learn why accuracy is the wrong number to report on fraud data. -->

# Finding Fraud: Classifying Bitcoin Transactions with an In-Database GNN

*Train a model on the graph without taking the graph out of the database, then work out whether the result is any good.*

Everything so far has queried a graph. This post trains a model on one. The technique is a graph neural network, which learns from a node's own features **and** from the features of the nodes it connects to, so a transaction is judged partly by the company it keeps.

Two things make this lesson different from the rest of the site, and both are worth explaining before any code.

## Why this one is in Rust

Every other lesson talks to AstraeaDB over the network from Python or R. This one cannot. The graph neural network lives in the `astraea-gnn` crate, and there is no wire command for it: the server's request protocol has no "train a model" verb. Training is a library call, so the program has to be linked against the database rather than connected to it.

That is not only a limitation. Training means reading every node's features many times over, and doing it in-process avoids moving all of that across a socket for every epoch.

## Why there is no data here

The obvious dataset for this is the Elliptic Bitcoin dataset: 203,769 transactions labelled licit, illicit or unknown. This site ships none of it.

It is distributed under **CC BY-NC-ND 4.0**. NoDerivatives means a sampled subset is plausibly adapted material that may not be redistributed, and NonCommercial sits badly with documentation for a commercial database. Compare `data/lanl/`, which is CC0 and ships freely: two public research datasets, opposite answers about what you may pass on. It is worth checking, every time, rather than assuming that "public" means "yours to redistribute".

So this lesson generates a graph with the same *shape* and trains on that. The shape is what matters for the code:

- **165 features per node.** Kaggle's documentation says 166, but the file has 167 columns: a transaction id, a time step, and 165 values. The vector index has to match the data, not the documentation.
- **A heavy class imbalance**, with illicit transactions a small minority. This turns out to be the most important property of the whole exercise.
- **Directed edges**, because money moves one way.

To use the real dataset, fetch it yourself under its own licence with
`kaggle datasets download -d ellipticco/elliptic-data-set`, and point the same code at it.

## Setting up

The dependencies are the database and the model crate:

<!-- verify: skip reason="the harness generates this Cargo.toml for the lesson's blocks; a second copy here would not be read" -->
```toml
[dependencies]
astraea-core = "0.3.1"
astraea-graph = { version = "0.3.1", features = ["test-utils"] }
astraea-gnn = "0.3.1"
rand = "0.8"
serde_json = "1"
```

```rust
use astraea_core::traits::GraphOps;
use astraea_gnn::{train_node_classification, MessagePassingConfig, TrainingConfig, TrainingData};
use astraea_graph::test_utils::InMemoryStorage;
use astraea_graph::Graph;
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use std::collections::HashMap;

const FEATURES: usize = 165;        // what the real file actually contains
const SIGNAL_FEATURES: usize = 6;   // only a few of them mean anything
const SEPARATION: f32 = 0.9;
```

`SIGNAL_FEATURES` deserves a note. It would be easy to generate data where all 165 features differ between classes, and the model would then reach perfect accuracy immediately and teach you nothing. Real feature sets are mostly weak or irrelevant, so here only six columns carry signal and the other 159 are noise the model has to see past.

## Building the graph

The graph is held in-process. Every transaction is a node carrying its 165 features as an embedding, and edges follow the flow of funds:

```rust
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut rng = StdRng::seed_from_u64(20260810);
    let graph = Graph::new(Box::new(InMemoryStorage::new()));

    let n = 400usize;
    let mut ids = Vec::new();
    let mut labels: HashMap<_, usize> = HashMap::new();

    for _ in 0..n {
        let illicit = rng.gen_bool(0.10);
        let centre = if illicit { SEPARATION } else { 0.0 };
        let feats: Vec<f32> = (0..FEATURES)
            .map(|f| {
                let base = rng.gen::<f32>() - 0.5;
                if f < SIGNAL_FEATURES { base + centre } else { base }
            })
            .collect();

        let id = graph.create_node(
            vec!["Tx".into()],
            serde_json::json!({ "illicit": illicit }),
            Some(feats),
        )?;

        // Only half the transactions are labelled, as in the real dataset,
        // where most are unknown.
        if rng.gen_bool(0.5) {
            labels.insert(id, if illicit { 1 } else { 0 });
        }
        ids.push((id, illicit));
    }

    // Illicit funds move among themselves more often than chance. That
    // correlation is the thing a graph model can use and a per-row model cannot.
    for k in 0..n {
        let (a, a_illicit) = ids[k];
        for _ in 0..2 {
            let (b, b_illicit) = ids[rng.gen_range(0..n)];
            if a != b && (a_illicit == b_illicit || rng.gen_bool(0.3)) {
                graph.create_edge(a, b, "SENT_TO".into(),
                                  serde_json::json!({}), 1.0, None, None)?;
            }
        }
    }

    println!("graph: {} nodes, {} labelled", n, labels.len());
```

## Training

```rust
    let cfg = TrainingConfig {
        layers: 2,                  // two rounds of neighbour aggregation
        learning_rate: 0.05,
        epochs: 30,
        message_passing: MessagePassingConfig::default(),
        hidden_dim: Some(32),       // Some(_) selects real backpropagation
        use_adam: true,
        early_stopping_patience: None,
        validation_split: Some(0.3),
    };

    let data = TrainingData { labels, num_classes: 2 };
    let out = train_node_classification(&graph, &data, &cfg)?;

    println!("first loss {:.4}  last loss {:.4}  accuracy {:.3}",
             out.epoch_losses[0],
             out.epoch_losses[out.epoch_losses.len() - 1],
             out.accuracy);
```

`layers: 2` is the graph part. One layer lets a node see its neighbours; two lets it see its neighbours' neighbours. And `hidden_dim: Some(32)` is not a detail: with `None`, the crate falls back to an older path that adjusts edge weights by finite differences rather than learning weight matrices by backpropagation.

You should see the loss fall and an accuracy around 0.98. Do not celebrate yet.

## The number that matters

An accuracy of 0.98 on fraud data means almost nothing, and the reason is the class imbalance. If a tenth of the transactions are illicit, a model that simply answers "licit" every single time scores 0.90 without learning anything at all. Always compute that floor, and always look at the class you actually care about:

```rust
    let n_labelled = data.labels.len() as f32;
    let n_illicit = data.labels.values().filter(|&&c| c == 1).count() as f32;
    println!("always-licit baseline accuracy: {:.3}",
             (n_labelled - n_illicit) / n_labelled);

    let (mut tp, mut fp, mut fneg) = (0.0f32, 0.0f32, 0.0f32);
    for (id, &truth) in data.labels.iter() {
        match (truth, *out.final_predictions.get(id).unwrap_or(&0)) {
            (1, 1) => tp += 1.0,
            (0, 1) => fp += 1.0,
            (1, 0) => fneg += 1.0,
            _ => {}
        }
    }
    let precision = if tp + fp > 0.0 { tp / (tp + fp) } else { 0.0 };
    let recall = if tp + fneg > 0.0 { tp / (tp + fneg) } else { 0.0 };
    println!("illicit class: precision {:.3}  recall {:.3}  (tp={} fp={} fn={})",
             precision, recall, tp as i32, fp as i32, fneg as i32);

    Ok(())
}
```

Now the result is readable. The run is seeded, so you should see accuracy about 0.985 against a floor of 0.904. The model did learn something, and the gap is eight points rather than the ninety-eight the headline implied.

Precision comes out near 0.94, meaning roughly one in eighteen flagged transactions is innocent, which is the workload you are handing whoever reviews them. Recall near 0.90 means about one illicit transaction in ten slips past. On this run that is seventeen caught, one false alarm, two missed.

Those two numbers trade against each other, and which way you want to lean is a business decision rather than a modelling one. An exchange freezing accounts cares about precision, because every false positive is an angry customer. An investigator generating leads cares about recall, because a missed case is invisible.

One caution on the reported `accuracy` field: it is measured over the labelled set, so it tells you how well the model fits data it has seen. `validation_split` holds part of that back during training, but if you want a number you can defend, keep your own test set aside and never train on it.

## Against the real dataset

The code above changes very little. You read the features from the CSV instead of generating them, keep 165 columns, and use the real labels. What changes is scale, 203,769 nodes rather than 400, and difficulty, because the real signal is far subtler than six obliging columns. Expect a much smaller gap between your model and the trivial baseline, and expect that gap to be the entire result.

## That is the path

You have gone from installing a database to training a model inside it. Along the way the graph has been a movie catalogue, a novel, a data lake, a codebase, a network under attack, and a ledger of transactions. The techniques were the same each time: give things identity, connect them, describe them so they can be found by meaning, and keep a trail back to the evidence.

The [glossary](../glossary.html) collects every term the path uses, and the [verification status](../status.html) page shows which of these lessons is machine-checked and which is not.
