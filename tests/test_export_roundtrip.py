"""Integration check of the actual C++ LP exporter on lossy-format regressions."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_identifiability_grid import parse


def test_cpp_export_preserves_small_terms_rhs_and_bounds(tmp_path):
    obj=ROOT/'code/build-audit/SystemController/Problema'
    if not obj.exists():
        import pytest
        pytest.skip('build-audit required: make audit-build')
    exe=tmp_path/'export-test'
    subprocess.run(['g++','-std=c++17','-I'+str(ROOT/'code'),str(ROOT/'tests/export_roundtrip.cpp'),
                    str(obj/'Problema.o'),str(obj/'ProblemaLp/ProblemaLp.o'),
                    str(obj/'PreprocesamientoMIP/PreprocesamientoMIP.o'),'-o',str(exe)],check=True)
    text=subprocess.check_output([str(exe)],text=True)
    lp=tmp_path/'model.lp';lp.write_text(text)
    rows,other=parse(lp)
    assert float(rows['tiny']['terms']['x']) == 1e-300
    assert float(rows['tiny']['terms']['y']) == -1.2345678901234567
    assert float(rows['tiny']['rhs']) == 1e-20
    bound=next(line for line in other if '<= x <=' in line).split()
    assert float(bound[0]) == 2.345678901234567e-15
    assert float(bound[-1]) == 1.2345678901234567
    cost=next(line for line in other if line.endswith(' x') and '<=' not in line)
    assert float(cost.split()[0]) == 9.876543210987654e-100
