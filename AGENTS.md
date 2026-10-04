# Panda Standard Board continuation

The user's current task is **the already split, routed main-branch Split-C1**
plus completion of mainland-chip functional migration. Read
`hardware/thin18-compact/SPLIT-C1-HANDOFF.md` first.

Inspect `git worktree list`, current status and remote main before editing.
Choose the design requested by the user, not whichever experiment has the newest
mtime. `thin7/portrait-r2` is a separate experiment and is not the source of the
current Core-C1 96x68 / Display-C1 45x36 prototype. Do not import its board shape,
MCU bare-chip design, interconnect, placement or internal-layer policy.

Preserve all unrelated worktrees and existing user edits. Do not reset, overwrite
or run a constructor directly on the saved routed PCB. Test a fresh candidate,
check source hashes before adoption, and keep reversible originals under .work.

Every electrical ECO must update schematic, native PCB, local libraries, exact
BOM identity, sourcing gaps and deterministic replay together. Require both
current and immutable-baseline rebuild DRC/open/parity/ERC 0/0/0/0, independent
functional pin/variant checks, 60-pin interface and unchanged-rule checks before
adoption. Do not remove required ICs, relax DRC or invent catalog codes to pass.
Run `release_split_c1.py --target split-c1` explicitly. Thin7 remains a separate
uncompleted mechanical requirement, not an export gate for this bench prototype.

Mainland-manufacturer identity does not certify module internal die provenance,
firmware correctness, accepted supply, USB compliance or physical EVT. The PG
supervisor is informational, not MCU reset; XL9535 P14 must stay input. The REGN
PSEL divider selects a nominal reset limit, not a firmware-independent ceiling.
Keep these limitations in engineering handoffs and generated manufacturing data.

Generated .work trials, production ZIPs/Gerbers/BOMs and native temporary outputs
stay untracked. Commit reproducible source, exact contracts, tests and concise
verification evidence. Never place synthetic supplier receipts into real data.

The hardware-finish checkpoint is documented in SPLIT-C1-HARDWARE-FINISH.md.
P05 is now active-high CHG_REQUEST, P15 is unused/input, and native GPIO2 through
R931 provides the direct FL_HWEN/charger permit. Never reintroduce the old
active-low P05 policy or expander-driven HWEN. TP19 can be grounded manually;
there is no claimed autonomous watchdog. Replay `_split_c1_hardware_finish_eco.py`
after the prior power ECO and require its independent pin/land/identity checks.
