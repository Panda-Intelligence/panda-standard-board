# Panda47 HDI6 v1 local source rules

This directory is the user-approved **separate six-layer upgrade** to the
Panda47 four-layer hardware. It is a long-lived independent branch and worktree,
not permission to overwrite or merge into `main`. Follow the inherited
electrical, product, battery/panel, 7 mm mechanical and safety rules in the
repository's root AGENTS.md except the four-layer count, which this variant
overrides **only** for source and native candidates generated here.

Canonical branch: `hw/pico47-hdi6-v1`.
Version ID: `pico47-hdi6-v1`; source path:
`hardware/pico47-hdi6/variant.json`.
Exact immutable input checkpoint:
`panda47-e02-20261015-r12/engineering-candidate`.

Initial accepted six-layer engineering candidate:
`panda47-hdi6-v1-20261017/engineering-candidate`, rebuilt twice with
matching PCB, schematic, rule and manifest hashes.

The exact current signal/reference allocation and factory-blocker policy are
in `variant.json`, `README.md`, `NEXT-STEPS.md`. In1/In4 are reference GND,
In3 is new signal. Preserve the actual original copper and all 237 GND pads;
no signal tracks on In1/In4; preserve the complete GPIO2/R813/U810.EN chain,
U810 negative EP isolation, C804 return, all footprints/pad UUIDs/net mappings
and via minima. Six-layer HDI blind-via architecture is *not* adopted merely
because the layer count has increased; only adjacent allowed layer spans may
be used and factory confirmation is required.

The initial native DRC is zero errors and warnings on both boards, but
there are still Core24 and Display4 unconnected items. That is **NOT**
manufacturing-ready. Do not use previous invalid 0-open geometric routes as
manufacturable copper. Require native zero-open, all-severity DRC, ERC/parity,
original-pad-group and complete-ground checks and source replay before
manufacturing review. Then require factory stackup, CAM/SMT, BOM/CPL, exact
pack/panel and mechanical qualification as applicable to the prototype type.

Keep generated boards, netlists, Gerbers, reports and route sessions external/
ignored. Do not change the root four-layer source builder on this branch as a
shortcut. Continue in the independent namespace; preserve the four-layer main
baseline and untracked packaging/.
