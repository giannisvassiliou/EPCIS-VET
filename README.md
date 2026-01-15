# EPCIS-VET
# Veterinary-Aware EPCIS Traceability Experiments

This repository contains the experimental code and synthetic data generators used in the paper:

**Integrating veterinary public health data into EPCIS-based digital traceability for dairy supply chains**  
Stavroula Chatzinikolaou, Giannis Vassiliou, Nikos Papadakis  
(submitted to / published in *Computers and Electronics in Agriculture*)

The code enables full reproduction of the synthetic evaluations reported in the paper, including:
- Risk propagation across milk → cheese transformation events
- Regulatory compliance checking
- Quantitative recall-scope reduction under delayed contamination detection

---

## Repository Structure

```
.
├── data_generation/
│   ├── generate_supply_chain.py     # Synthetic dairy supply-chain generator
│   ├── inject_contamination.py      # Delayed contamination and risk injection
│
├── experiments/
│   ├── recall_simulation.py         # Baseline vs trace-forward recall strategies
│   ├── metrics.py                   # Precision, recall, scope-reduction metrics
│
├── config/
│   └── parameters.yaml              # Experimental parameters (W, k, prevalence)
│
├── outputs/
│   ├── sample_results.csv           # Example output (non-authoritative)
│
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Experimental Scope

The experiments are **synthetic but process-consistent**, designed to reflect realistic
dairy production and traceability constraints while enabling controlled validation.

They correspond directly to:

- **Section 5.1** – Functional validation (risk propagation, traceability completeness, compliance checking)
- **Section 5.2** – Quantitative evaluation of recall-scope reduction (Tables 2–6)

No real farm, veterinary, or commercial data are used.

---

## Requirements

- Python ≥ 3.9  
- Tested on Linux and macOS

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## Reproducing the Experiments

### 1. Generate the synthetic supply-chain dataset

```bash
python data_generation/generate_supply_chain.py   --config config/parameters.yaml   --output data/
```

This step creates:
- Dairy farms
- Milk lots
- Cheese batches
- Transformation relationships
- Packaged distribution units

A fixed random seed is used to ensure reproducibility.

---

### 2. Inject delayed contamination events

```bash
python data_generation/inject_contamination.py   --input data/   --output data/
```

This simulates:
- Low-prevalence contamination
- Laboratory confirmation delays (7–14 days)
- Assignment of zoonotic risk levels

---

### 3. Run recall-scope experiments

```bash
python experiments/recall_simulation.py   --input data/   --config config/parameters.yaml   --output results/
```

This evaluates:
- Baseline time-window recall strategy
- Proposed EPCIS trace-forward recall strategy

---

### 4. Compute evaluation metrics

```bash
python experiments/metrics.py   --input results/   --output results/summary.csv
```

The output reproduces:
- Recall scope
- Precision and recall
- Recall-scope reduction percentages

Values correspond to **Table 6** in the paper (subject to floating-point variation).

---

## Configuration Parameters

Key parameters are defined in `config/parameters.yaml`, including:

- `W`: Time-window size (hours) for baseline recalls
- `k`: Number of milk lots per cheese batch
- `prevalence`: Contamination prevalence
- `production_days`
- `random_seed`

Changing these values allows sensitivity analysis while preserving the experimental logic.

---

## Notes on EPCIS and Semantics

This repository focuses on **experimental evaluation logic** rather than full EPCIS event repositories.

- EPCIS concepts (ObjectEvents, TransformationEvents, dispositions) are represented abstractly
- Semantic reasoning is emulated through deterministic propagation rules consistent with the paper
- Full EPCIS payload examples and schemas are provided in the paper’s Supplementary Material

---

## Reproducibility and Citation

If you use this code or adapt it for further research, please cite the associated paper.

A Zenodo DOI will be added upon publication.

---

## License

This project is released under the MIT License.

---

## Contact

For questions or issues related to this repository, please contact:

- Giannis Vassiliou – vassil@hmu.gr  
- Nikos Papadakis – npapadak@hmu.gr
