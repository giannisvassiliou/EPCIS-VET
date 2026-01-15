# Experimental Code for the Paper

This repository contains **only the two Python scripts** used to produce the experimental results reported in the paper:

**Integrating veterinary public health data into EPCIS-based digital traceability for dairy supply chains**  
Stavroula Chatzinikolaou, Giannis Vassiliou, Nikos Papadakis

No additional framework, libraries, datasets, or supporting scripts are included.

---

## Repository Contents

```
.
├── functional.py
├── recall_experiment.py
└── README.md
```

---

## Experiment 1 – Functional Validation (`functional.py`)

This script implements the **functional validation** described in **Section 5.1** of the paper.

It demonstrates, using synthetic data:

- Propagation of veterinary zoonosis risk from milk batches to derived cheese batches
- End-to-end traceability (Cheese → Milk → Farm) using RDF/SPARQL queries
- Automatic detection of a missing mandatory quality-testing event
- Measurement of SQL-to-RDF translation latency under incremental updates

All data are generated internally by the script or inserted programmatically.
No external datasets are required.

Run:
```bash
python functional.py
```

(Requires a local PostgreSQL instance and the Python dependencies used in the script.)

---

## Experiment 2 – Recall-Scope Reduction (`recall_experiment.py`)

This script implements the **quantitative recall-scope experiment** described in **Section 5.2** of the paper.

It generates a synthetic cheese supply-chain dataset and compares:

- A **baseline** time-window recall strategy (±W hours, same processing line)
- A **proposed** trace-forward recall strategy based on explicit batch derivation

The script outputs CSV files with recall scope, precision, recall, and scope-reduction metrics,
reproducing **Table 6** in the paper (up to stochastic variation).

Run:
```bash
python recall_experiment.py --seed 7 --mixing_k 4 --W 24 --outdir outputs
```

---

## Reproducibility

- Both scripts rely exclusively on **synthetic, process-consistent data**
- Random seeds are configurable via command-line arguments
- No real farm, veterinary, or commercial data are used

The code is intentionally minimal and corresponds **one-to-one** with the experiments reported in the manuscript.

---

## Citation

If you use or adapt this code, please cite the associated paper.

---

## License

MIT License
