"""Exact finite checks before native solves; no optimizer import."""
from fractions import Fraction
import json
from pathlib import Path

import method

F=Fraction.from_float
HERE=Path(__file__).resolve().parent


def main():
    count=0;amplification=0
    # Exhaustive k/sigma/alpha search on a small finite window, independent of selector.
    for M in (2.**8,2.**16):
        rows=[{'row':0,'z':0,'M':M,'terms':{'0':-M,'1':1.}}]
        delta=1e-4;got=method.select(rows,delta)
        brute=None
        for t in range(31):
            lo=max(F(1e-9),Fraction(2)**(-t));hi=min(F(1e9),Fraction(2)**t)
            for k in range(29):
                K=2**k
                sigmas=[Fraction(2)**r for r in range(-40,41) if lo<=Fraction(2)**r and Fraction(2)**r*K<=hi]
                if not sigmas:continue
                sigma=max(sigmas)
                if K*F(1e-9)+F(1e-6)/sigma+F(1e-9)>=Fraction(1,2):continue
                effective=(F(1e-9)+F(1e-6)/sigma)/K
                alphas=[Fraction(2)**u for u in range(-50,51) if lo<=Fraction(2)**u and Fraction(2)**u*F(M)<=hi
                        and F(1e-6)/(Fraction(2)**u)+F(M)*effective<=F(delta)]
                if alphas:brute=(t,k,float(sigma));break
            if brute:break
        assert got['compatible'] and (got['t'],got['groups'][0]['k'],got['groups'][0]['sigma'])==brute
        count+=1
    for k in range(29):
        K=Fraction(2)**k
        for r in (-10,0,10,20):
            sigma=Fraction(2)**r;eta=F(1e-6)/sigma
            if K*F(1e-9)+eta+F(1e-9)>=Fraction(1,2):continue
            for nearest in (0,1):
                for direction in (-1,1):
                    error=direction*min(F(1e-9),(F(1e-9)+eta)/K)
                    z=nearest+error
                    q=K*z-direction*min(eta,abs(K*error))
                    assert abs(z-round(z))<=F(1e-9)
                    assert abs(q-round(q))<=F(1e-9)
                    assert abs(sigma*(K*z-q))<=F(1e-6)
                    assert round(q)==K*round(z)
                    assert abs(z-round(z))<=(F(1e-9)+eta)/K
                    amplification+=1
    for z in (0,1):
        for k in range(29):
            q=2**k*z
            assert q==round(q) and q-2**k*z==0 and 0<=q<=2**k
    result={'independently_enumerated_selector_cases':count,'exact_amplification_checks':amplification,
            'projection_checks':58,'optimizer_calls':0}
    (HERE/'STATIC_TESTS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
