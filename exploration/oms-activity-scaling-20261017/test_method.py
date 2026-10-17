"""Small exhaustive selectors, projected equivalence, conditional sharp examples."""
from fractions import Fraction
import json
import math
from pathlib import Path

import method

F = Fraction.from_float
HERE = Path(__file__).resolve().parent


def main():
    checked = 0
    for terms in ([1.], [2.**-8], [2.**20], [1., -2.**10], [2.**-10, 2.**20]):
        for budget in (2.**-10, 2.**-24, 2.**-40):
            answer = method.select_activity(terms, 2.**30, budget)
            feasible = []
            # Direct rational enumeration: no selector endpoints or logarithms.
            for v in range(-40, 41):
                h = Fraction(2)**v
                ub = Fraction(2)**30 / h
                if ub > F(1e19):
                    continue
                candidates = []
                for u in range(-50, 51):
                    alpha = Fraction(2)**u
                    values = [abs(F(a)*alpha) for a in terms]+[h*alpha]
                    if min(values) < F(1e-9) or max(values) > F(1e9):
                        continue
                    if F(1e-6)/alpha+h*F(1e-6) > F(budget):
                        continue
                    norm2 = sum((x*x for x in values), Fraction(0))
                    candidates.append((max(norm2,1/norm2),-u,u))
                if candidates:
                    feasible.append((v,min(candidates)[2]))
            assert bool(answer) == bool(feasible)
            if answer:
                v, u = max(feasible, key=lambda pair:pair[0])
                assert answer['h'] == 2.**v and answer['alpha'] == 2.**u
                checked += 1
    projection = 0
    conditional = 0
    for M in (Fraction(1), Fraction(2)**20, Fraction(10)**17):
        for h in (Fraction(1,128), Fraction(1), Fraction(64)):
            for z in (0,1):
                for g in (-2*M,-M,Fraction(0),M/2,M,2*M):
                    y=max(Fraction(0),g/h);w=1-z
                    lifted=(g<=h*y and 0<=y<=M/h and (w==0 or y==0))
                    assert lifted == (g<=M*z)
                    projection += 1
            for alpha in (Fraction(1,32),Fraction(1),Fraction(512)):
                bound=F(1e-6)/alpha+h*max(F(1e-9),F(1e-6))
                # Extremal hypotheses for both values of the rounded binary.
                for rounded in (0,1):
                    z=Fraction(rounded);w=1-z
                    y=F(1e-9) if rounded==0 else M/h+F(1e-6)
                    g=h*y+F(1e-6)/alpha
                    assert abs(z-rounded)<=F(1e-9) and abs(w+z-1)<=F(1e-6)
                    assert min(abs(y),abs(w))<=F(1e-9)
                    assert y<=M/h+F(1e-6)
                    assert max(Fraction(0),g-M*rounded)<=bound
                    conditional += 1
    result={'exhaustive_selector_cases':15,'feasible_selector_cases':checked,
            'projected_equivalence_checks':projection,'conditional_extremal_checks':conditional,
            'optimizer_calls':0}
    (HERE/'STATIC_TESTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
