#!/usr/bin/env python3
"""Audit the stylized model using complete-row transformations only.

The old version divided coupling coefficients by different block scales, which
changed the constraint. After exact local geometric-mean normalization all
post-local block centers equal one; SA-Mat equals the role-hybrid L2 control.
This exact-kernel check excludes production guards. All matrices have full column
rank; no numerical singular-value cutoff is used.
"""
import argparse
import csv
from pathlib import Path
import numpy as np


def kappa2(matrix):
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    return float(singular_values[0] / singular_values[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]
                        / 'results-revision/research-audit/stylized.csv')
    args = parser.parse_args()
    blocks, records = 4, []
    for exponent_range in (0, 1, 2, 3):
        vector = 10.0 ** np.linspace(-exponent_range, exponent_range, blocks)
        base = np.vstack([np.diag(vector), vector])
        rhs = np.concatenate([vector, [float(vector.sum())]])
        local_factors = 1.0 / vector
        local_matrix = local_factors[:, None] * base[:blocks]
        post_scales = np.abs(np.diag(local_matrix))
        np.testing.assert_allclose(post_scales, 1.0, rtol=1e-14)
        gamma_gm = 1.0 / np.sqrt(vector.max() * vector.min())
        gamma_sa = 1.0 / np.linalg.norm(vector / post_scales)
        gamma_l2 = 1.0 / np.linalg.norm(vector)
        for variant, gamma in [('Flat-GM', gamma_gm), ('SA-Mat-post', gamma_sa),
                               ('Role-Hybrid', gamma_l2), ('Flat-L2', gamma_l2)]:
            factors = np.concatenate([local_factors, [gamma]])
            scaled, scaled_rhs = factors[:, None] * base, factors * rhs
            recovered = np.column_stack([scaled, scaled_rhs]) / factors[:, None]
            np.testing.assert_allclose(recovered, np.column_stack([base, rhs]), rtol=1e-14)
            predicted = np.sqrt(1.0 + gamma * gamma * np.dot(vector, vector))
            observed = kappa2(scaled)
            np.testing.assert_allclose(observed, predicted, rtol=1e-11)
            if variant != 'Flat-GM':
                np.testing.assert_allclose(observed, np.sqrt(2.0), rtol=1e-12)
            records.append(dict(blocks=blocks, exponent_range=exponent_range,
                                variant=variant, coupling_factor=gamma,
                                post_local_scale_min=float(post_scales.min()),
                                post_local_scale_max=float(post_scales.max()),
                                kappa2=observed, predicted_kappa2=float(predicted),
                                row_scaling_verified=1,
                                coupling_coefficient_ratio=float(vector.max()/vector.min())))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print('Complete-row equivalence and closed-form spectra verified (16 matrices).')
    for record in records:
        print(f"R={record['exponent_range']} {record['variant']:14s} "
              f"kappa2={record['kappa2']:.7g} gamma={record['coupling_factor']:.7g}")
    print(f'CSV: {args.output}')


if __name__ == '__main__':
    main()
