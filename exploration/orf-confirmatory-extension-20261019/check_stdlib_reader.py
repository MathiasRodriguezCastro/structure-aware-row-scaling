#!/usr/bin/env python3
"""Cross-check the new LP reader and reject corrupt witnesses, with zero solver calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
from verify_reference_witnesses_stdlib import Q, read_model, check_point, digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    spec = importlib.util.spec_from_file_location('prior_reference_reader',
        ROOT / 'exploration/orf-confirmatory-20261018/check.py')
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    data = json.loads((HERE / 'MODEL_PREPARATION.json').read_text())['models']
    seen = set()
    records = []
    for name, metadata in data.items():
        key = metadata['family'], metadata['horizon']
        if key in seen:
            continue
        seen.add(key)
        base = HERE / 'models' / name / 'Base.lp'
        actual, old = read_model(base), prior.canonical(base)
        assert actual[0] == old[0] and actual[3] == old[3]
        assert actual[2] == {n:c for n,c in old[2].items() if c} and old[5] == 0
        assert set(actual[1]) == set(old[1])
        sentinels = []
        for variable, bounds in actual[1].items():
            for side, (literal, native) in enumerate(zip(bounds, old[1][variable])):
                if literal == native:
                    continue
                assert native is None and literal is not None
                assert literal <= -10**20 if side == 0 else literal >= 10**20
                sentinels.append(dict(variable=variable, side='lower' if side==0 else 'upper',
                    written_value=str(literal), prior_reader_value='infinite'))
        records.append(dict(instance=name, rows=len(actual[0]), variables=len(actual[1]),
            integers=len(actual[3]), literal_bounds_preserved_in_addition_to_native_reader=sentinels))
    assert len(records) == 12
    name = 'simple-v1_simple_000127-h024'
    model = read_model(HERE / 'models' / name / 'Base.lp')
    point = {n:Q(v) for n,v in json.loads((HERE/'references'/name/'exact-witness.json').read_text()).items()}
    check_point(model, point)
    rejected = []
    for kind in ['water_balance', 'bound', 'integrality']:
        bad = dict(point)
        if kind == 'water_balance':
            variable = next(n for n in bad if '_v1h(' in n)
            bad[variable] += 1
        elif kind == 'bound':
            variable = next(n for n,(lo,hi) in model[1].items() if hi is not None)
            bad[variable] = model[1][variable][1] + 1
        else:
            variable = next(iter(model[3]))
            bad[variable] += Q(1,2)
        try:
            check_point(model, bad)
        except AssertionError:
            rejected.append(kind)
        else:
            raise AssertionError('Corrupt point accepted: ' + kind)
    with tempfile.TemporaryDirectory() as temporary:
        invalid = Path(temporary) / 'invalid.lp'
        invalid.write_text('min\nobj:\n +1 x\ns.t.\nr:\n +1 x\n >= 0\nbounds\n nan <= x <= +inf\nend\n')
        try:
            read_model(invalid)
        except AssertionError:
            pass
        else:
            raise AssertionError('NaN bound accepted.')
    report = dict(status='passed', independent_model_reader_comparisons=records,
        original_exact_point_passed=True, corrupt_points_rejected=rejected,
        NaN_bound_rejected=True, optimizer_calls=0,
        third_party_packages_needed_by_new_verifier=0,
        verifier_sha256=digest(HERE/'verify_reference_witnesses_stdlib.py'),
        check_source_sha256=digest(Path(__file__).resolve()),
        bound_scope='Retain explicit finite written bounds, including native infinity sentinels.')
    (HERE/'STDLIB_READER_CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
    print('12 model-reader strata passed; three corrupt points and a NaN bound rejected.')


if __name__ == '__main__':
    import sys
    if sys.flags.optimize:
        raise RuntimeError('Run without -O for integrity checks.')
    if hasattr(sys,'set_int_max_str_digits'):
        sys.set_int_max_str_digits(0)
    main()
