#!/usr/bin/env python3
"""Prepare an ORF delivery with the unchanged, audited scientific archive."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import unicodedata
import zipfile
from orf_config import ROOT, PAPER, ORF, OUT, VERSION, DATE, TITLE, PARENT, PARENT_DIR, FOLLOWUP, FOLLOWUP_ARCHIVE, VERIFIED, VERIFIED_ARCHIVE, sha
from orf_config import CONFIRMATION, CONFIRMATION_ARCHIVE, CONFIRMATION_ARCHIVE_PATH, COMPARATIVE_MIP_CALLS
from orf_config import CONFIRMATION_SUPPORT_ARCHIVE

FILES = ('main_orf.pdf','orf-editable-sources.zip','cover-letter.pdf','title-page.pdf','ESM_1.pdf','ESM_2.zip')
EXTRAS = ('REPRODUCE.md','UPLOAD_INSTRUCTIONS.md','ONLINE_RESOURCE_CAPTIONS.txt',
          'FORM_FIELDS.json','REPRODUCTION-VALIDATION.json','SHA256SUMS')
SCIENCE = 'scientific-evidence-oms-v1.3.17.zip'


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def archive(path, entries):
    # A previous validated build may share storage with its immutable release.
    if path.exists() or path.is_symlink():path.unlink()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        hashes=[]
        for name, value in sorted(entries.items()):
            if isinstance(value,Path):
                z.write(value,name);digest=sha(value)
            else:
                value=value.encode() if isinstance(value,str) else value
                z.writestr(name,value);digest=hashlib.sha256(value).hexdigest()
            hashes.append(f'{digest}  {name}\n')
        z.writestr('CONTENTS.sha256',''.join(hashes))


def plain(text):
    text=text.replace(r'\,',' ').replace(r'\textsuperscript{3}','³').replace('$10^{-9}$','10⁻⁹').replace(r'\%','%')
    text=re.sub(r"\\'\{?([A-Za-z])\}?",lambda m:unicodedata.normalize('NFC',m[1]+'\u0301'),text)
    for name in ('path','url','texttt','emph'):
        text=re.sub(r'\\'+name+r'\{([^{}]*)\}',r'\1',text)
    text=re.sub(r'\\doi\{([^{}]*)\}',r'https://doi.org/\1',text)
    text=text.replace(r'\_','_').replace('~',' ')
    assert '\\' not in text,text
    return ' '.join(text.split())


def build_delivery(validation=None):
    uploads=OUT/'uploads'
    write_json(uploads/'REPRODUCTION-VALIDATION.json',{
        'snapshot_version':VERSION,'status':'passed' if validation else 'not_yet_validated',
        'validation':validation})
    names=FILES+EXTRAS
    (uploads/'SHA256SUMS').write_text(''.join(f'{sha(uploads/n)}  {n}\n' for n in names if n!='SHA256SUMS'))
    delivery=OUT/'orf-delivery.zip'
    if delivery.exists() or delivery.is_symlink():delivery.unlink()
    with zipfile.ZipFile(delivery,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in names:z.write(uploads/name,name)
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(uploads/n)}  uploads/{n}\n' for n in FILES)+
        f'{sha(OUT/"orf-delivery.zip")}  orf-delivery.zip\n')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    parent_archive=PARENT_DIR/'reproducibility-artifact.zip'
    parent_validation=json.loads((PARENT_DIR/'VALIDATION.json').read_text())
    assert parent_validation['snapshot_version']==PARENT
    assert sha(parent_archive)==parent_validation['archives']['reproducibility-artifact.zip']['sha256']
    with zipfile.ZipFile(parent_archive) as z:
        for name in ('paper/main.tex','paper/supporting-information.tex'):
            assert z.read(name)==(ROOT/name).read_bytes(),'Scientific source drift: '+name
    entries={}
    for name in ('main_orf.tex','main_orf.bbl','main_orf.pdf','ESM_1.tex','ESM_1.pdf',
                 'cover-letter.tex','cover-letter.pdf','sn-jnl.cls','sn-basic.bst',
                 'title-page.tex','title-page.pdf',
                 'research-references.bib','TEMPLATE_PROVENANCE.md','Makefile'):
        entries[name]=ORF/name
    for folder in ('sections','tables','figs/research'):
        for p in (ORF/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.tex','.pdf'):entries[p.relative_to(ORF).as_posix()]=p
    entries['README.md']='Current ORF editable sources. Run make in this directory with pdfLaTeX and BibTeX.\n'
    source_zip=OUT/'orf-editable-sources.zip';archive(source_zip,entries)
    followup_validation=json.loads((FOLLOWUP/'VALIDATION.json').read_text())
    assert followup_validation['status']=='passed' and followup_validation['MIP_calls']==360
    logging_validation=json.loads((FOLLOWUP/'logging-confirmation/VALIDATION.json').read_text())
    assert logging_validation['status']=='passed' and logging_validation['MIP_calls']==360
    assert logging_validation['complete_native_logs']==360
    cluster_validation=json.loads((FOLLOWUP/'CLUSTER_VALIDATION.json').read_text())
    assert cluster_validation['status']=='passed'
    assert cluster_validation['analysis_sha256']==sha(FOLLOWUP/'CLUSTER_ANALYSIS.json')
    parent_sensitivity=json.loads((FOLLOWUP/'PARENT_SENSITIVITY_VALIDATION.json').read_text())
    assert parent_sensitivity['status']=='passed'
    assert parent_sensitivity['analysis_sha256']==sha(FOLLOWUP/'PARENT_SENSITIVITY.json')
    followup_entries={p.relative_to(ROOT).as_posix():p for p in FOLLOWUP.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.zip')}
    followup_zip=OUT/FOLLOWUP_ARCHIVE;archive(followup_zip,followup_entries)
    verified_zip=VERIFIED/'research-evidence.zip'
    verified_validation=json.loads((VERIFIED/'PACKAGE_VALIDATION.json').read_text())
    assert verified_validation['status']=='passed' and verified_validation['clean_extraction']
    assert sha(verified_zip)==verified_validation['research_evidence_sha256']
    assert verified_validation['new_optimization_assignments']==630
    assert verified_validation['additional_technical_repetitions']==1
    assert all(r['passed'] for r in verified_validation['commands'])
    confirmation_validation=json.loads((CONFIRMATION/'CONFIRMATION_ARCHIVE_VALIDATION.json').read_text())
    assert confirmation_validation['status']=='passed' and confirmation_validation['full_stream_read_and_checksums']
    assert confirmation_validation['archive_sha256']==sha(CONFIRMATION_ARCHIVE_PATH)
    # Installation helpers omitted by the old raw-tar metadata filter are
    # restored separately; no sealed model, vector, log or result is rewritten.
    support_entries={p.relative_to(ROOT).as_posix():p for p in (CONFIRMATION/'cluster').iterdir()
        if p.is_file() and p.suffix in ('.py','.json','.slurm','.sh','.md','.txt','.sha256')}
    support_zip=OUT/CONFIRMATION_SUPPORT_ARCHIVE
    archive(support_zip,support_entries)
    # Canonical editorial inputs and build tools, distinct from the scientific archive.
    revision={}
    roots=['README.md','CITATION.cff','.zenodo.json','LICENSE','DATA_LICENSE.md','Makefile',
           'paper/Makefile','paper/README.md','paper/main.tex','paper/supporting-information.tex',
           'paper/research-references.bib','paper/orf/Makefile','paper/orf/README.md',
           'paper/orf/TEMPLATE_PROVENANCE.md','paper/orf/REVISION_NOTES.md','paper/orf/cover-letter.tex','paper/orf/title-page.tex','paper/orf/sn-jnl.cls','paper/orf/sn-basic.bst',
           'paper/submission/orf/README.md','paper/submission/orf/SUBMISSION_CHECKLIST.md',
           'scripts/research/orf_config.py','scripts/research/build_orf.py',
           'scripts/research/package_orf.py','scripts/research/validate_orf.py','scripts/research/freeze_orf.py',
           'scripts/research/orf_followup_tables.py','scripts/research/orf_confirmation_tables.py',
           'scripts/research/orf_confirmation_evidence.py',
           'scripts/research/orf_acceptance_sensitivity.py',
           'scripts/research/check_orf_acceptance_sensitivity.py',
           'scripts/research/orf_resource_inventory.py','scripts/research/audit_orf_release.py',
           'paper/submission/orf/PORTAL_FIELDS.md','paper/submission/orf/SUPPLEMENTARY_CAPTIONS.txt']
    for name in roots:revision[name]=ROOT/name
    sensitivity=ROOT/'exploration/orf-acceptance-sensitivity-20261022'
    sensitivity_validation=json.loads((sensitivity/'VALIDATION.json').read_text())
    assert sensitivity_validation['status']=='passed'
    assert sensitivity_validation['sensitivity_sha256']==sha(sensitivity/'SENSITIVITY.json')
    for name in ('PLAN.json','SENSITIVITY.json','VALIDATION.json','README.md'):
        p=sensitivity/name;revision[p.relative_to(ROOT).as_posix()]=p
    for folder in ('paper/orf/editorial','paper/sections','paper/tables','paper/figs/research'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.tex','.pdf','.bib'):revision[p.relative_to(ROOT).as_posix()]=p
    revision_zip=OUT/'orf-revision-sources.zip';archive(revision_zip,revision)
    snapshot={'version':VERSION,'date':DATE,'target':'Operations Research Forum','title':TITLE,
        'published':False,'submitted':False,'version_doi':None,'new_optimization_experiments':COMPARATIVE_MIP_CALLS,
        'comparative_MIP_count_scope':'1351 earlier comparative/logging calls plus 3840 final confirmation assignments; resource pilots, reference acquisition and excluded infrastructure attempts are separate.',
        'larger_confirmation_assignments':3840,'larger_confirmation_quality_evaluable':3816,
        'larger_confirmation_diagnostic':24,
        'prospective_primary_MIP_calls':360,'logging_confirmation_MIP_calls':360,
        'verified_followup_MIP_assignments':630,'verified_followup_technical_MIP_repetitions':1,
        'verified_followup_new_independent_scenarios':0,
        'verified_followup_archive_sha256':sha(verified_zip),
        'verified_followup_prior_validation_sha256':sha(VERIFIED/'PACKAGE_VALIDATION.json'),
        'confirmation_archive_sha256':sha(CONFIRMATION_ARCHIVE_PATH),
        'confirmation_archive_validation_sha256':sha(CONFIRMATION/'CONFIRMATION_ARCHIVE_VALIDATION.json'),
        'confirmation_support_archive_sha256':sha(support_zip),
        'confirmation_support_files':len(support_entries),
        'confirmation_analysis_sha256':sha(CONFIRMATION/'CONFIRMATION_ANALYSIS.json'),
        'confirmation_statistical_replay_sha256':sha(CONFIRMATION/'CONFIRMATION_ANALYSIS_REPLAY.json'),
        'acceptance_sensitivity_sha256':sha(sensitivity/'SENSITIVITY.json'),
        'acceptance_sensitivity_validation_sha256':sha(sensitivity/'VALIDATION.json'),
        'acceptance_sensitivity_is_post_hoc':True,'registered_acceptance_endpoint_unchanged':True,
        'earlier_prospective_exact_LP_attempts':96, 'confirmation_reference_exact_LP_attempts':181,'prospective_archive_sha256':sha(followup_zip),
        'prospective_validation_sha256':sha(FOLLOWUP/'VALIDATION.json'),
        'cluster_analysis_sha256':sha(FOLLOWUP/'CLUSTER_ANALYSIS.json'),
        'cluster_analysis_is_post_hoc':True,'cluster_resamples':100000,'scenario_clusters':24,
        'parent_deletion_analysis_sha256':sha(FOLLOWUP/'PARENT_SENSITIVITY.json'),
        'parent_deletion_is_post_hoc':True,'parent_deletions':6,
        'scientific_parent':PARENT,'scientific_archive_sha256':sha(parent_archive),
        'scientific_parent_validation_sha256':sha(PARENT_DIR/'VALIDATION.json'),
        'current_sources_sha256':sha(source_zip),'canonical_revision_sha256':sha(revision_zip),
        'scientific_source_unchanged':True,
        'editorial_changes':['accuracy workflow first','practical framing and implications',
            'Springer template and numbered bibliography','Online Resource names and reproduction instructions',
            'new cover letter and ORF declarations/portal preparation',
            'prospective 24-scenario validation, 360 primary MIP calls, 360 logging confirmations and rational references',
            'finite-export error bound, concise discussion, workflow figure and uncluttered author line',
            'main-text prospective outcome table, candidate-cost qualification and post hoc scenario-cluster uncertainty',
            'selective verified-candidate summary and constructive export-aware selector; controls in Online Resource 1',
            'prospective-first abstract, explicit exact-domain counts, six-parent deletion sensitivity and concise cover letter',
            'larger fixed-policy confirmation: full primary comparison and adverse outcomes; all controls and strata retained',
            'concise conclusions updated to the complete evidence; inherited limitations retained with explicit extension',
            'dedicated larger-confirmation subsection, horizon results and post hoc exact-domain sensitivity; registered endpoint unchanged',
            'prospective table split into readable precision/performance panels; redundant editorial caveats condensed',
            'v1.7.1 packaging repair restores cluster Python helpers and wheel lock without modifying the sealed raw evidence'],
        'journal_instructions':'https://link.springer.com/journal/43069/submission-guidelines'}
    write_json(OUT/'SNAPSHOT.json',snapshot)
    captions=(ORF.parent/'submission/orf/SUPPLEMENTARY_CAPTIONS.txt').read_text()
    guide=f'''# {TITLE}

Journal: Operations Research Forum
Author: Mathias Rodríguez Castro
Affiliation: Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay
Correspondence: mathiasr@fing.edu.uy
ORCID: https://orcid.org/0009-0002-7235-7677
Local snapshot: {VERSION}; {DATE}. No new Zenodo DOI has been assigned.

ESM_1.pdf is Online Resource 1. ESM_2.zip is the complete Online Resource 2.
The latter contains the exact {PARENT} scientific-evidence ZIP and its validation
record, current editable ORF sources, canonical editorial sources and SNAPSHOT.json.
Historical OMS filenames identify provenance. The current article, letter and
resource captions are addressed to ORF. A separately identified prospective study
adds 24 new within-family scenarios, 360 primary MIP calls, a registered 360-call
logging confirmation and 96 exact LP attempts. The first campaign is retained
with its suppressed native traces; the confirmation supplies complete logs.
A further frozen follow-up supplies 630 MIP assignments and one technical
repeat, with new seeds on those same 24 known scenarios. It contains candidate
traces, physical-margin tests, CPLEX/ScaleFlag controls and export-aware selection.
It supplies no new independent scenarios. These earlier ORF studies account
for 1,351 comparative MIP calls, including both kinds of technical repetition.
The larger frozen confirmation adds 3,840 assignments on 160 generated models
from 40 known historical-component parents: 3,816 are quality-eligible and 24
remain diagnostic. Its 256-call resource pilot, Base-only calibration, reference
acquisition/recovery and excluded infrastructure attempts are accounted for
separately; they do not enlarge the confirmatory comparison. The lossless
{CONFIRMATION_ARCHIVE} supplies the final campaign, pilot and reference raw data,
frozen sources, native logs, vectors, whole-parent analysis and independent replay.
Its validated stream preserves repeated contents as ordinary tar hard links.
The small {CONFIRMATION_SUPPORT_ARCHIVE} restores cluster installation helpers
and the wheel lock omitted by the v1.7.0 metadata filter. Extract it over the same
scientific root as the raw tar. It includes no solver binaries and changes no
scientific input or result. The wheel lock matches the recorded installation.

## Reproduce the evidence

Extract ESM_2.zip and check its CONTENTS.sha256. Then extract {SCIENCE} into an
empty directory and enter that extracted scientific repository:

```sh
sha256sum --quiet -c CONTENTS.sha256
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r environment/research-requirements.txt
make research-oms-check
make research-check-python
make research-check
make research-analysis
```

Install the system prerequisites listed in environment/apt-packages.txt; the
native export check needs GNU Make and a C++17 compiler. These commands verify
saved results without rerunning research MILPs or requiring a commercial solver
license. Mathematical tests include small SciPy reference LPs. The controls cover
90 new saved calls and 36 reused Budget-L2 points, exact witnesses, original-unit
residuals, paired work and complete-process time. Analysis regenerates 42 tables
and three figures. The scientific archive's paper build preserves its historical
OMS presentation; compile the ORF source bundle for the current documents.

## Replay the prospective study

Extract {FOLLOWUP_ARCHIVE} over the extracted scientific repository, preserving
its exploration/ path. Its CONTENTS.sha256 lists the additional files. From that
repository root run:

```sh
python3 exploration/orf-confirmatory-20261018/check.py
python3 exploration/orf-confirmatory-20261018/check.py --logging-confirmation
python3 exploration/orf-confirmatory-20261018/check_export_bound.py
python3 exploration/orf-confirmatory-20261018/check_cluster_analysis.py
python3 exploration/orf-confirmatory-20261018/parent_sensitivity.py --check
```

These commands check both sets of 360 saved MIP outcomes, complete confirmation
logs, endpoint/point replication, factor interventions, rational
reference certificates and the elementary finite-export bound without commercial
solver calls. The fixed protocol retains known parent data, new scenario
perturbations and three horizon sizes. This is prospective within-family evidence;
it is not a new independent application. The 96 rational LP acquisition attempts
are separately costed and do not certify every returned floating-point candidate.

## Replay the verified-candidate and export-selector follow-up

Extract {VERIFIED_ARCHIVE} over that same repository root and verify
`sha256sum --quiet -c FOLLOWUP_CONTENTS.sha256` before running these commands:

```sh
python3 exploration/orf-v15-verified-20261019/check.py
python3 exploration/orf-v15-verified-20261019/check_selector.py
python3 exploration/orf-v15-verified-20261019/precision.py
python3 exploration/orf-v15-verified-20261019/analyze.py
python3 exploration/orf-v15-verified-20261019/check_statistics.py
python3 exploration/orf-v15-verified-20261019/projection_sensitivity.py
```

These six license-free saved-result replays retain target misses, tiny bound
violations, the failed pre-optimizer worker and the identified technical repeat.
They check all 630 assignments, 6,725 primary candidate events, the exact finite
export/rounding reserves and 44 scenario-cluster intervals. The ZIP is inherited
byte-for-byte from its clean-extraction research audit, whose record is supplied
as VERIFIED_PACKAGE_VALIDATION.json. That record refers to the pre-integration
v1.4.2 manuscript; the current SNAPSHOT.json and validation identify this version.
The research note's original decision to keep the study separate is historical;
the current ORF sources incorporate the selected findings only. Neither saved
replay nor a paper rebuild reruns commercial optimization or recreates timings.

## Replay the larger fixed-policy confirmation

Extract {CONFIRMATION_ARCHIVE} over the same scientific repository with GNU tar
(`tar -xJf path/to/{CONFIRMATION_ARCHIVE}`). Keep hard links when extracting:
they preserve identical content at its original paths and reduce disk usage.
CONFIRMATION_ARCHIVE_CONTENTS.json lists every path, size and SHA-256. Over
the same repository root, extract {CONFIRMATION_SUPPORT_ARCHIVE} and check its
CONTENTS.sha256 too. This overlay supplies the cluster Python helpers and wheel
lock omitted by the old metadata filter. The wheel filenames and hashes match
DEPENDENCY_INSTALLATION.json. The full audit checks all 3,840 job bundles and
every cluster Python helper referenced by the supplied launch scripts. Then run:

```sh
python3 exploration/orf-confirmatory-extension-20261019/seal_confirmation.py --check
python3 exploration/orf-confirmatory-extension-20261019/seal_pending_validation.py --check
python3 exploration/orf-confirmatory-extension-20261019/seal_reference_recovery.py --check
python3 exploration/orf-confirmatory-extension-20261019/verify_confirmation_analysis.py
```

The independent statistical replay checks all 48 comparisons and 80 marginal
whole-parent intervals against the 480 saved block reports, without commercial
optimizer calls. All 3,840 executions already passed their independent vector
audits; to rerun their full rational arithmetic, use replay_confirmation.py
with each block index 0 through 479. This is substantially more costly than
replaying the aggregate analysis. The archive preserves the exact acceptance
rules, missing applicability of scaled bound contrasts, tiny written-bound
violations and adverse runtime outcomes. It does not certify MILP optimality.
Provenance and manifests identify excluded infrastructure attempts; their
separate raw archives remain outside this bundle. Before fresh model generation,
restore execute permission on code/build-audit/SistemaElectrico if required.

## Build the current documents

Extract orf-editable-sources.zip separately, verify CONTENTS.sha256 and run `make`.
It supplies pdfLaTeX sources, bibliography, publisher class/style, figures, current
main PDF, Online Resource 1 and letter. orf-revision-sources.zip supplies the
repository-relative canonical editorial inputs and build scripts as well.

To reconstruct the complete package from those canonical revision sources,
create paper/submission/oms/releases/{PARENT}/ beneath the extracted revision
root. Copy {SCIENCE} there as reproducibility-artifact.zip and copy
SCIENTIFIC_PARENT_VALIDATION.json there as VALIDATION.json. Then run
`make paper` and `python3 scripts/research/package_orf.py`. For packaging, also
extract both follow-up archives over the revision root, copy {VERIFIED_ARCHIVE}
to exploration/orf-v15-verified-20261019/research-evidence.zip and copy
VERIFIED_PACKAGE_VALIDATION.json there as PACKAGE_VALIDATION.json. Run
`python3 scripts/research/orf_followup_tables.py` to regenerate the five selected
follow-up tables. Also extract {CONFIRMATION_ARCHIVE} and
{CONFIRMATION_SUPPORT_ARCHIVE} over the revision root,
copy the tar/xz file into exploration/orf-confirmatory-extension-20261019/ and
copy CONFIRMATION_ARCHIVE_VALIDATION.json into that directory. Run
`python3 scripts/research/orf_acceptance_sensitivity.py` and
`python3 scripts/research/check_orf_acceptance_sensitivity.py` to reconstruct
and independently check the post hoc threshold sensitivity from all saved
eligible vectors. It reuses sealed physical/row/cost audits, changes no registered
endpoint, and estimates no alternative verification times. Its plan and results
are in exploration/orf-acceptance-sensitivity-20261022 within the canonical ZIP.
Then run `python3 scripts/research/orf_confirmation_tables.py` to regenerate the
seven confirmation table fragments. All these inputs are supplied here; the
parent ZIP does not need a separate public download.

Rebuilding all 1,530 historical bases additionally requires the separate baseline
bulk archive at DOI 10.5281/zenodo.23145294. That DOI identifies the historical
baseline, not the later experiments or this submission. The four saved-result
commands above do not need that bulk archive. Fresh timed solver runs require
the documented solver versions and licenses and have hardware-dependent timing.

Code is MIT; data/results are CC BY 4.0. Publisher class/style files retain their
own notices. Manuscript text and PDFs are outside the code/data licenses.
'''
    esm=OUT/'ESM_2.zip'
    archive(esm,{'README.md':guide,'SNAPSHOT.json':OUT/'SNAPSHOT.json',
        CONFIRMATION_SUPPORT_ARCHIVE:support_zip,
        FOLLOWUP_ARCHIVE:followup_zip,
        VERIFIED_ARCHIVE:verified_zip,'VERIFIED_PACKAGE_VALIDATION.json':VERIFIED/'PACKAGE_VALIDATION.json',
        CONFIRMATION_ARCHIVE:CONFIRMATION_ARCHIVE_PATH,
        'CONFIRMATION_ARCHIVE_VALIDATION.json':CONFIRMATION/'CONFIRMATION_ARCHIVE_VALIDATION.json',
        SCIENCE:parent_archive,'SCIENTIFIC_PARENT_VALIDATION.json':PARENT_DIR/'VALIDATION.json',
        'orf-editable-sources.zip':source_zip,'orf-revision-sources.zip':revision_zip,
        'ONLINE_RESOURCE_CAPTIONS.txt':captions,'CITATION.cff':ROOT/'CITATION.cff',
        'zenodo-metadata.json':ROOT/'.zenodo.json','LICENSE':ROOT/'LICENSE','DATA_LICENSE.md':ROOT/'DATA_LICENSE.md'})
    uploads=OUT/'uploads';uploads.mkdir(exist_ok=True)
    for name,origin in {'main_orf.pdf':ORF/'main_orf.pdf','cover-letter.pdf':ORF/'cover-letter.pdf',
                        'title-page.pdf':ORF/'title-page.pdf',
                        'ESM_1.pdf':ORF/'ESM_1.pdf','ESM_2.zip':esm,'orf-editable-sources.zip':source_zip}.items():
        destination=uploads/name
        if destination.exists() or destination.is_symlink():destination.unlink()
        if origin.stat().st_size>20_000_000:os.link(origin,destination)
        else:shutil.copyfile(origin,destination)
    (uploads/'REPRODUCE.md').write_text(guide)
    (uploads/'ONLINE_RESOURCE_CAPTIONS.txt').write_text(captions)
    (uploads/'UPLOAD_INSTRUCTIONS.md').write_text('''# ORF separate upload preparation

Extract orf-delivery.zip before assigning individual files in the portal.
main_orf.pdf: manuscript with author details (single-blind review).
orf-editable-sources.zip: editable LaTeX source files.
cover-letter.pdf: editor-only cover letter.
title-page.pdf: author information and title-page acknowledgements; use the portal's
title-page role if requested. Author details also remain in the main manuscript.
ESM_1.pdf: Online Resource 1; ESM_2.zip: Online Resource 2, both for review.
ONLINE_RESOURCE_CAPTIONS.txt gives the supplementary captions.
FORM_FIELDS.json supplies the current title, abstract, keywords and declarations.

The official journal instructions were checked again on 22 October 2026:
https://link.springer.com/journal/43069/submission-guidelines
Confirm the exact portal categories and limits when uploading. Enter author
contributions and competing interests in the interface too. The DOI/deposit
remains deferred by the author; no remote submission or publication was performed.
REPRODUCTION-VALIDATION.json must say passed. SHA256SUMS covers all delivery files.
''')
    abstract=plain((ORF/'editorial/abstract.tex').read_text())
    assert 150<=len(abstract.split())<=250
    scientific_source=(PAPER/'main.tex').read_text()
    declarations={}
    for name,body in re.findall(r'\\paragraph\{([^}]+)\}\s*(.*?)(?=\\paragraph\{|\\section\*?\{|\Z)',scientific_source,re.S):
        if name in ('Funding','Competing interests','Author contributions',
                    'Ethics approval, consent and human or animal participants','AI declaration'):
            declarations[name]=plain(body)
    assert len(declarations)==5
    fields={'version':VERSION,'journal':'Operations Research Forum','proposed_article_type':'Original Research Article',
        'title':TITLE,'abstract':abstract,'abstract_words':len(abstract.split()),
        'keywords':['Mixed-integer programming','Numerical scaling','Feasibility tolerances',
                    'Accuracy contracts','Computational optimization','Reproducibility'],
        'author':{'name':'Mathias Rodríguez Castro','affiliation':'Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay',
                  'email':'mathiasr@fing.edu.uy','orcid':'0009-0002-7235-7677','corresponding_author':True},
        'MSC_2020':['90C11','65F35','90-08','65G50'],'declarations':declarations,
        'data_availability':plain((ORF/'editorial/availability.tex').read_text().split('}',1)[1]),
        'funding_received':False,'CAP_supported_work':False,'new_version_DOI':None,
        'DOI_deferred_by_author':True,'portal_categories_confirmed':False,'submission_performed':False}
    write_json(uploads/'FORM_FIELDS.json',fields)
    build_delivery()
    print('Prepared full ORF delivery:',VERSION,'abstract words:',len(abstract.split()))


if __name__=='__main__':main()
