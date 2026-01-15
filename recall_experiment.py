"""Recall Scope Experiment (Baseline vs Veterinary-aware Traceability)

Baseline: line-level time-window recall (±W hours around detected batch production time)
Proposed: trace-forward recall only the detected batch's derived cases

This script generates a synthetic dataset and runs the experiment.
Outputs: CSVs including recall_results.csv.

Run:
  python recall_experiment.py --seed 7 --mixing_k 4 --W 24 --outdir outputs
"""

import argparse
import os
import datetime as dt
import numpy as np
import pandas as pd

def generate_dataset_fast(
    seed: int = 7,
    n_days: int = 14,
    n_farms: int = 15,
    milk_lots_per_day: int = 40,
    cheese_batches_per_day: int = 15,
    mixing_k: int = 4,
    contamination_rate: float = 0.03,
    lab_delay_days_min: int = 7,
    lab_delay_days_max: int = 14,
    w_hours_baseline: int = 24,
    line_count: int = 2,
    maturation_rooms: int = 3,
    avg_cases_per_batch: int = 60,
    case_size_units: int = 10,
    ship_days_per_week: int = 6,
):
    rng = np.random.default_rng(seed)
    start_date = dt.datetime(2025, 1, 1, 6, 0, 0)
    farms = np.array([f"FARM-{i:03d}" for i in range(1, n_farms + 1)], dtype=object)

    # Milk lots
    milk_rows = []
    lot_counter = 1
    for d in range(n_days):
        day_time = start_date + dt.timedelta(days=d)
        mins = rng.integers(0, 12 * 60, size=milk_lots_per_day)
        times = [ (day_time + dt.timedelta(minutes=int(m))).isoformat() for m in mins ]
        farm_ids = farms[rng.integers(0, n_farms, size=milk_lots_per_day)]
        scc = np.clip(rng.normal(180_000, 60_000, size=milk_lots_per_day), 50_000, 600_000).astype(int)
        antibiotic = rng.random(milk_lots_per_day) < 0.005
        herd_free = rng.random(milk_lots_per_day) < 0.95
        vol = np.clip(rng.normal(500, 120, size=milk_lots_per_day), 150, 900)
        for j in range(milk_lots_per_day):
            milk_rows.append({
                "milk_lot_id": f"ML-{lot_counter:06d}",
                "farm_id": farm_ids[j],
                "collection_time": times[j],
                "scc": int(scc[j]),
                "antibiotic_residue": bool(antibiotic[j]),
                "herd_health_free": bool(herd_free[j]),
                "volume_liters": float(vol[j]),
            })
            lot_counter += 1
    milk_df = pd.DataFrame(milk_rows)
    milk_df["collection_time_dt"] = pd.to_datetime(milk_df["collection_time"])

    # Cheese batches + transformations
    cheese_rows, trans_rows = [], []
    batch_counter = 1
    for d in range(n_days):
        day_time = start_date + dt.timedelta(days=d)
        eligible = milk_df[
            (milk_df["collection_time_dt"] >= (day_time - dt.timedelta(days=2))) &
            (milk_df["collection_time_dt"] < (day_time + dt.timedelta(days=1)))
        ]["milk_lot_id"].to_numpy()

        for _ in range(cheese_batches_per_day):
            prod_time = day_time + dt.timedelta(hours=14) + dt.timedelta(minutes=int(rng.integers(0, 6 * 60)))
            line = f"LINE-{int(rng.integers(1, line_count + 1))}"
            room = f"ROOM-{int(rng.integers(1, maturation_rooms + 1))}"
            batch_id = f"CB-{batch_counter:06d}"
            batch_counter += 1
            chosen = eligible if len(eligible) <= mixing_k else rng.choice(eligible, size=mixing_k, replace=False)
            for ml in chosen:
                trans_rows.append({
                    "event_type": "TransformationEvent",
                    "event_time": prod_time.isoformat(),
                    "input_milk_lot_id": ml,
                    "output_cheese_batch_id": batch_id,
                    "biz_step": "processing",
                    "line_id": line
                })
            cheese_rows.append({
                "cheese_batch_id": batch_id,
                "production_time": prod_time.isoformat(),
                "line_id": line,
                "maturation_room": room,
                "mixing_k": mixing_k
            })
    cheese_df = pd.DataFrame(cheese_rows)
    trans_df = pd.DataFrame(trans_rows)

    # Contamination + lab detections
    cheese_df["is_contaminated"] = (rng.random(len(cheese_df)) < contamination_rate)
    detect_rows = []
    for _, r in cheese_df[cheese_df["is_contaminated"]].iterrows():
        prod_time = pd.to_datetime(r["production_time"])
        delay = int(rng.integers(lab_delay_days_min, lab_delay_days_max + 1))
        detect_rows.append({
            "cheese_batch_id": r["cheese_batch_id"],
            "detect_time": (prod_time + dt.timedelta(days=delay)).isoformat(),
            "pathogen": "Listeria_monocytogenes",
            "result": "detected"
        })
    detect_df = pd.DataFrame(detect_rows)

    # Cases
    rng_cases = np.clip(rng.normal(avg_cases_per_batch, avg_cases_per_batch * 0.15, size=len(cheese_df)),
                        avg_cases_per_batch * 0.5, avg_cases_per_batch * 1.7).astype(int)
    batch_ids_rep = np.repeat(cheese_df["cheese_batch_id"].to_numpy(), rng_cases)
    case_ids = [f"CASE-{i:08d}" for i in range(1, len(batch_ids_rep) + 1)]
    prod_time_map = cheese_df.set_index("cheese_batch_id")["production_time"]
    pack_times = pd.to_datetime(prod_time_map.loc[batch_ids_rep].to_numpy()) + pd.to_timedelta(2, unit="D")
    cases_df = pd.DataFrame({
        "case_id": case_ids,
        "cheese_batch_id": batch_ids_rep,
        "pack_time": pack_times.astype(str),
        "units_in_case": case_size_units
    })

    # Ground truth affected cases
    contam_map = cheese_df.set_index("cheese_batch_id")["is_contaminated"]
    cases_df["is_affected_true"] = cases_df["cheese_batch_id"].map(contam_map).fillna(False).astype(bool)

    # Recall results
    cheese_df_dt = cheese_df.copy()
    cheese_df_dt["production_time_dt"] = pd.to_datetime(cheese_df_dt["production_time"])
    cheese_by_id = cheese_df_dt.set_index("cheese_batch_id")

    results = []
    for _, det in detect_df.iterrows():
        bid = det["cheese_batch_id"]
        line = cheese_by_id.loc[bid, "line_id"]
        prod_time = cheese_by_id.loc[bid, "production_time_dt"]

        proposed_recalled = int((cases_df["cheese_batch_id"] == bid).sum())

        W = dt.timedelta(hours=w_hours_baseline)
        w_start, w_end = prod_time - W, prod_time + W
        baseline_batches = cheese_df_dt[
            (cheese_df_dt["line_id"] == line) &
            (cheese_df_dt["production_time_dt"] >= w_start) &
            (cheese_df_dt["production_time_dt"] <= w_end)
        ]["cheese_batch_id"].to_numpy()
        baseline_recalled = int(cases_df["cheese_batch_id"].isin(baseline_batches).sum())

        true_affected = int(((cases_df["cheese_batch_id"] == bid) & (cases_df["is_affected_true"])).sum())
        prec_p = true_affected / proposed_recalled if proposed_recalled else 1.0
        prec_b = true_affected / baseline_recalled if baseline_recalled else 1.0
        sr = (baseline_recalled - proposed_recalled) / baseline_recalled * 100 if baseline_recalled else 0.0

        results.append({
            "detected_batch": bid,
            "detect_time": det["detect_time"],
            "line_id": line,
            "baseline_W_hours": w_hours_baseline,
            "true_affected_cases": true_affected,
            "baseline_recalled_cases": baseline_recalled,
            "proposed_recalled_cases": proposed_recalled,
            "scope_reduction_percent": float(sr),
            "baseline_precision": float(prec_b),
            "baseline_recall": 1.0,
            "proposed_precision": float(prec_p),
            "proposed_recall": 1.0,
        })
    recall_results = pd.DataFrame(results).sort_values("scope_reduction_percent", ascending=False)

    return {
        "farms": pd.DataFrame({"farm_id": farms}),
        "milk_lots": milk_df.drop(columns=["collection_time_dt"]),
        "cheese_batches": cheese_df,
        "transformations": trans_df,
        "cases": cases_df,
        "lab_detections": detect_df,
        "recall_results": recall_results
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n_days", type=int, default=14)
    ap.add_argument("--n_farms", type=int, default=15)
    ap.add_argument("--milk_lots_per_day", type=int, default=40)
    ap.add_argument("--cheese_batches_per_day", type=int, default=15)
    ap.add_argument("--mixing_k", type=int, default=4)
    ap.add_argument("--contamination_rate", type=float, default=0.03)
    ap.add_argument("--delay_min", type=int, default=7)
    ap.add_argument("--delay_max", type=int, default=14)
    ap.add_argument("--W", type=int, default=24)
    ap.add_argument("--outdir", type=str, default="outputs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    data = generate_dataset_fast(
        seed=args.seed,
        n_days=args.n_days,
        n_farms=args.n_farms,
        milk_lots_per_day=args.milk_lots_per_day,
        cheese_batches_per_day=args.cheese_batches_per_day,
        mixing_k=args.mixing_k,
        contamination_rate=args.contamination_rate,
        lab_delay_days_min=args.delay_min,
        lab_delay_days_max=args.delay_max,
        w_hours_baseline=args.W,
    )

    for name, df in data.items():
        df.to_csv(os.path.join(args.outdir, f"{name}.csv"), index=False)

    rr = data["recall_results"]
    if len(rr) == 0:
        print("No detections in this run (increase contamination_rate).")
    else:
        print(rr.describe(include="all"))

if __name__ == "__main__":
    main()
