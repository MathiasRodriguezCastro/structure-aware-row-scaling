#!/usr/bin/env python3
"""Audit the ORF sources, preserved science and full clean-extraction replay."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import os
import tarfile
import unicodedata
import zipfile
from orf_config import ROOT, PAPER, ORF, OUT, VERSION, PARENT, TITLE, FOLLOWUP_ARCHIVE, VERIFIED_ARCHIVE, sha
from orf_config import CONFIRMATION_ARCHIVE, COMPARATIVE_MIP_CALLS
from orf_config import CONFIRMATION_SUPPORT_ARCHIVE
from orf_resource_inventory import check_coverage
from package_orf import FILES, EXTRAS, SCIENCE, build_delivery, write_json
from build_orf import relabel


def run(command,cwd):
    r=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    if r.returncode:
        raise RuntimeError(' '.join(command)+'\n'+r.stdout[-7000:]+r.stderr[-2000:])
    return r.stdout


def extract(path,destination,manifest='CONTENTS.sha256'):
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        assert all((destination/n).resolve().is_relative_to(destination.resolve()) for n in z.namelist())
        z.extractall(destination)
    run(['sha256sum','--quiet','-c',manifest],destination)


def compile_documents(folder):
    run(['make','-B'],folder)
    result={}
    for stem in ('main_orf','ESM_1','cover-letter','title-page'):
        log=(folder/(stem+'.log')).read_text()
        assert 'Overfull' not in log,stem+' has overfull content'
        assert 'undefined' not in log.lower(),stem+' has unresolved references'
        pages=int(re.search(r'Pages:\s+(\d+)',run(['pdfinfo',stem+'.pdf'],folder))[1])
        result[stem]={'pages':pages,'rebuilt_from_extracted_sources':True,
                      'overfull_boxes':0,'undefined_references':0}
    assert result['cover-letter']['pages']==1
    assert result['title-page']['pages']==1
    return result


def extract_confirmation(path,destination):
    """Unpack checked regular files/hard links; retain deduplication on disk."""
    contents={}
    manifest=None
    with tarfile.open(path,'r|xz') as archive:
        for item in archive:
            relative=Path(item.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            target=(destination/relative).resolve()
            assert target.is_relative_to(destination.resolve())
            if item.name=='CONFIRMATION_ARCHIVE_CONTENTS.json':
                manifest=json.load(archive.extractfile(item))
                continue
            assert item.name not in contents
            target.parent.mkdir(parents=True,exist_ok=True)
            if item.islnk():
                assert item.linkname in contents
                source=(destination/item.linkname).resolve()
                assert source.is_relative_to(destination.resolve())
                if target.exists():target.unlink()
                os.link(source,target)
                contents[item.name]=dict(contents[item.linkname],path=item.name)
            else:
                assert item.isfile()
                # Remove a prior hard link before replacing its contents.
                if target.exists():target.unlink()
                with target.open('wb') as stream:
                    h=hashlib.sha256();count=0
                    incoming=archive.extractfile(item)
                    for block in iter(lambda:incoming.read(1048576),b''):
                        stream.write(block);h.update(block);count+=len(block)
                assert count==item.size
                target.chmod(item.mode & 0o777)
                contents[item.name]=dict(path=item.name,bytes=count,sha256=h.hexdigest())
    assert manifest and [contents[n] for n in sorted(contents)]==manifest['files']
    return manifest


def expand(name,folder,stack=()):
    assert name not in stack
    source=(folder/name).read_text()
    source=re.sub(r'\\adjustbox\{max width=\\linewidth\}\{(\\input\{tables/[^}]+\})\}',r'\1',source)
    return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(m[1]+'.tex',folder,stack+(name,)),source)


def normalized(source):
    return re.sub(r'\s+','',relabel(source))


def scientific_preservation(science,sources):
    old=expand('main.tex',science/'paper');new=expand('main_orf.tex',sources)
    begin=r'\section{Scaling framework}';end=r'\section{Discussion and conclusions}'
    old_core=old.split(begin,1)[1].split(end,1)[0]
    new_core=new.split(begin,1)[1].split(end,1)[0]
    addition=r'\subsection{Prospective scenario validation}'
    assert addition in new_core
    new_core=new_core.split(addition,1)[0]
    new_core=re.sub(r'\\paragraph\{Research-tool documentation\}.*?\n\n','',new_core,flags=re.S)
    extension=r'% BEGIN ORF EXPORT SELECTOR EXTENSION.*?% END ORF EXPORT SELECTOR EXTENSION'
    assert len(re.findall(extension,new_core,re.S))==1
    assert r'\label{eq:orf-selected-export-contract}' in new_core
    new_core=re.sub(extension,'',new_core,flags=re.S)
    assert normalized(old_core)==normalized(new_core),'Scientific sections changed'
    start=r'\subsection{Scope and limitations}';finish=r'\subsection{Conclusions}'
    new_scope=new.split(start,1)[1].split(finish,1)[0]
    scope_extension=r'% BEGIN ORF LARGER CONFIRMATION SCOPE.*?% END ORF LARGER CONFIRMATION SCOPE'
    assert len(re.findall(scope_extension,new_scope,re.S))==1
    new_scope=re.sub(scope_extension,'',new_scope,flags=re.S)
    assert normalized(old.split(start,1)[1].split(finish,1)[0])==normalized(new_scope)
    assert '3,840-assignment confirmation' in new.split(finish,1)[1]
    old_si=expand('supporting-information.tex',science/'paper')
    new_si=expand('ESM_1.tex',sources)
    addition=r'\section{Prospective scenario validation}'
    assert addition in new_si
    new_si=new_si.split(addition,1)[0]+r'\section{Finite-export residual accounting}'+new_si.split(r'\section{Finite-export residual accounting}',1)[1]
    extra_start=r'\section{Finite-export residual accounting}'
    extra_end=r'\section{Reproduction and artifact layout}'
    assert extra_start in new_si
    extension=new_si.split(extra_start,1)[1].split(extra_end,1)[0]
    assert 'eq:orf-export-transfer' in extension and 'eq:orf-export-contract' in extension
    new_si=new_si.split(extra_start,1)[0]+extra_end+new_si.split(extra_end,1)[1]
    old_si=old_si.split(r'\section{Proof for the triangular model}',1)[1].split(r'\section{Reproduction and artifact layout}',1)[0]
    new_si=new_si.split(r'\section{Proof for the triangular model}',1)[1].split(r'\section{Reproduction and artifact layout}',1)[0]
    assert normalized(old_si)==normalized(new_si),'Scientific supplement changed'
    theorem=r'\\begin\{(theorem|proposition|lemma|corollary|definition|example|proof)\}(.*?)\\end\{\1\}'
    old_math=re.findall(theorem,old+'\n'+old_si,re.S)
    new_math=re.findall(theorem,new+'\n'+new_si,re.S)
    assert len(old_math)>0 and [(a,normalized(b)) for a,b in old_math]==[(a,normalized(b)) for a,b in new_math]
    # A tabular row break followed by [4pt] is not a display-math opener.
    display=r'(?<!\\)\\\[(.*?)(?<!\\)\\\]'
    old_display=re.findall(display,old+'\n'+old_si,re.S)
    new_display=re.findall(display,new+'\n'+new_si,re.S)
    assert [normalized(x) for x in old_display]==[normalized(x) for x in new_display]
    tables=list((sources/'tables').glob('*.tex'))
    assert len(tables)==42
    for table in tables:assert table.read_bytes()==(science/'paper/tables'/table.name).read_bytes(),table.name
    return {'scientific_sections_3_to_7_identical_after_resource_relabelling':True,
        'inherited_scope_preserved_with_explicit_confirmation_extension':True,
        'conclusions_updated_for_complete_confirmation':True,'technical_supplement_preserved':True,
        'theorem_definition_example_and_proof_environments':len(old_math),
        'displayed_math_blocks_preserved':len(old_display),'numerical_table_files_identical':len(tables),
        'additional_elementary_export_bound_documented':True,
        'constructive_export_selector_added_without_changing_inherited_statements':True,
        'new_optimization_experiments':COMPARATIVE_MIP_CALLS,'earlier_prospective_exact_LP_attempts':96, 'confirmation_reference_exact_LP_attempts':181}


def abstract_normalized(text):
    text=unicodedata.normalize('NFKD',text)
    return ''.join(c.lower() for c in text if c.isalnum() or c in '.%')


def render_hashes(root):
    with tempfile.TemporaryDirectory(prefix='orf-figure-render-') as tmp:
        hashes={}
        for p in sorted((root/'paper/figs/research').glob('*.pdf')):
            dest=Path(tmp)/p.stem
            run(['pdftoppm','-f','1','-singlefile','-scale-to','1200','-png',str(p),str(dest)],root)
            hashes[p.name]=sha(dest.with_suffix('.png'))
        return hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-parent-replay',type=Path,
        help='Reuse an earlier full replay only for a byte-identical parent evidence archive; current sources and prospective evidence are still checked.')
    args=parser.parse_args()
    result={'version':VERSION,'title':TITLE,'target':'Operations Research Forum',
            'new_optimization_experiments':COMPARATIVE_MIP_CALLS,'earlier_prospective_exact_LP_attempts':96, 'confirmation_reference_exact_LP_attempts':181,
            'submitted':False,'published':False,'version_doi':None}
    uploads=OUT/'uploads'
    with tempfile.TemporaryDirectory(prefix='orf-complete-audit-') as tmp:
        workspace=Path(tmp)
        sources=workspace/'current-sources'
        extract(uploads/'orf-editable-sources.zip',sources)
        for member,upload in [('main_orf.pdf','main_orf.pdf'),('ESM_1.pdf','ESM_1.pdf'),('cover-letter.pdf','cover-letter.pdf'),('title-page.pdf','title-page.pdf')]:
            assert sha(sources/member)==sha(uploads/upload)
        result['source_builds']=compile_documents(sources)
        text=(sources/'main_orf.tex').read_text()
        assert VERSION in text and TITLE in text
        supplement_text=(sources/'ESM_1.tex').read_text()
        assert ('Online Resource~2 is the complete code/data package for\n'+r'\path{'+VERSION+'}') in supplement_text
        assert text.index('A verifiable model-generation procedure')<text.index('An auditable computational evaluation')
        assert 'Statements and Declarations' in text and 'Research-tool documentation' in text
        assert 'Supplementary Material' not in text
        pdf=run(['pdftotext','-layout','main_orf.pdf','-'],sources)
        assert 'Supplementary Material' not in pdf and 'Optimization Methods and Software' not in pdf
        assert 'Online Resource' in pdf and '??' not in pdf
        assert 'ORCID' not in pdf.split('\f',1)[0]
        titlepage=run(['pdftotext','title-page.pdf','-'],sources)
        assert '0009-0002-7235-7677' in titlepage
        fields=json.loads((uploads/'FORM_FIELDS.json').read_text())
        abstract=pdf.split('Abstract',1)[1].split('Keywords:',1)[0]
        assert abstract_normalized(abstract)==abstract_normalized(fields['abstract'])
        assert 150<=fields['abstract_words']<=250 and len(fields['keywords'])==6
        assert fields['version']==VERSION and fields['title']==TITLE
        assert fields['funding_received'] is False and fields['CAP_supported_work'] is False
        assert len(fields['declarations'])==5 and fields['DOI_deferred_by_author']
        result['forms']={'abstract_words':fields['abstract_words'],'abstract_matches_current_pdf':True,
                         'keywords':6,'declarations':5,'current_target_verified':True}
        print('ORF source archive: clean builds and current portal fields passed',flush=True)
        esm=workspace/'online-resource-2'
        extract(uploads/'ESM_2.zip',esm)
        assert sha(esm/'orf-editable-sources.zip')==sha(uploads/'orf-editable-sources.zip')
        snapshot=json.loads((esm/'SNAPSHOT.json').read_text())
        parent=json.loads((esm/'SCIENTIFIC_PARENT_VALIDATION.json').read_text())
        assert snapshot['version']==VERSION and parent['snapshot_version']==PARENT
        assert sha(esm/SCIENCE)==snapshot['scientific_archive_sha256']==parent['archives']['reproducibility-artifact.zip']['sha256']
        assert sha(esm/'SCIENTIFIC_PARENT_VALIDATION.json')==snapshot['scientific_parent_validation_sha256']
        assert json.loads((esm/'zenodo-metadata.json').read_text())['version']==VERSION
        assert f'version: "{VERSION}"' in (esm/'CITATION.cff').read_text()
        science=workspace/'scientific-evidence'
        extract(esm/SCIENCE,science)
        assert sha(esm/FOLLOWUP_ARCHIVE)==snapshot['prospective_archive_sha256']
        extract(esm/FOLLOWUP_ARCHIVE,science)
        result['scientific_preservation']=scientific_preservation(science,sources)
        before={p.name:p.read_bytes() for p in (science/'paper/tables').glob('*.tex')}
        figures=render_hashes(science)
        command_results={}
        if args.reuse_parent_replay:
            prior=json.loads(args.reuse_parent_replay.read_text())
            assert prior['scientific_parent']['archive_sha256']==sha(esm/SCIENCE)
            assert prior['scientific_parent']['byte_identical_to_audited_parent']
            assert prior['replay']['cpp_roundtrip_passed_without_skip']
            assert prior['replay']['final_tables_regenerated_identically']==len(before)
            assert prior['replay']['figures_with_identical_rendered_content']==len(figures)
            command_results=prior['replay']['four_standard_commands']
            assert set(command_results)=={'research-oms-check','research-check-python','research-check','research-analysis'}
            assert all(r['passed'] for r in command_results.values())
            result['parent_replay_reuse']={'validation_record_sha256':sha(args.reuse_parent_replay),
                'parent_archive_sha256':sha(esm/SCIENCE),
                'reason':'Editorial revalidation; identical parent evidence was fully replayed in the supplied earlier audit.'}
            print('Reusing full parent replay for the checked byte-identical archive',flush=True)
        else:
            for target in ('research-oms-check','research-check-python','research-check','research-analysis'):
                print('Extracted scientific evidence: '+target,flush=True)
                output=run(['make',target],science)
                command_results[target]={'passed':True,'output_sha256':hashlib.sha256(output.encode()).hexdigest()}
                if target=='research-check':
                    assert '1 passed' in output and 'skipped' not in output
                    assert (science/'code/build-audit/SistemaElectrico').is_file()
        print('Prospective scenario archive: rational point/certificate replay',flush=True)
        followup=science/'exploration/orf-confirmatory-20261018'
        output=run(['python3',str(followup/'check.py')],science)
        followup_validation=json.loads((followup/'VALIDATION.json').read_text())
        assert followup_validation['status']=='passed' and followup_validation['MIP_calls']==360
        assert sha(followup/'VALIDATION.json')==snapshot['prospective_validation_sha256']
        run(['python3',str(followup/'check.py'),'--logging-confirmation'],science)
        logging_validation=json.loads((followup/'logging-confirmation/VALIDATION.json').read_text())
        assert logging_validation['MIP_calls']==360 and logging_validation['complete_native_logs']==360
        result['logging_confirmation']=logging_validation
        run(['python3',str(followup/'check_export_bound.py')],science)
        result['prospective_replay']=followup_validation
        result['finite_export_bound_checks']=json.loads((followup/'EXPORT_BOUND_VALIDATION.json').read_text())
        run(['python3',str(followup/'check_cluster_analysis.py')],science)
        cluster_validation=json.loads((followup/'CLUSTER_VALIDATION.json').read_text())
        assert cluster_validation['status']=='passed' and cluster_validation['scenario_clusters']==24
        assert cluster_validation['analysis_sha256']==snapshot['cluster_analysis_sha256']
        assert cluster_validation['confidence_intervals_reconstructed_from_native_work_and_outer_timings']==32
        result['scenario_cluster_uncertainty']=cluster_validation
        run(['python3',str(followup/'parent_sensitivity.py'),'--check'],science)
        sensitivity=json.loads((followup/'PARENT_SENSITIVITY.json').read_text())
        sensitivity_validation=json.loads((followup/'PARENT_SENSITIVITY_VALIDATION.json').read_text())
        assert sensitivity_validation['status']=='passed'
        assert sensitivity_validation['analysis_sha256']==snapshot['parent_deletion_analysis_sha256']
        assert sensitivity_validation['independently_reconstructed_ratios']==56
        assert sensitivity['domains']['Base']['exact_domains_passed']==69
        assert sensitivity['domains']['Base-tight']['exact_domains_passed']==66
        assert all(sensitivity['domains'][p]['exact_domains_passed']==72 for p in ['L2','L2-NF3','Budget-L2'])
        assert 'Domains' in text and '69/72' in text and '66/72' in text
        result['known_parent_deletion_sensitivity']=sensitivity_validation
        # Replay the byte-identical frozen follow-up from the complete delivery.
        assert sha(esm/VERIFIED_ARCHIVE)==snapshot['verified_followup_archive_sha256']
        assert sha(esm/'VERIFIED_PACKAGE_VALIDATION.json')==snapshot['verified_followup_prior_validation_sha256']
        previous_verified=json.loads((esm/'VERIFIED_PACKAGE_VALIDATION.json').read_text())
        assert previous_verified['research_evidence_sha256']==sha(esm/VERIFIED_ARCHIVE)
        extract(esm/VERIFIED_ARCHIVE,science,manifest='FOLLOWUP_CONTENTS.sha256')
        verified=science/'exploration/orf-v15-verified-20261019'
        frozen_names=['VALIDATION.json','SELECTOR_VALIDATION.json','PRECISION_RESULTS.json',
                      'COMPUTATIONAL_RESULTS.json','STATISTICS_VALIDATION.json','PROJECTION_SENSITIVITY.json']
        frozen_results={n:(verified/n).read_bytes() for n in frozen_names}
        replay={}
        for command in ['check.py','check_selector.py','precision.py','analyze.py',
                        'check_statistics.py','projection_sensitivity.py']:
            print('Frozen verified-candidate follow-up: '+command,flush=True)
            output=run(['python3',str(verified/command)],science)
            replay[command]={'passed':True,'output_sha256':hashlib.sha256(output.encode()).hexdigest()}
        for n,original in frozen_results.items():
            assert (verified/n).read_bytes()==original,'Follow-up replay drift: '+n
        checked=json.loads((verified/'VALIDATION.json').read_text())
        assert checked['status']=='passed' and checked['research_MIP_assignments']==630
        assert checked['additional_technical_MIP_calls']==1 and checked['technical_repeat_independently_compared']
        assert checked['candidate_events']==6725 and checked['full_rational_candidate_audits']==1943
        statistics=json.loads((verified/'STATISTICS_VALIDATION.json').read_text())
        assert statistics['status']=='passed'
        result['verified_followup_replay']={'status':'passed','archive_sha256':sha(esm/VERIFIED_ARCHIVE),
            'six_commands':replay,'replayed_results_identical':True,
            'MIP_assignments':630,'technical_repetitions':1,'new_independent_scenarios':0,
            'candidate_events':6725,'full_rational_candidate_audits':1943,
            'statistics_validation':statistics,
            'selector_validation':json.loads((verified/'SELECTOR_VALIDATION.json').read_text())}
        print('Larger confirmation: lossless extraction and independent statistics replay',flush=True)
        assert sha(esm/CONFIRMATION_ARCHIVE)==snapshot['confirmation_archive_sha256']
        archive_validation=json.loads((esm/'CONFIRMATION_ARCHIVE_VALIDATION.json').read_text())
        assert sha(esm/'CONFIRMATION_ARCHIVE_VALIDATION.json')==snapshot['confirmation_archive_validation_sha256']
        assert archive_validation['status']=='passed' and archive_validation['full_stream_read_and_checksums']
        assert archive_validation['archive_sha256']==sha(esm/CONFIRMATION_ARCHIVE)
        manifest=extract_confirmation(esm/CONFIRMATION_ARCHIVE,science)
        assert sha(esm/CONFIRMATION_SUPPORT_ARCHIVE)==snapshot['confirmation_support_archive_sha256']
        with zipfile.ZipFile(esm/CONFIRMATION_SUPPORT_ARCHIVE) as support:
            support_members=[n for n in support.namelist() if n!='CONTENTS.sha256']
            # Repeated launch files are exactly the historical files in the tar.
            for name in support_members:
                if (science/name).exists():assert (science/name).read_bytes()==support.read(name),name
        extract(esm/CONFIRMATION_SUPPORT_ARCHIVE,science)
        assert len(support_members)==snapshot['confirmation_support_files']
        result['resource_2_coverage']=check_coverage(science,manifest,support_members)
        confirmation=science/'exploration/orf-confirmatory-extension-20261019'
        assert sha(confirmation/'CONFIRMATION_ANALYSIS.json')==snapshot['confirmation_analysis_sha256']
        expected_replay=(confirmation/'CONFIRMATION_ANALYSIS_REPLAY.json').read_bytes()
        for seal in ['seal_pending_validation.py','seal_reference_recovery.py']:
            run(['python3',str(confirmation/seal),'--check'],science)
        replay_output=run(['python3',str(confirmation/'verify_confirmation_analysis.py')],science)
        assert (confirmation/'CONFIRMATION_ANALYSIS_REPLAY.json').read_bytes()==expected_replay
        confirmation_replay=json.loads(expected_replay)
        assert confirmation_replay['status']=='passed' and confirmation_replay['comparisons_reproduced']==48
        assert confirmation_replay['bootstrap_intervals_reproduced']==80
        assert sha(confirmation/'CONFIRMATION_ANALYSIS_REPLAY.json')==snapshot['confirmation_statistical_replay_sha256']
        result['larger_confirmation']={'status':'passed','archive_sha256':sha(esm/CONFIRMATION_ARCHIVE),
            'files_reconstructed_and_checksum_verified':manifest['file_count'],
            'logical_bytes':manifest['logical_bytes'],'archive_validation':archive_validation,
            'statistical_replay':confirmation_replay,
            'output_sha256':hashlib.sha256(replay_output.encode()).hexdigest(),'new_optimizer_calls':0}
        for name,value in before.items():
            assert (science/'paper/tables'/name).read_bytes()==value==(sources/'tables'/name).read_bytes(),name
        assert render_hashes(science)==figures
        result['replay']={'four_standard_commands':command_results,
            'final_tables_regenerated_identically':len(before),'figures_with_identical_rendered_content':len(figures),
            'cpp_roundtrip_passed_without_skip':True,
            'directed_controls':json.loads((science/'exploration/oms-base-control-20261018/VALIDATION.json').read_text()),
            'interleaved_confirmation':json.loads((science/'exploration/oms-base-control-20261018/confirmation/VALIDATION.json').read_text())}
        # Current canonical editorial sources must rebuild the exact submitted TeX.
        revision=workspace/'canonical-revision'
        extract(esm/'orf-revision-sources.zip',revision)
        # Regenerate the new tables from the extracted audited results, then compare
        # with the canonical fragments shipped in the editorial source archive.
        editorial=revision/'paper/orf/editorial'
        fragments={n:(editorial/n).read_bytes() for n in ['prospective-main.tex','prospective-supplement.tex']}
        run(['python3',str(followup/'write_report.py')],science)
        for n, original in fragments.items():
            assert (science/'paper/orf/editorial'/n).read_bytes()==original,n
        result['prospective_tables_regenerated_from_audited_data']=True
        # Render every added table from the cleanly replayed machine results.
        (revision/'exploration').mkdir(exist_ok=True)
        (revision/'exploration/orf-v15-verified-20261019').symlink_to(verified,target_is_directory=True)
        added_tables=[p for p in editorial.glob('verified-*-table.tex')]
        assert len(added_tables)==5
        originals={p.name:p.read_bytes() for p in added_tables}
        run(['python3','scripts/research/orf_followup_tables.py'],revision)
        assert all((editorial/n).read_bytes()==value for n,value in originals.items())
        result['verified_followup_tables_regenerated_identically']=len(originals)
        (revision/'exploration/orf-confirmatory-extension-20261019').symlink_to(confirmation,target_is_directory=True)
        sensitivity=revision/'exploration/orf-acceptance-sensitivity-20261022'
        expected_sensitivity=(sensitivity/'SENSITIVITY.json').read_bytes()
        expected_sensitivity_validation=(sensitivity/'VALIDATION.json').read_bytes()
        assert sha(sensitivity/'SENSITIVITY.json')==snapshot['acceptance_sensitivity_sha256']
        assert sha(sensitivity/'VALIDATION.json')==snapshot['acceptance_sensitivity_validation_sha256']
        run(['python3','scripts/research/orf_acceptance_sensitivity.py'],revision)
        assert (sensitivity/'SENSITIVITY.json').read_bytes()==expected_sensitivity
        run(['python3','scripts/research/check_orf_acceptance_sensitivity.py'],revision)
        assert (sensitivity/'VALIDATION.json').read_bytes()==expected_sensitivity_validation
        result['post_hoc_acceptance_sensitivity']=json.loads(expected_sensitivity_validation)
        confirmation_tables=list(editorial.glob('confirmation-*-table.tex'))
        assert len(confirmation_tables)==7
        originals={p.name:p.read_bytes() for p in confirmation_tables}
        run(['python3','scripts/research/orf_confirmation_tables.py'],revision)
        assert all((editorial/n).read_bytes()==value for n,value in originals.items())
        result['confirmation_tables_regenerated_identically']=7
        run(['python3','scripts/research/build_orf.py'],revision)
        assert (revision/'paper/orf/main_orf.tex').read_bytes()==(sources/'main_orf.tex').read_bytes()
        assert (revision/'paper/orf/ESM_1.tex').read_bytes()==(sources/'ESM_1.tex').read_bytes()
        result['canonical_editorial_regeneration_identical']=True
        result['archives']={n:{'sha256':sha(uploads/n),'bytes':(uploads/n).stat().st_size} for n in FILES}
        result['scientific_parent']={'version':PARENT,'archive_sha256':sha(esm/SCIENCE),
                                     'validation_sha256':sha(esm/'SCIENTIFIC_PARENT_VALIDATION.json'),
                                     'byte_identical_to_audited_parent':True}
    print('ORF mathematical preservation, full replay and canonical regeneration passed',flush=True)
    build_delivery(result)
    with tempfile.TemporaryDirectory(prefix='orf-delivery-check-') as tmp:
        folder=Path(tmp)
        with zipfile.ZipFile(OUT/'orf-delivery.zip') as z:
            assert set(z.namelist())==set(FILES+EXTRAS)
            z.extractall(folder)
        run(['sha256sum','--quiet','-c','SHA256SUMS'],folder)
        assert all(sha(folder/n)==sha(uploads/n) for n in FILES+EXTRAS)
        report=json.loads((folder/'REPRODUCTION-VALIDATION.json').read_text())
        assert report['status']=='passed' and report['validation']==result
    result['delivery']={'sha256':sha(OUT/'orf-delivery.zip'),'checksums_verified':True,
                        'files':sorted(FILES+EXTRAS),'bytes':(OUT/'orf-delivery.zip').stat().st_size}
    run(['sha256sum','--quiet','-c','SHA256SUMS'],OUT)
    write_json(OUT/'VALIDATION.json',result)
    print('ORF complete delivery and all checksums passed:',VERSION,flush=True)


if __name__=='__main__':main()
