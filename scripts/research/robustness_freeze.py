#!/usr/bin/env python3
"""Write the frozen run tables of the solver-robustness campaign.

Stages: smoke (historical instances, infrastructure only), pilot (Base only on
the calibration set), primary, multiseed and i077 (instance077 audit). Runs of
one instance group are executed consecutively in a seeded random policy order.
"""
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results-revision/solver-robustness"
POLICIES = ["Base", "Flat-GM", "Flat-L2", "Role-Hybrid"]
SOLVERS = ["gurobi", "cplex", "highs"]
GAPS = ["0.01", "0.001"]
KEY = {"Simple": "simple", "SG-Ter-Mer": "sgtm", "Full": "completo"}
PER_SHARD = {"Simple": 10, "SG-Ter-Mer": 10, "Full": 2}
FIELDS = ["run_id", "stage", "shard", "order", "family", "instance", "instance_path", "instance_sha256",
          "policy", "solver", "gap", "seed", "cap_s", "threads"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy_order(*parts):
    rng = random.Random(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest())
    order = POLICIES[:]
    rng.shuffle(order)
    return order


def emit(rows, stage, solver, groups, caps, threads=1):
    """groups: list of (shard_key, [(family, instance, path)], gap, seed, policies)."""
    shard_ids = {}
    order = 0
    for shard_key, items, gap, seed, policies in groups:
        shard = shard_ids.setdefault(shard_key, len(shard_ids))
        for fam, inst, path in items:
            digest = sha(ROOT / path)
            pols = policy_order(digest, solver, gap, seed) if policies is None else policies
            for pol in pols:
                rows.append({"run_id": f"{stage}-{solver}-{KEY.get(fam, fam)}-{inst}-{pol}-g{gap}-s{seed}"
                                       + ("" if threads == 1 else f"-t{threads}"),
                             "stage": stage, "shard": shard, "order": order, "family": fam,
                             "instance": inst, "instance_path": path, "instance_sha256": digest,
                             "policy": pol, "solver": solver, "gap": gap, "seed": seed,
                             "cap_s": caps[fam], "threads": threads})
                order += 1


def chunks(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True, choices=["smoke", "pilot", "primary", "multiseed", "i077"])
    ap.add_argument("--split", type=Path, default=BASE / "design/instance-split.csv")
    ap.add_argument("--caps", default="Simple=1800,SG-Ter-Mer=1800,Full=3600")
    ap.add_argument("--decision", type=Path, default=None,
                    help="calibration-decision.json: caps and the HiGHS scope of rule R2")
    ap.add_argument("--primary-seed", type=int, default=1)
    ap.add_argument("--extra-seeds", default="2,3,4,5")
    ap.add_argument("--out", type=Path, default=BASE / "runs")
    args = ap.parse_args()
    caps = {k: float(v) for k, v in (x.split("=") for x in args.caps.split(","))}
    restricted = set()
    if args.decision:
        decision = json.loads(args.decision.read_text())["decision"]
        caps = {fam: float(d["cap_s"]) for fam, d in decision.items()}
        restricted = {fam for fam, d in decision.items() if d["highs_scope"] != "full evaluation set"}
    split = list(csv.DictReader(args.split.open()))
    inst = lambda fam, role=None, ms=None: [
        (fam, r["instance"], f"data/benchmark-v1/{KEY[fam]}/{r['instance']}.txt") for r in split
        if r["family"] == fam and (role is None or r["role"] == role)
        and (ms is None or r["multiseed"] == ms)]
    tables = {}
    if args.stage == "smoke":
        hist = [("Simple", "caso01a", "data/entradas/entrada-modelo-simple/caso01a.txt"),
                ("SG-Ter-Mer", "instance001", "data/entradas/entrada-SG-Ter-Mer/instance001.txt"),
                ("Full", "instance001", "data/entradas/entrada-modelo-completo/instance001.txt")]
        smoke_caps = {"Simple": 300.0, "SG-Ter-Mer": 300.0, "Full": 300.0}
        for solver in SOLVERS:
            rows = []
            groups = [(0, [hist[0]], "0.01", args.primary_seed, POLICIES),
                      (0, hist[1:], "0.01", args.primary_seed, ["Base"])]
            emit(rows, "smoke", solver, groups, smoke_caps)
            tables[f"smoke-{solver}"] = rows
    elif args.stage == "pilot":
        pilot_caps = {k: 7200.0 for k in caps}
        for solver in ["cplex", "highs"]:
            rows, groups = [], []
            for fam in KEY:
                for item in inst(fam, "calibration"):
                    for gap in GAPS:
                        groups.append(((fam, item[1]), [item], gap, args.primary_seed, ["Base"]))
            emit(rows, "pilot", solver, groups, pilot_caps)
            tables[f"pilot-{solver}"] = rows
    elif args.stage in ("primary", "multiseed"):
        seeds = [args.primary_seed] if args.stage == "primary" else [int(s) for s in args.extra_seeds.split(",")]
        for solver in SOLVERS:
            rows, groups = [], []
            for fam in KEY:
                pool = inst(fam, "evaluation") if args.stage == "primary" else inst(fam, "evaluation", "True")
                if solver == "highs" and fam in restricted:
                    # Rule R2: HiGHS keeps only the replication subset where it barely completes.
                    pool = inst(fam, "evaluation", "True")
                for seed in seeds:
                    for gap in GAPS:
                        for block in chunks(pool, PER_SHARD[fam]):
                            groups.append(((fam, gap, seed, block[0][1]), block, gap, seed, None))
            emit(rows, args.stage, solver, groups, caps)
            tables[f"{args.stage}-{solver}"] = rows
    else:
        versions = [("SG-Ter-Mer", "instance077", "data/entradas/entrada-SG-Ter-Mer/instance077.txt"),
                    ("SG-Ter-Mer", "instance077c", "data/benchmark-v1/instance077-corrected/instance077.txt")]
        seeds = [args.primary_seed] + [int(s) for s in args.extra_seeds.split(",")]
        for solver in SOLVERS:
            rows, groups = [], []
            for item in versions:
                for seed in seeds:
                    for gap in GAPS:
                        groups.append(((item[1], gap, seed), [item], gap, seed, None))
            emit(rows, "i077", solver, groups, caps)
            tables[f"i077-{solver}"] = rows
        # Historical condition of the reported timeout: Gurobi, 16 threads, seed 42.
        rows = []
        emit(rows, "i077hist", "gurobi", [((gap,), versions[:1], gap, 42, None) for gap in GAPS],
             caps, threads=16)
        tables["i077hist-gurobi"] = rows
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, rows in tables.items():
        path = args.out / f"{name}.csv"
        if path.exists():
            raise SystemExit(f"{path} exists; run tables are frozen")
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        shards = {}
        for r in rows:
            shards.setdefault(r["shard"], 0.0)
            shards[r["shard"]] += float(r["cap_s"])
        summary[name] = {"runs": len(rows), "shards": len(shards),
                         "max_shard_cap_s": max(shards.values()), "sha256": sha(path)}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
