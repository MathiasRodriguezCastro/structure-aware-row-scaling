# Operations Research Forum manuscript

Current editorial version: **v1.4.0-orf-submission**.

**Accuracy-Aware Row Scaling for Generated Mixed-Integer Programs: A Computational
and Software Study** — Mathias Rodríguez Castro.

Run `make paper` from the repository root. The main PDF is `main_orf.pdf`;
`ESM_1.pdf` is Online Resource 1 and `cover-letter.pdf` is the new ORF letter.
The publisher class and numeric bibliography style are retained unmodified;
see [template provenance](TEMPLATE_PROVENANCE.md).

The ORF adaptation leads with accuracy-aware model generation and verification,
followed by computational evaluation and mechanism attribution. It adds practical
interpretation of original-unit budgets, returned-point checks and preparation
overhead. Mathematical statements, proofs, experimental records and numerical
tables are preserved. No additional optimizer experiments are introduced.

`editorial/` contains the canonical ORF abstract, opening, practical implications,
availability and reproduction instructions. `scripts/research/build_orf.py` applies
them to the preserved scientific body in `paper/main.tex`, generates
`main_orf.tex` and `ESM_1.tex`, and copies shared inputs. Edit those editorial
fragments or the shared scientific source, rather than the generated mirrors.
The self-contained editable source ZIP includes the generated complete TeX files.

The current data archive is Online Resource 2. It contains the **exact** previously
audited `v1.3.17-oms-submission` scientific-evidence ZIP, its validation report, the
current ORF sources and an inheritance record. Its historical internal names are
preserved. This keeps scientific replay separate from the current editorial
format. The frozen OMS delivery remains unchanged.

See [submission preparation](../submission/orf/README.md). The current local
snapshot has no separately assigned Zenodo DOI; the historical baseline DOI does
not identify the later experiments. No journal submission has been performed.
