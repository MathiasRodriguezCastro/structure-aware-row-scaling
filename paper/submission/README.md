# Submission preparation

**Research status, 13 September 2026: not recommended for submission yet.**
New classical GCD/RHS-strengthening controls solve every case of the earlier stress experiment. The previously packaged manuscript remains a preserved candidate; substantive research is continuing. See `paper/research-audit/research-status-20260913.md`.

Prospective first venue: **Optimization Letters**. Its stated scope includes optimization theory, algorithms and computational studies, and it seeks communications of approximately 15 journal pages. The current main PDF is 15 manuscript pages; the eventual typeset length is the journal's decision. Source: [official aims and scope](https://link.springer.com/journal/11590/aims-and-scope), checked 9 September 2026.

The [author instructions](https://link.springer.com/journal/11590/submission-guidelines) request an abstract of 150–250 words, 4–6 keywords, author/contact information, declarations, and editable sources. This draft provides those items and an explicit AI-assistance declaration. The supplement is Online Resource 1; the reproducibility archive is Online Resource 2. The journal name in the supplement indicates the intended destination, not submission or acceptance.

Files prepared locally:

- `../main.pdf`: main manuscript.
- `../supporting-information.pdf`: Online Resource 1.
- `manuscript-sources.zip`: current LaTeX sources, bibliography and vector figures.
- `reproducibility-artifact.zip`: code, experiment data, manifests and verification/analysis instructions.
- `cover-letter.txt`: editable cover letter.
- `SHA256SUMS`: checksums for the local package.

`python3 scripts/research/package_submission.py` rebuilds the two archives and package checksums from the current files. It performs no upload or submission. `../research-audit/final-review.md` records internal checks and scientific limits.

The main contribution is a specific information-loss theorem and its bounded extension, integrated with explicit row-factor admissibility and arithmetic checks. The interval projection itself is elementary and tolerance scaling and power-of-two scaling have clear precedents. The case for publication rests on the combined characterization, counterexamples and reproducible controls; editorial assessment of originality and significance remains uncertain.

Before an actual submission, the author needs to review and take responsibility for the final mathematical claims, code, figures and AI disclosure, and confirm the submission-system statements about prior publication, exclusive consideration and institutional approval. The cover letter does not presume those unconfirmed facts. Authorship, no external funding and no competing interests were explicitly confirmed. Nothing has been submitted, sent to editors, uploaded or released by this workflow.
