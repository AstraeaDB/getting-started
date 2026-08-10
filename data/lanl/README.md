# LANL cyber-security events, sampled slice

A slice of the Los Alamos National Laboratory **Comprehensive Multi-Source
Cyber-Security Events** dataset, used by the Run tier lessons.

- **Source:** <https://csr.lanl.gov/data/cyber1/>
- **Licence:** CC0 1.0 Universal, a public domain dedication. That is what makes
  redistributing this derived slice possible. (Contrast the Elliptic dataset
  used by `run-01`, which is CC BY-NC-ND and therefore is *not* shipped here.)
- **Citation:** A. D. Kent, *Comprehensive, Multi-Source Cyber-Security Events*,
  Los Alamos National Laboratory (2015).

## What is here

| File | Rows | Columns |
| --- | ---: | --- |
| `dns.csv` | 7,937 | `time, source_computer, resolved_computer` |
| `redteam.csv` | 25 | `time, user@domain, source_computer, destination_computer` |

`redteam.csv` is ground truth: authentication events the dataset's authors have
labelled as red-team activity. It is what lets a lesson say whether a hunt found
the right thing.

## How it was cut

`make_subset.py` keeps every event in the window 140,000 to 245,000 seconds,
which brackets the entire red-team campaign. Selecting a span of time rather
than a set of hosts keeps the slice honest: nothing was included because it
looked interesting.

Regenerate it from the full download with:

```bash
python3 make_subset.py full_dns.csv full_redteam.csv .
```
