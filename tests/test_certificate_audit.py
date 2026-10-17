"""A missing historical source must never produce a falsely complete table."""
import importlib.util
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location('certificate_audit',Path(__file__).resolve().parents[1]/'scripts/research/certificate_audit.py')
audit=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(audit)


@pytest.mark.parametrize('missing',['contradictions.csv','runs.csv'])
def test_missing_campaign_input_fails_before_writing(tmp_path,monkeypatch,missing):
    cpath=tmp_path/'contradictions.csv';rpath=tmp_path/'runs.csv'
    for p in (cpath,rpath):
        if p.name!=missing:p.write_text('placeholder\n')
    table=tmp_path/'table.tex';detail=tmp_path/'detail.tex';report=tmp_path/'report.json'
    monkeypatch.setattr(audit,'SOURCES',[('stopped campaign',cpath,rpath)])
    monkeypatch.setattr('sys.argv',['certificate_audit.py','--out',str(table),'--detail',str(detail),'--json',str(report)])
    with pytest.raises(FileNotFoundError,match='required stopped campaign analysis input missing'):
        audit.main()
    assert not any(p.exists() for p in (table,detail,report))
