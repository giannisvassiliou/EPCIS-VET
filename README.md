# Code for the Paper Experiments

This repository contains **only two Python scripts**, implementing the **two experiments** reported in the paper:

**Integrating veterinary public health data into EPCIS-based digital traceability for dairy supply chains**  
Stavroula Chatzinikolaou, Giannis Vassiliou, Nikos Papadakis

There is **no other code** in this repository.

---

## Files in this repository

```
functional.py
recall_experiment.py
README.md
```

---

## Python Version

- Python **3.9 or newer**

---

## Required Python Libraries

### Standard library modules (included with Python)

These require **no installation**:
- `json`
- `time`
- `random`
- `statistics`
- `typing`
- `argparse`
- `os`
- `datetime`

---

### Third‑party Python libraries

These **must be installed separately**:

#### Used by `functional.py`
- `psycopg2` (PostgreSQL client library)
- `rdflib` (RDF graphs and SPARQL queries)

#### Used by `recall_experiment.py`
- `numpy`
- `pandas`

Install all required libraries with:

```bash
pip install psycopg2-binary rdflib numpy pandas
```

---

## External Software

- **PostgreSQL** (required only for `functional.py`)
  - Used to emulate incremental ingestion via `LISTEN / NOTIFY`
  - Connection string is defined inside the script and may be adjusted

---

## 1) Functional Validation Experiment (`functional.py`)

Implements the functional checks described in the manuscript (Section 5.1):

- Risk propagation from milk lots to derived cheese batches
- End‑to‑end traceability queries (Cheese → Milk → Farm)
- Automatic detection of a missing mandatory quality‑testing event
- Measurement of SQL‑to‑RDF translation latency

Run:
```bash
python functional.py
```

---

## 2) Recall‑Scope Reduction Experiment (`recall_experiment.py`)

Implements the quantitative recall experiment described in Section 5.2:

- **Baseline**: line‑level time‑window recall (±W hours)
- **Proposed**: trace‑forward recall using explicit batch derivation

Run (example):
```bash
python recall_experiment.py --seed 7 --mixing_k 4 --W 24 --outdir outputs
```

Outputs CSV files containing recall scope and precision metrics.

---

## Reproducibility

- All data are **synthetic**
- Random seeds are configurable
- No real farm, veterinary, or commercial data are used

---

## Citation

If you use or adapt this code, please cite the associated paper.

---

## License

MIT License
