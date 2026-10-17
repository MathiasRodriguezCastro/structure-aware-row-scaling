#!/usr/bin/env python3
"""Prepare local portal text and exact source files from a frozen OMS release.

Does not sign in, submit, upload, contact editors, or change a frozen release.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
import zipfile

from oms_snapshot import ROOT, OUT, VERSION, REVISION_DATE


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def argument(text, command):
    """Read one balanced braced argument, including nested LaTeX groups."""
    match = re.search(re.escape(command) + r'\s*\{', text)
    if match is None:
        raise ValueError(f'Missing {command}')
    start = match.end()
    depth = 1
    for position in range(start, len(text)):
        if position and text[position - 1] == '\\':
            continue
        if text[position] == '{':
            depth += 1
        elif text[position] == '}':
            depth -= 1
            if not depth:
                return text[start:position]
    raise ValueError(f'Unclosed {command}')


def plain(text):
    text = re.sub(r"\\'\{?([A-Za-z])\}?",
                  lambda m: unicodedata.normalize('NFC', m[1] + '\u0301'), text)
    text = re.sub(r'\\doi\{([^{}]*)\}', r'https://doi.org/\1', text)
    for command in ('url', 'path', 'texttt', 'emph', 'textbf'):
        text = re.sub(r'\\' + command + r'\{([^{}]*)\}', r'\1', text)
    text = text.replace('\\_', '_').replace('~', ' ').replace('--', '–')
    if '\\' in text:
        raise ValueError(f'Unconverted LaTeX in form text: {text}')
    return ' '.join(text.split())


def main():
    release = OUT / 'releases' / VERSION
    target = OUT / 'portal-preparation' / VERSION
    if target.exists():
        raise SystemExit(f'Refusing to overwrite existing preparation: {target}')
    release_checks = {}
    for line in (release / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        assert digest(release / name) == expected, name
        release_checks[name] = expected
    validation = json.loads((release / 'VALIDATION.json').read_text())
    assert validation['snapshot_version'] == VERSION
    source_zip = release / 'oms-submission.zip'
    with zipfile.ZipFile(source_zip) as source:
        source_bytes = {name: source.read(name) for name in source.namelist()
                        if not name.endswith('/')}
    assert source_bytes['main_oms.pdf'] == (release / 'main_oms.pdf').read_bytes()
    tex = source_bytes['main_oms.tex'].decode()
    pdf_text = subprocess.check_output(
        ['pdftotext', '-layout', str(release / 'main_oms.pdf'), '-'], text=True)
    abstract_pdf = ' '.join(pdf_text.split('ABSTRACT', 1)[1].split('KEYWORDS', 1)[0].split())
    abstract_pdf_words = len(abstract_pdf.split())
    assert 0 < abstract_pdf_words <= 200
    # Restore superscript notation lost by text extraction, without changing meaning.
    abstract = abstract_pdf.replace(' m3', ' m³').replace('10−9', '10^(-9)')
    abstract = re.sub(r'\s+([,.;:!?])', r'\1', abstract)
    abstract_words = len(abstract.split())
    assert 0 < abstract_words <= 200
    assert not any(character in abstract for character in ('\\', '$', '\x0c'))
    keyword_tex = re.search(r'\\begin\{keywords\}(.*?)\\end\{keywords\}', tex, re.S)
    assert keyword_tex is not None
    keywords = [plain(item).rstrip('.') for item in keyword_tex[1].split(';')]
    assert len(keywords) == 6
    title = plain(argument(tex, r'\title'))
    cff = (release / 'CITATION.cff').read_text()
    assert f'title: "{title}"' in cff
    author = {'given_names': 'Mathias', 'family_names': 'Rodríguez Castro',
              'full_name': 'Mathias Rodríguez Castro',
              'affiliation': 'Facultad de Ingeniería, Universidad de la República, Montevideo, Uruguay',
              'email': 'mathiasr@fing.edu.uy', 'orcid': '0009-0002-7235-7677',
              'country': 'Uruguay', 'corresponding_author': True, 'sole_author': True}
    for value in (author['given_names'], author['family_names'], author['email'], author['orcid']):
        assert value in cff
    declarations = {}
    for match in re.finditer(r'\\paragraph\{([^}]+)\}\s*(.*?)(?=\\paragraph\{|\\section\*?\{|\Z)', tex, re.S):
        if match[1] in ('Funding', 'Competing interests', 'Author contributions',
                        'Ethics approval, consent and human or animal participants', 'AI declaration'):
            declarations[match[1]] = plain(match[2])
    assert len(declarations) == 5
    availability = re.search(r'\\section\*\{Data and software availability\}(.*?)\\section\*\{', tex, re.S)
    assert availability is not None
    availability_text = '\n\n'.join(plain(p) for p in re.split(r'\n\s*\n', availability[1].strip()))
    assert VERSION in availability_text and 'no separate Zenodo version DOI' in availability_text
    fields = {'snapshot': VERSION, 'preparation_date': REVISION_DATE,
              'journal': 'Optimization Methods and Software',
              'proposed_article_type': 'Research Article', 'title': title,
              'abstract': abstract, 'abstract_words': len(abstract.split()),
              'keywords': keywords, 'author': author,
              'MSC_2020': ['90C11', '65F35', '90-08', '65G50'],
              'MSC_2010_compatible': ['90C11', '65F35', '90-08', '65G50'],
              'MSC_version_label_in_frozen_manuscript': '2020',
              'declarations': declarations, 'data_and_software_availability': availability_text,
              'funding_form': {'financial_funding_received': False, 'funders': [],
                               'grant_identifiers': [], 'CAP_supported_this_work': False,
                               'computing_resources_acknowledgement': 'ClusterUY'},
              'new_OMS_dataset_DOI': None, 'DOI_deferred_by_author': True,
              'historical_baseline_DOI': '10.5281/zenodo.23145294',
              'portal_dropdown_values_and_journal_limits_confirmed': False}
    for code in fields['MSC_2020']:
        assert code in tex
    target.mkdir(parents=True)

    def write(name, data):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    write('FORM_FIELDS.json', fields)
    write('title.txt', title + '\n')
    write('abstract.txt', abstract + '\n')
    write('keywords.txt', '\n'.join(keywords) + '\n')
    write('author.txt', '\n'.join(f'{key}: {value}' for key, value in author.items()) + '\n')
    write('declarations.txt', '\n\n'.join(f'{key}\n{value}' for key, value in declarations.items()) + '\n')
    write('data-availability.txt', availability_text + '\n')
    write('funding-form.txt', 'Financial funding received: No.\n'
          'Funder and grant identifiers: Not applicable.\n'
          'Funding statement: No external financial funding or research grant was received.\n'
          'Computing resources: ClusterUY, acknowledged in the manuscript.\n'
          'The author confirmed CAP did not support this work.\n')
    write('cover-letter.txt', subprocess.check_output(
        ['pdftotext', str(release / 'cover-letter.pdf'), '-'], text=True).replace('\x0c', '').strip() + '\n')
    for name, contents in source_bytes.items():
        path = target / 'latex-sources' / name
        assert path.resolve().is_relative_to((target / 'latex-sources').resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    def expand(name, stack=()):
        assert name not in stack
        text = source_bytes[name].decode()
        return re.sub(r'\\input\{([^}]+)\}',
                      lambda match: expand(match[1] + '.tex', stack + (name,)), text)

    figure_records = []
    for index, block in enumerate(re.findall(r'\\begin\{figure\}(.*?)\\end\{figure\}', expand('main_oms.tex'), re.S), 1):
        filename = re.search(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', block)[1]
        source_name = 'figs/research/' + filename
        figure_path = target / 'figures-if-requested' / f'Figure-{index}-{filename}'
        figure_path.parent.mkdir(parents=True, exist_ok=True)
        figure_path.write_bytes(source_bytes[source_name])
        caption = argument(block, r'\caption')
        figure_records.append({'figure': index, 'source_member': source_name,
                               'file': str(figure_path.relative_to(target)), 'sha256': digest(figure_path)})
        write(f'figures-if-requested/Figure-{index}-caption.tex', caption + '\n')
    assert len(figure_records) == 2
    roles = [('main_oms.pdf', 'Manuscript – with author details', True),
             ('oms-submission.zip', 'LaTeX source files; confirm the exact portal label', True),
             ('cover-letter.pdf', 'Cover letter / editor-only file', False),
             ('supplementary-material-1.pdf', 'Supplementary Material 1; for peer review', True),
             ('reproducibility-artifact.zip', 'Supplementary Material 2; for peer review', True)]
    uploads = [{'file': name, 'absolute_path': str(release / name),
                'bytes': (release / name).stat().st_size, 'sha256': release_checks[name],
                'intended_role': role, 'intended_for_peer_review': review,
                'exact_portal_category_confirmed': False,
                'required_at_initial_submission': None} for name, role, review in roles]
    for item in uploads:
        if item['file'] == 'oms-submission.zip':
            item['editable_sources_required_for_accepted_final_submission'] = True
            item['source_of_final_stage_requirement'] = 'Taylor & Francis Interact documentation, Section 1.2'
    write('UPLOAD_MAP.json', {'version': VERSION, 'files': uploads, 'figures_if_requested': figure_records})
    write('VALIDATION.json', {'version': VERSION, 'frozen_release_checksums_verified': len(release_checks),
          'source_archive_member_count': len(source_bytes),
          'all_source_payload_files_plus_checksum_extracted_identically': True,
          'source_archive_manuscript_matches_frozen_upload': True,
          'abstract_semantically_identical_to_frozen_PDF_except_restored_typography': True,
          'abstract_words': abstract_words,
          'raw_PDF_abstract_words_before_punctuation_normalization': abstract_pdf_words,
          'keywords': 6, 'declarations_from_frozen_source': 5,
          'main_article_figures_extracted_identically': len(figure_records),
          'saved_scientific_results_changed': False, 'native_optimizer_calls': 0,
          'remote_upload_performed': False, 'journal_submission_performed': False,
          'release_checksums': release_checks})
    print('Prepared portal form fields and exact sources:', target.relative_to(ROOT))
    print(f'Portal abstract: {abstract_words} words; raw PDF extraction: {abstract_pdf_words}; '
          f'keywords: {len(keywords)}; upload roles: {len(uploads)}; article figures: {len(figure_records)}.')


if __name__ == '__main__':
    main()
