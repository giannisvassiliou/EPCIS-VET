# Integrating veterinary public health data into EPCIS-based digital traceability for dairy supply chains

Digital traceability systems are widely used in agri-food supply chains to support transparency and food safety, yet in dairy production they typically capture only product and logistics events, remaining disconnected from veterinary public health data. This limits their ability to support automated risk detection, compliance verification, and targeted recalls.

This paper presents a computational framework that integrates structured veterinary public health controls directly into EPCIS-based digital traceability for cheese production. The approach extends standard EPCIS event models using Common Business Vocabulary extensions, instance and lot master data, and event-level metadata to encode herd health status, milk quality indicators, inspection outcomes, and zoonotic risk parameters. Semantic interoperability and automated reasoning are enabled through an RDF/OWL ontology implemented via a hybrid SQL-to-RDF architecture that preserves transactional performance.

A representative cheese supply-chain use case and a synthetic evaluation demonstrate correct risk propagation, improved recall scoping, and near-real-time operational performance. The proposed framework is compatible with existing traceability infrastructures and provides a scalable, health-aware foundation for digital food safety systems in dairy supply chains.

# Code for the Paper Experiments

This repository contains  **two Python scripts**, implementing the **two experiments** reported in the paper:

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

---

---

## License

MIT License
