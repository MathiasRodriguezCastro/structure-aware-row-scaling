# Attribution controls — Option B (block metadata) is closed

Frozen snapshot of the attribution study before the new operational campaign
(Base / Flat-GM / Flat-L2 / Role-Hybrid). All figures below are for the headline
cell **block_heterogeneous, coupling, S=6, R=2 (`SYNTH_BLOCK_RANGE=2`), 30 seeds,
κ2+** unless stated. Raw per-seed data lives beside this file:

- `kappa2_controls_blockhet_S6.csv` — SA-Mat / Flat-Mat / Flat-L2 / SA-Mat-permB
- `kappa2_optionB_blockhet_S6.csv` — SA-Pre / SA-Pre-permB (Option B)
- `kappa2_localGMcouplingL2_blockhet_S6.csv` — Local-GM-Coupling-L2 control
- `kappa2_perm24_blockhet_S6.csv`, `rank_true_map_perm24.csv` — 24-permutation sweep

## Established results (do not re-derive)

1. **SA-Mat is byte-identical to Local-GM-Coupling-L2** (κ2+ ratio = 1.000, 0/30
   seeds differ). SA-Mat's coupling factor was always `γ_r = 1/‖a_r‖₂`.

2. **The SA-Mat vs Flat-Mat advantage is the kernel on the coupling rows, not the
   block metadata.** Flat-Mat (geometric-mean, role-blind) = 1.36e4; SA-Mat = Flat-L2
   in norm = Euclidean on the coupling rows. The 10× gap is Euclidean-vs-geometric-mean,
   not `s_i`/`β`.

3. **SA-Pre loses to the blind control Local-GM-Coupling-L2 in 30/30 seeds**
   (SA-Pre 6.69e3 vs blind 1.33e3; 4.27× worse). Connecting the block map via
   `s_i^pre` computed before the local kernel actively hurts.

4. **The true block→scale map is never the best of the 24 permutations** (0/30 seeds
   rank 1). A permuted map beats the true map in 30/30 seeds (best permuted 5.6×
   better than true).

5. **Rank of the true map among the 24 permutations: min 8, median 18, max 24.**
   The correct assignment sits among the *worst* choices.

6. **Therefore the block scale `s_i^pre` does not rescue the block-metadata
   hypothesis.** With the geometric-mean kernel the post-local block scale degenerates
   to `s_i = 1` (permute-β byte-identical); the pre-local variant is worse than blind.

## Consequence

Neither the operational nor the synthetic evidence isolates block metadata. The
synthetic effect attributed to block structure is a **norm/kernel** effect
(Euclidean per coupling row). SA-Pre is retained only as a **falsification**
experiment, never as a recommended method. The paper's central positive claim as
stated is unsound and must be reframed after the operational campaign decides among
Base / Flat-GM / Flat-L2 / Role-Hybrid.

Frozen at git tag `attribution-controls-frozen` (commit 5e2eb5d).
