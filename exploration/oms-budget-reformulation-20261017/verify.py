"""Replay every rational bound derivation and activation contraction; no optimizer."""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F = Fraction.from_float


def initial(model, variable, side):
    b = model["variables"][variable][("lower", "upper")[side]]
    assert b is not None
    return F(float(b))


def bound_value(model, proofs, variable, side, reference, before):
    if reference is None:
        return initial(model, variable, side)
    assert isinstance(reference, int) and 0 <= reference < before
    proof = proofs[reference]
    assert (proof["variable"], proof["side"]) == (variable, side)
    return Fraction(proof["value"])


def ceil_log2(q):
    k = q.numerator.bit_length() - q.denominator.bit_length()
    while Fraction(2) ** k < q:
        k += 1
    return k


def incompatible_rows(model):
    incompatible = []
    for i, row in enumerate(model["rows"]):
        E = F(1e-9) * sum((abs(F(float(a))) for j, a in row["terms"].items()
                           if model["variables"][int(j)]["integer"]), Fraction(0))
        remainder = F(float(row["budget"])) - E
        if remainder <= 0:
            incompatible.append(i)
            continue
        coefficients = [abs(F(float(a))) for a in row["terms"].values()]
        low = max(F(1e-6) / remainder, F(1e-9) / min(coefficients))
        high = F(1e9) / max(coefficients)
        k = max(-1074, ceil_log2(low))
        passed = False
        while k <= 1023 and Fraction(2) ** k <= high:
            try:
                values = [math.ldexp(float(a), k) for a in [*row["terms"].values(), row["rhs"]]]
                passed = all(math.isfinite(v) and F(v) == F(float(a)) * Fraction(2) ** k
                             for a, v in zip([*row["terms"].values(), row["rhs"]], values))
            except OverflowError:
                passed = False
            if passed:
                break
            k += 1
        if not passed:
            incompatible.append(i)
    return incompatible


def main():
    counts = []
    for folder in sorted((HERE / "diagnostic").iterdir()):
        if not folder.is_dir():
            continue
        record = json.loads((folder / "certificate.json").read_text())
        source = ROOT / record["source"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == record["source_sha256"]
        model = json.loads(source.read_text())
        proofs = record["bound_derivations"]
        for i, proof in enumerate(proofs):
            row = model["rows"][proof["row"]]
            sign = proof["row_sign"]
            assert sign in (1, -1)
            assert row["sense"] == "=" or sign == (1 if row["sense"] == "<" else -1)
            j = proof["variable"]
            terms = {int(k): sign * F(float(a)) for k, a in row["terms"].items()}
            a = terms[j]
            assert proof["side"] == (1 if a > 0 else 0)
            support = {k: (side, ref) for k, side, ref in proof["support"]}
            assert set(support) == set(terms) - {j}
            total = Fraction(0)
            for k in support:
                side, ref = support[k]
                assert side == (0 if terms[k] > 0 else 1)
                total += terms[k] * bound_value(model, proofs, k, side, ref, i)
            assert Fraction(proof["value"]) == (sign * F(float(row["rhs"])) - total) / a
        for contraction in record["contractions"]:
            row = model["rows"][contraction["row"]]
            j = contraction["binary"]
            variable = model["variables"][j]
            assert variable["integer"] and (variable["lower"], variable["upper"]) == (0., 1.)
            sign = 1 if row["sense"] == "<" else -1
            assert sign == contraction["sense_sign"] and row["rhs"] == 0
            terms = {int(k): sign * F(float(a)) for k, a in row["terms"].items()}
            assert terms[j] == -Fraction(contraction["original_M"])
            del terms[j]
            assert all(not model["variables"][k]["integer"] for k in terms)
            used = {k: (side, ref) for k, side, ref in contraction["support"]}
            assert set(used) == set(terms)
            total = Fraction(0)
            for k, a in terms.items():
                side, ref = used[k]
                assert side == (1 if a > 0 else 0)
                total += a * bound_value(model, proofs, k, side, ref, len(proofs))
            assert total == Fraction(contraction["certified_global_upper"])
            assert max(Fraction(0), total) <= F(contraction["new_M"]) < Fraction(contraction["original_M"])
            row["terms"][str(j)] = -sign * contraction["new_M"]
            if not contraction["new_M"]:
                del row["terms"][str(j)]
        supplied = json.loads((folder / "reformulated-model.json").read_text())
        assert supplied == model
        assert incompatible_rows(model) == [r["row"] for r in record["incompatible_after"]]
        original = json.loads(source.read_text())
        assert incompatible_rows(original) == [r["row"] for r in record["incompatible_before"]]
        counts.append({"instance": folder.name, "exact_bound_derivations": len(proofs),
                       "equivalent_binary_contractions": len(record["contractions"]),
                       "remaining_incompatible_rows": len(record["incompatible_after"])})
    result = {"models": len(counts), "checks": counts, "new_optimizer_calls": 0,
              "propagation_runner_imported": False, "restored_complete_rounded_contracts": 0}
    (HERE / "VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
