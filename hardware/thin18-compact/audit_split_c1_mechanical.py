#!/usr/bin/env python3
"""Check native split-board XY occupancy and calculate a parameterized Z budget.

Bounding boxes are conservative 2D footprint envelopes, not solid body models.
This check never signs off the enclosure, battery, or physical mating.
"""
from pathlib import Path
import argparse, hashlib, json, math
import wx
APP = wx.App(False)
import pcbnew

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"
PCB = {
    "Core-C1": ROOT / "core-c1-96x68-split" / REL / (STEM + ".kicad_pcb"),
    "Display-C1": ROOT / "display-c1-45x36-production-bom/PANDA-EPD0426-SPI-EVT.kicad_pcb",
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def mm(value): return round(pcbnew.ToMM(value), 6)
def bbox(item):
    box = item.GetBoundingBox(False, False) if isinstance(item, pcbnew.FOOTPRINT) else item.GetBoundingBox()
    return [mm(v) for v in (box.GetX(), box.GetY(), box.GetRight(), box.GetBottom())]
def intersection(a, b):
    result = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    return result if result[0] < result[2] and result[1] < result[3] else None
def display_world(rect):
    return [rect[0] + 38, 66 - rect[3], rect[2] + 38, 66 - rect[1]]

def audit(inputs_path):
    inputs = json.loads(inputs_path.read_text())
    contract = json.loads((ROOT / "split-c1-interface.json").read_text())
    if not contract["cad_complete"] or not contract["all_60_pins_verified"]:
        raise ValueError("Run verify_split_c1.py first")
    for board, path in PCB.items():
        if sha(path) != contract["pcb_sha256"][board]:
            raise ValueError("Stale interface PCB hash: " + board)
    assert contract["assembly"]["display_to_core_matrix"] == [
        [1, 0, 0, 38], [0, -1, 0, 66], [0, 0, -1, -1.5], [0, 0, 0, 1]]
    boards = {name: pcbnew.LoadBoard(str(path)) for name, path in PCB.items()}
    display_rect = [38, 30, 83, 66]
    battery_rect = inputs["battery"]["rect_xyxy_mm"]
    if len(battery_rect) != 4 or not (battery_rect[0] < battery_rect[2] and battery_rect[1] < battery_rect[3]):
        raise ValueError("Invalid planning battery rectangle")
    back = {}
    for name, board in boards.items():
        entries = []
        for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
            if fp.GetLayer() != pcbnew.B_Cu: continue
            rect = bbox(fp)
            world = display_world(rect) if name == "Display-C1" else rect
            entries.append({
                "ref": fp.GetReference(), "value": fp.GetValue(), "dnp": fp.IsDNP(),
                "in_bom": not fp.IsExcludedFromBOM(), "native_bbox_mm": rect,
                "world_bbox_mm": world,
                "overlap_display_projection": bool(intersection(world, display_rect)),
                "overlap_battery_planning_projection": bool(intersection(world, battery_rect)),
                "model_path_is_not_a_verified_body": True,
            })
        back[name] = entries
    core_gap = [e["ref"] for e in back["Core-C1"]
                if e["in_bom"] and not e["dnp"] and e["overlap_display_projection"]]
    display_gap = [e["ref"] for e in back["Display-C1"] if e["in_bom"] and not e["dnp"]]
    unexpected = {"Core-C1": sorted(set(core_gap) - {"J601"}),
                  "Display-C1": sorted(set(display_gap) - {"J1"})}
    if any(unexpected.values()):
        raise ValueError("Unexpected gap-facing SMT components: " + str(unexpected))
    pth = []
    for fp in boards["Core-C1"].GetFootprints():
        if fp.IsDNP(): continue
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH: continue
            rect = bbox(pad)
            if intersection(rect, display_rect):
                pth.append({"ref": fp.GetReference(), "pad": pad.GetNumber(),
                            "uuid": str(pad.m_Uuid.AsString()), "bbox_mm": rect,
                            "center_mm": [mm(pad.GetPosition().x), mm(pad.GetPosition().y)],
                            "z_clearance_verified": False})
    pth.sort(key=lambda e: (e["ref"], e["center_mm"]))
    display_front = []
    for fp in sorted(boards["Display-C1"].GetFootprints(), key=lambda f: f.GetReference()):
        if fp.GetLayer() != pcbnew.F_Cu or fp.IsDNP() or fp.IsExcludedFromBOM(): continue
        rect = display_world(bbox(fp))
        display_front.append({"ref": fp.GetReference(), "world_bbox_mm": rect,
                              "overlap_battery_planning_projection": bool(intersection(rect, battery_rect)),
                              "maximum_body_height_mm": None})
    overlap = intersection(battery_rect, display_rect)
    overlap_area = (overlap[2] - overlap[0]) * (overlap[3] - overlap[1]) if overlap else 0
    core_t, display_t = [mm(boards[n].GetDesignSettings().GetBoardThickness()) for n in ("Core-C1", "Display-C1")]
    gap = contract["assembly"]["mated_board_gap_mm"]
    panel_t = inputs["panel"]["nominal_dimensions_mm"][2]
    fixed = round(core_t + gap + display_t + panel_t, 6)
    params = inputs["budget_parameters_mm"]
    missing = [name for name, value in params.items() if value is None]
    for name, value in params.items():
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError("Invalid budget parameter: " + name)
    available = None
    rear_component_extent = None
    if not missing:
        rear_component_extent = max(gap + display_t + params["display_front_max_component_height"],
                                    params["core_back_outside_display_max_component_height"])
        heights = {"core_front_max_component_height", "display_front_max_component_height",
                   "core_back_outside_display_max_component_height"}
        available = round(params["target_outer_thickness"] - core_t - panel_t
                          - params["core_front_max_component_height"] - rear_component_extent
                          - sum(value for name, value in params.items()
                                if name != "target_outer_thickness" and name not in heights), 6)
    battery_t = inputs["battery"]["maximum_assembly_thickness_mm"]
    swelling = inputs["battery"]["swelling_allowance_mm"]
    for name, value in [("maximum_assembly_thickness_mm", battery_t), ("swelling_allowance_mm", swelling)]:
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError("Invalid battery parameter: " + name)
    fits_budget = None if available is None or battery_t is None or swelling is None else battery_t + swelling <= available
    xy = inputs["enclosure_xy_study"]
    for name in ("edge_clearance_each_side_mm", "wall_each_side_mm"):
        if not isinstance(xy[name], (float, int)) or not math.isfinite(xy[name]) or xy[name] < 0:
            raise ValueError("Invalid XY study parameter: " + name)
    center = xy["panel_center_core_xy_mm"]
    panel_w, panel_h = inputs["panel"]["nominal_dimensions_mm"][:2]
    panel_rect = [round(v,6) for v in [center[0]-panel_w/2, center[1]-panel_h/2, center[0]+panel_w/2, center[1]+panel_h/2]]
    envelopes = [[0,0,96,68], display_rect, panel_rect]
    ports, mounting = [], []
    for name, board in boards.items():
        for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
            if fp.IsDNP(): continue
            native_rect = bbox(fp)
            world = display_world(native_rect) if name == "Display-C1" else native_rect
            if not fp.IsExcludedFromBOM(): envelopes.append(world)
            if fp.GetReference().startswith(("J", "SW")):
                ports.append({"board":name,"ref":fp.GetReference(),"native_center_mm":[mm(fp.GetPosition().x),mm(fp.GetPosition().y)],
                              "native_orientation_deg":fp.GetOrientationDegrees(),"world_bbox_mm":world,
                              "enclosure_opening_verified":False})
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and fp.GetReference().startswith("H"):
                    pos = [mm(pad.GetPosition().x), mm(pad.GetPosition().y)]
                    if name == "Display-C1": pos = [pos[0]+38,66-pos[1]]
                    mounting.append({"board":name,"ref":fp.GetReference(),"world_center_mm":pos,
                                     "drill_mm":[mm(pad.GetDrillSize().x),mm(pad.GetDrillSize().y)],
                                     "boss_and_fastener_envelope_verified":False})
    union = [min(e[0] for e in envelopes), min(e[1] for e in envelopes),
             max(e[2] for e in envelopes), max(e[3] for e in envelopes)]
    extra = 2*(xy["edge_clearance_each_side_mm"]+xy["wall_each_side_mm"])
    example_outer = [round(union[2]-union[0]+extra,6),round(union[3]-union[1]+extra,6)]
    battery_xy = [battery_rect[2]-battery_rect[0], battery_rect[3]-battery_rect[1]]
    battery_screens = []
    for cell in inputs["battery_candidates"]:
        dims = cell["proposed_core_xy_dimensions_mm"]
        slack = [round(battery_xy[i]-dims[i],6) for i in (0,1)]
        battery_screens.append({"manufacturer":cell["manufacturer"],"mpn":cell["mpn"],
                               "candidate_xy_mm":dims,"total_xy_slack_mm":slack,
                               "passes_example_1mm_each_side_body_only":all(v>=2 for v in slack),
                               "pcm_harness_swelling_verified":False,"battery_selected":False})
    report = {
        "schema": "panda-split-c1-mechanical-audit-v1",
        "pcb_sha256": {name: sha(path) for name, path in PCB.items()},
        "inputs_sha256": sha(inputs_path), "interface_sha256": sha(ROOT / "split-c1-interface.json"),
        "method": "Native footprint bounding-box XY screening; no verified solid model or Z-body collision test.",
        "component_gap_xy_screen_passed": True, "unexpected_gap_facing_smt": unexpected,
        "back_footprints": back, "core_pth_pads_intersecting_display": pth,
        "display_front_component_envelopes": display_front,
        "battery_display_xy_intersection_mm": overlap,
        "battery_display_xy_overlap_area_mm2": round(overlap_area, 6),
        "battery_gap_placement_rejected": any(e["ref"]=="J601" and e["overlap_battery_planning_projection"] for e in back["Core-C1"]),
        "battery_gap_rejection_reason": "The full planning battery rectangle overlaps the occupied J601/J1 mating connector region.",
        "battery_proposal": "Place behind the outward Display F.Cu component envelope, with insulation and swelling clearance; not frozen.",
        "board_planes_core_b_z_mm": {"core_b": 0, "core_f": core_t,
                                     "display_b": -gap, "display_f": round(-gap-display_t, 6)},
        "fixed_nominal_z_contribution_mm": fixed,
        "budget_formula": "T_outer = T_core + T_panel + H_core_F + max(gap + T_display + H_display_F, H_core_B_outside_Display) + panel_clearance_and_adhesive + battery_clearance_and_insulation + front_wall + rear_wall + manufacturing_tolerance_reserve + T_battery_max + swelling_allowance",
        "rear_component_extent_below_core_b_mm": rear_component_extent,
        "enclosure_xy_study": {"panel_rect_mm":panel_rect,"panel_pose_verified":False,
                               "union_of_boards_panel_and_native_footprints_mm":union,
                               "example_outer_xy_mm":example_outer,
                               "example_rounded_outer_xy_mm":[math.ceil(v) for v in example_outer],
                               "edge_clearance_each_side_mm":xy["edge_clearance_each_side_mm"],
                               "wall_each_side_mm":xy["wall_each_side_mm"],
                               "excluded_envelopes":xy["excluded_envelopes"],"released_dimensions":False},
        "native_connector_switch_envelopes":ports,"mounting_holes":mounting,
        "display_retention": "No dedicated Display mounting-hole footprint; design insulating edge supports/retention, not DF40 as sole load-bearing attachment.",
        "battery_candidate_xy_screens":battery_screens,
        "maximum_battery_plus_swelling_budget_mm": available,
        "battery_fits_parameter_budget": fits_budget, "unresolved_budget_parameters": missing,
        "nominal_budget_is_not_tolerance_signoff": True,
        "enclosure_z_stack_verified": False, "battery_stack_verified": False,
        "physical_mating_verified": False, "manufacturing_release": False,
        "open_gates": ["J201 midmount body/stakes/solder Z clearance at Display projection edge",
                       "Exact battery assembly maximum dimensions, swelling, protection PCB and harness",
                       "Supplier maximum component heights, solder/mount tolerances and PCB warp",
                       "FT01C XY pose, actual thickness tolerance, FPC contact side and bend/access envelope",
                       "Enclosure walls/supports, insulation, retention, heat and physical EVT"],
    }
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=ROOT / "split-c1-mechanical-inputs.json")
    parser.add_argument("--output", type=Path, default=ROOT / "split-c1-mechanical-audit.json")
    args = parser.parse_args()
    report = audit(args.inputs)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in [
        "component_gap_xy_screen_passed", "unexpected_gap_facing_smt",
        "core_pth_pads_intersecting_display", "battery_display_xy_overlap_area_mm2",
        "fixed_nominal_z_contribution_mm", "maximum_battery_plus_swelling_budget_mm",
        "enclosure_z_stack_verified", "manufacturing_release"]}, indent=2))

if __name__ == "__main__": main()
