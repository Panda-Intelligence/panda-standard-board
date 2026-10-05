# CURRENT OVERRIDE: <=7mm native product relayout

The user explicitly rejected the22mm prototype and asked for PCB relayout.
Finished whole-device thickness MUST be <=7mm, including positive tolerances.
USB-C is allocated to bottom center and microSD to the right side near the lower
corner. Read `hardware/thin18-compact/SEVEN-MM-RELAYOUT.md` and
`seven_mm_layout.json`. They supersede older text freezing the existing outline,
WROOM module, stacked connector or treating7mm as merely optional.

The latest develop is the electrical/BOM donor; preserve the proven functionality,
all-mainland identity policy,16MB Flash/8MB PSRAM,>=24h isolated RTC and direct
shutdown. Do not merge the old R2/media branches or claim its work is verified here.
New native candidates must stay in ignored/external output; only reviewed source,
contracts, tests and reusable builders belong in Git. No renders/models/reports/ZIPs.

The source allocation and initial footprint packing are NOT finished native
routing, supplier maximum-envelope qualification, or fabrication approval. The
old product-render/RFQ/release entry points are deliberately blocked. Do not remove
that stop based on a budget calculation, old DRC, or scaled visuals. New parts,
footprints, pin maps, current/returned-path routing, mechanical tolerance and full
native rebuild checks must precede release. Keep the old routed CAD reversible.
MacBook canonical checkout remains `/Users/isaac/workspace/AI/panda-standard-board`;
any Mac-mini cache clone is temporary validation, not another long-lived worktree.

# Earlier guidance (current override above governs product geometry)

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

## Generated-output Git policy — user instruction 2026-10-04

Do NOT commit or push generated or intermediate render deliverables without
explicit user authorization for those artifacts. Rendering, viewing, or delivering
a result is not permission to put it in Git. This includes rendered PNG/JPEG,
MP4/GIF, frame sequences, generated Blender/GLB exports, preview galleries,
render manifests/checksums, and disposable scripts stored with those outputs.

Keep render output under ignored `/.work/` or `/visualization/`, or another
user-designated delivery location. Never use a source-code repository as a file
transfer workaround. Reusable rendering source belongs in a reviewed source
location separately from generated assets. Native PCB/schematic libraries and
required source contracts remain versioned according to the existing CAD policy.

Inspect the exact staged paths and diff before any commit; do not broadly stage
an output directory or force-add ignored render files. Preserve local deliverables
when removing them from tracking. Do not rewrite pushed history, delete remote
branches, or force-push as a cleanup shortcut without explicit authorization.

## Canonical checkout and integration branch

Continue the validated Split-C1 in `/Users/isaac/workspace/AI/panda-standard-board`
on `develop`. This branch starts from merged main `be0ef37`, not the discarded
Thin7/R2 or media-only branch. Worktree cleanup archives stay outside this repo.
Keep the existing untracked `packaging/` untouched. Reusable renderer code may
be reviewed as source; output goes to an external delivery directory or `.work`.

Fresh verification JSON, native interface measurements and release-candidate reports
are generated outputs and explicitly ignored. Run the release pipeline to recreate
them; do not force-add them. Source replay plans, precise BOM/part contracts, tests
and handoffs remain versioned. Keep any actual supplier receipts separately from
synthetic tests, and never mark them received based on a public catalog page.
