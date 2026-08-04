#!/usr/bin/env python3
"""Numerical check of the stylized attribution-slope model (spectral audit).

Confirms the closed form behind the "why the advantage grows by an order of
magnitude per unit of range" paragraph: for B blocks at exponents e_i spread over
[-R,R] with one coupling row whose incidence inherits the block scale, the
role-blind (Flat-Mat) pseudo-condition number is ~10^R while the block-relative
(SA-Mat) one is sqrt(1+B), independent of R -- so the ratio is sqrt(1+B)*10^-R.

    python3 scripts/stylized_model_check.py
"""
import numpy as np


def kappa2(A):
    s = np.linalg.svd(A, compute_uv=False)
    s = s[s > s.max() * 1e-14]
    return s.max() / s.min()


def main():
    B = 4
    print(f'{"R":>3} {"FlatMat k2":>12} {"SAMat k2":>10} {"ratio":>12} '
          f'{"sqrt(1+B)*10^-R":>16}')
    for R in (1, 2, 3):
        e = np.array([-R + 2 * R * i / (B - 1) for i in range(B)])
        Iloc = np.eye(B)
        v = 10.0 ** e                       # coupling coefficients inherit block scale
        vflat = v / np.sqrt(v.max() * v.min())          # Flat-Mat: per-row geometric mean
        vsa = v / (10.0 ** e)                           # SA-Mat: divide by block scale
        kf = kappa2(np.vstack([Iloc, vflat]))
        ks = kappa2(np.vstack([Iloc, vsa]))
        pred = np.sqrt(1 + B) * 10.0 ** (-R)
        print(f'{R:>3} {kf:>12.3g} {ks:>10.3g} {ks / kf:>12.4g} {pred:>16.4g}')
    print('\nFlat-Mat ~ 10^R, SA-Mat ~ sqrt(1+B) const, ratio ~ sqrt(1+B)*10^-R '
          '(one order of magnitude per unit R).')


if __name__ == '__main__':
    main()
