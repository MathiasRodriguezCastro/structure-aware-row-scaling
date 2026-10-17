"""Minimum dyadic continuous-column change under exact scaling constraints.

Difference constraints and shortest-path certificates are classical. This research
prototype changes the objective and adds original-coordinate bound budgets; no
historical priority or improvement in MILP running time is implied.
"""
from fractions import Fraction
import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "exploration/oms-joint-contracts-20261016/joint.py"
spec = importlib.util.spec_from_file_location("prior_exact_scaling_graph", SOURCE)
graphlib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graphlib)
F = Fraction.from_float


def construct(model, bound_budgets=None, epsilon_bound=1e-6):
    graph = graphlib.construct(model, t=40, columns=True)
    columns = {name: len(model["rows"]) + i + 1
               for i, name in enumerate(model["columns"])}
    for name, budget in (bound_budgets or {}).items():
        if name in model["integers"]:
            continue
        if not math.isfinite(float(budget)) or budget <= 0:
            raise ValueError("continuous bound budget must be positive and finite")
        cap = graphlib.floorlog(F(float(budget)) / F(epsilon_bound))
        # v_j=-w_j <= cap, hence p_anchor-p_column <= cap.
        graph.edge(columns[name], 0, cap, "original bound budget " + name)
    return graph


def radius_graph(base, model, radius):
    if not isinstance(radius, int) or radius < 0:
        raise ValueError("integer nonnegative radius required")
    graph = graphlib.Graph(base.labels)
    graph.edges = list(base.edges)
    for i, name in enumerate(model["columns"]):
        if name not in model["integers"]:
            graph.box(len(model["rows"]) + i + 1, -radius, radius,
                      "column change radius " + name)
    return graph


def select_rows(model, graph, potential):
    """Choose nearest admissible row-L2 factors with column potentials fixed."""
    nrows = len(model["rows"])
    limits = {i: [-1074, 1023] for i in range(1, nrows + 1)}
    for a, b, cap, _ in graph.edges:
        if 1 <= b <= nrows:
            assert not 1 <= a <= nrows
            limits[b][1] = min(limits[b][1], cap + potential[a])
        elif 1 <= a <= nrows:
            limits[a][0] = max(limits[a][0], potential[b] - cap)
    v = {name: -potential[nrows + i + 1]
         for i, name in enumerate(model["columns"])}
    result = list(potential)
    for i, (name, row) in enumerate(model["rows"].items(), 1):
        low, high = limits[i]
        assert low <= high
        norm2 = sum((F(float(a)) ** 2 * graphlib.power(2 * v[j])
                     for j, a in row["terms"].items()), Fraction(0))
        if not norm2:
            # A constant row's feasibility must be checked by the caller.
            raise ValueError("constant rows require separate feasibility treatment")
        middle = (-graphlib.floorlog(norm2)) // 2
        candidates = {min(high, max(low, k)) for k in range(middle - 1, middle + 2)}

        def distance(k):
            value = norm2 * graphlib.power(2 * k)
            return max(value, 1 / value), -k

        result[i] = min(candidates, key=distance)
    graph.check({"potential": result})
    u = {name: result[i] for i, name in enumerate(model["rows"], 1)}
    return u, v, result


def certificate(graph, result):
    return {"labels": graph.labels, "edges": graph.edges, "result": result}


def select(model, bound_budgets=None, epsilon_bound=1e-6):
    base = construct(model, bound_budgets, epsilon_bound)
    zero_graph = radius_graph(base, model, 0)
    zero = zero_graph.solve()
    if "potential" in zero:
        best, answer, high = zero_graph, zero, 0
    else:
        high = 1074
        best = radius_graph(base, model, high)
        answer = best.solve()
        if "negative_cycle" in answer:
            return {"compatible": False, "certificate": certificate(best, answer)}
        low = 0
        while high - low > 1:
            middle = (low + high) // 2
            graph = radius_graph(base, model, middle)
            result = graph.solve()
            if "potential" in result:
                high, best, answer = middle, graph, result
            else:
                low = middle
    u, v, potential = select_rows(model, best, answer["potential"])
    assert max((abs(x) for x in v.values()), default=0) == high
    below = None
    if high:
        previous = radius_graph(base, model, high - 1)
        obstruction = previous.solve()
        assert "negative_cycle" in obstruction
        below = certificate(previous, obstruction)
    return {"compatible": True, "radius": high, "u": u, "v": v,
            "feasible_certificate": certificate(best, {"potential": potential}),
            "lower_certificate": below}
