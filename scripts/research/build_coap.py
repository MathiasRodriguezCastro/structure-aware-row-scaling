#!/usr/bin/env python3
"""Derive the COAP submission using the established Springer conversion."""
import build_mpc as springer

springer.OUT = springer.ROOT / "paper/coap/main_coap.tex"
springer.ABSTRACT = springer.ROOT / "paper/coap/abstract.tex"
springer.PREAMBLE = springer.PREAMBLE.replace("Mathematical Programming Computation", "Computational Optimization and Applications").replace("scripts/research/build_mpc.py", "scripts/research/build_coap.py").replace("paper/mpc/MPC_NOTES.md", "paper/coap/COAP_NOTES.md").replace("Computational reproducibility", "Finite-precision optimization")

springer.PREAMBLE = springer.PREAMBLE.replace(r"\smartqed", r"\smartqed" + "\n" + r"\renewcommand{\makeheadbox}{}")

springer.PREAMBLE = springer.PREAMBLE.replace(r"\date{Received: date / Accepted: date}", r"\date{}")

if __name__ == "__main__":
    springer.main()
