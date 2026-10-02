#!/usr/bin/env python3
"""Check native split-board XY occupancy and calculate a parameterized Z budget.

Bounding boxes are conservative 2D footprint envelopes, not solid body models.
This check never signs off the enclosure, battery, or physical mating.
"""
from pathlib import Path
import argparse, hashlib, json, math, re
from _split_c1_sourcing import blocks, property_value
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
    identities = {name: {property_value(fp, "Reference"): property_value(fp, "MPN")
                         for _, _, fp in blocks(path.read_text(), r"\(footprint\s")}
                  for name, path in PCB.items()}
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
    reference = inputs.get("reference_benchmark")
    reference_screen = None
    runtime_budget = None
    if reference is not None:
        reference_dims = reference["published_body_dimensions_mm"]
        if len(reference_dims) != 3 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in reference_dims):
            raise ValueError("Invalid reference body dimensions")
        capacity = reference["published_battery_capacity_mah"]
        if not isinstance(capacity, (int, float)) or not math.isfinite(capacity) or capacity <= 0:
            raise ValueError("Invalid reference battery capacity")
        candidate_z = []
        for cell in inputs["battery_candidates"]:
            maximum = cell.get("body_maximum_l_w_t_mm")
            nominal = cell.get("body_nominal_l_w_t_mm")
            thickness = (maximum or nominal)[2]
            subtotal = round(fixed + thickness, 6)
            candidate_z.append({"manufacturer": cell["manufacturer"], "mpn": cell["mpn"],
                                "published_battery_thickness_mm": thickness,
                                "thickness_basis": "published cell maximum; excludes added PCM/harness" if maximum else "published nominal pack thickness; maximum tolerance unknown",
                                "fixed_plus_published_battery_thickness_mm": subtotal,
                                "exceeds_reference_thickness_before_other_terms": subtotal > reference_dims[2],
                                "nominal_capacity_delta_from_reference_mah": cell["capacity_nominal_mah"] - capacity,
                                "selected": False})
        component_z = []
        for item in inputs.get("published_component_height_screens", []):
            board_name = item["board"]
            footprint = next(f for f in boards[board_name].GetFootprints() if f.GetReference() == item["ref"])
            if identities[board_name].get(item["ref"]) != item["mpn"] or footprint.GetLayer() != pcbnew.F_Cu:
                raise ValueError("Published-height identity or layer mismatch: " + item["ref"])
            height = item["height_nominal_mm"]
            if not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0:
                raise ValueError("Invalid published component height")
            world = bbox(footprint)
            if board_name == "Display-C1": world = display_world(world)
            panel_overlap = intersection(world, panel_rect)
            shared_overlap = intersection(panel_overlap, display_rect) if panel_overlap else None
            subtotal = round(fixed + height, 6) if shared_overlap else None
            component_z.append({"board": board_name, "ref": item["ref"], "mpn": item["mpn"],
                                "world_native_bbox_mm": world, "shared_panel_core_display_xy_screen_mm": shared_overlap,
                                "published_height_nominal_mm": height,
                                "height_basis": item.get("height_basis", "published nominal height; maximum mounted height unverified"),
                                "source_locator": item.get("source_locator"),
                                "nominal_overlap_section_screen_without_battery_walls_mm": subtotal,
                                "exceeds_reference_in_nominal_xy_screen": None if subtotal is None else subtotal > reference_dims[2],
                                "method": "Conservative native footprint bbox plus published height; exact solid-body and mounting tolerances remain open.",
                                "source_url": item["source_url"], "physical_fit_verified": False})
        reference_screen = {"model": reference["model"],
                            "published_body_dimensions_mm": reference_dims,
                            "published_battery_capacity_mah": capacity,
                            "fixed_nominal_z_mm": fixed,
                            "remaining_for_battery_components_walls_and_all_allowances_mm": round(reference_dims[2] - fixed, 6),
                            "remaining_budget_is_optimistic_not_a_fit_signoff": True,
                            "example_outer_xy_minus_reference_xy_mm": [round(example_outer[i]-reference_dims[i], 6) for i in (0,1)],
                            "battery_candidate_z_screens": candidate_z,
                            "published_component_overlap_z_screens": component_z,
                            "architecture_action": "Current DF40 overlap stack and studied 5mm-class batteries do not support a 5.95mm case. A two-board mechanical/interconnect ECO must precede any claim of matching the reference.",
                            "reference_goal_verified": False}
        planning = inputs["runtime_planning"]
        fraction, basis = planning["usable_capacity_fraction"], planning["capacity_basis_mah"]
        if not isinstance(fraction, (int, float)) or not math.isfinite(fraction) or not 0 < fraction <= 1:
            raise ValueError("Invalid usable-capacity fraction")
        if not isinstance(basis, (int, float)) or not math.isfinite(basis) or basis <= 0:
            raise ValueError("Invalid runtime capacity basis")
        usable = basis * fraction
        sensitivity = []
        for current in planning["total_battery_current_sensitivity_ma"]:
            if not isinstance(current, (int, float)) or not math.isfinite(current) or current <= 0:
                raise ValueError("Invalid total battery current")
            sensitivity.append({"total_battery_current_ma": current, "calculated_runtime_h": round(usable/current, 6)})
        runtime_budget = {"capacity_basis_mah": basis, "usable_capacity_fraction": fraction,
                          "illustrative_usable_capacity_mah": round(usable, 6),
                          "battery_current_sensitivity": sensitivity,
                          "assumption_status": planning["usable_capacity_fraction_status"],
                          "current_measurement_basis": planning["current_measurement_basis"],
                          "runtime_target_hours": planning["runtime_target_hours"],
                          "target_policy": planning["target_policy"],
                          "is_physical_measurement": False, "is_x4_pro_runtime_claim": False}
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
        "reference_benchmark_screen": reference_screen, "runtime_design_budget": runtime_budget,
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
