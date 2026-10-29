#!/usr/bin/env python3
"""Verify and export JLCPCB / JLC EDA (嘉立创) free-coupon compliance for Panda47 Core & Display.

Checks the three customer coupon requirements:
1. Complete EDA design (.kicad_pro/.kicad_sch/.kicad_pcb), dimensions within 10x10cm (<=100x100mm)
   and >=1x1cm (>=10x10mm), 5 pcs single-board delivery (单片出货，不做拼版: 1 closed Edge.Cuts loop),
   standard 4-layer process (常规工艺), and 4-layer green solder mask only (四层板仅支持绿油).
2. Coupon type compatibility: PCB+SMT (exports BOM_JLCPCB.csv & CPL_JLCPCB.csv), EDA ENIG coupon
   (沉金券: copper_finish ENIG, exposed solder-mask opening area < 20% of board area), or OSP coupon.
3. Open-source anti-split-order uniqueness (防拆单问题: unique project/revision identifiers and
   unique Gerber/GBRJOB hash generation so the package does not collide with public open-source uploads).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

KCLI_DEFAULT = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KPY_DEFAULT = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"


def polygon_area(pts: list[tuple[float, float]]) -> float:
    if len(pts) < 3:
        return 0.0
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def trace_single_closed_outline(segments: list[tuple[tuple[float, float], tuple[float, float]]], tol: float = 1e-3) -> list[tuple[float, float]]:
    """Verify that Edge.Cuts segments form a single closed simple loop (no panelization/V-cuts)."""
    if len(segments) < 3:
        raise ValueError(f"Expected >= 3 Edge.Cuts segments, got {len(segments)}")
    unused = list(segments)
    loop = [unused.pop(0)[0], segments[0][1]]
    while unused:
        cur = loop[-1]
        found = None
        for idx, (a, b) in enumerate(unused):
            if math.hypot(cur[0] - a[0], cur[1] - a[1]) <= tol:
                found = (idx, b)
                break
            if math.hypot(cur[0] - b[0], cur[1] - b[1]) <= tol:
                found = (idx, a)
                break
        if found is None:
            raise ValueError("Edge.Cuts segments do not form a single contiguous loop (panelization or disjoint cuts detected)")
        idx, nxt = found
        unused.pop(idx)
        if unused:
            loop.append(nxt)
        else:
            if math.hypot(nxt[0] - loop[0][0], nxt[1] - loop[0][1]) > tol:
                raise ValueError("Edge.Cuts loop is not closed")
    return loop


def parse_stackup_policy(pcb_text: str) -> dict:
    has_stackup = "(stackup" in pcb_text
    f_mask_green = bool(re.search(r'\(layer\s+"F\.Mask".*?\(color\s+"Green"\)', pcb_text, re.S))
    b_mask_green = bool(re.search(r'\(layer\s+"B\.Mask".*?\(color\s+"Green"\)', pcb_text, re.S))
    finish_m = re.search(r'\(copper_finish\s+"([^"]+)"\)', pcb_text)
    finish = finish_m.group(1) if finish_m else None
    rev_m = re.search(r'\(title_block.*?\(rev\s+"([^"]+)"\)', pcb_text, re.S)
    comment2_m = re.search(r'\(title_block.*?\(comment\s+2\s+"([^"]+)"\)', pcb_text, re.S)
    return {
        "has_explicit_stackup": has_stackup,
        "f_mask_green": f_mask_green,
        "b_mask_green": b_mask_green,
        "four_layer_green_mask_compliant": has_stackup and f_mask_green and b_mask_green,
        "copper_finish": finish,
        "enig_or_osp_ready": finish in {"ENIG", "OSP"},
        "revision": rev_m.group(1) if rev_m else "",
        "unique_build_comment": comment2_m.group(1) if comment2_m else "",
    }


def inspect_board_native(candidate_dir: Path, board_name: str) -> dict:
    import pcbnew

    pcb_path = candidate_dir / f"{board_name}.kicad_pcb"
    sch_path = candidate_dir / f"{board_name}.kicad_sch"
    pro_path = candidate_dir / f"{board_name}.kicad_pro"
    for p in (pcb_path, sch_path, pro_path):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required EDA file: {p}")

    pcb_text = pcb_path.read_text()
    stackup = parse_stackup_policy(pcb_text)

    b = pcbnew.LoadBoard(str(pcb_path))
    to_mm = pcbnew.ToMM

    edge_segs = []
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            s = d.GetStart()
            e = d.GetEnd()
            edge_segs.append(((round(to_mm(s.x), 4), round(to_mm(s.y), 4)), (round(to_mm(e.x), 4), round(to_mm(e.y), 4))))

    loop = trace_single_closed_outline(edge_segs)
    xs = [pt[0] for pt in loop]
    ys = [pt[1] for pt in loop]
    width_mm = round(max(xs) - min(xs), 4)
    height_mm = round(max(ys) - min(ys), 4)
    bbox_area_mm2 = round(width_mm * height_mm, 2)
    poly_area_mm2 = round(polygon_area(loop), 2)

    # Exposed solder-mask opening area (F.Mask + B.Mask)
    f_mask_area = 0.0
    b_mask_area = 0.0
    smt_part_count = 0
    for fp in b.GetFootprints():
        if not (fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES) and not fp.IsDNP():
            smt_part_count += 1
        for pad in fp.Pads():
            sx, sy = to_mm(pad.GetSize().x), to_mm(pad.GetSize().y)
            shape = pad.GetShape()
            if shape in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_OVAL) and abs(sx - sy) < 1e-4:
                a = math.pi * (sx / 2.0) ** 2
            else:
                a = sx * sy
            lset = pad.GetLayerSet()
            if lset.Contains(pcbnew.F_Mask):
                f_mask_area += a
            if lset.Contains(pcbnew.B_Mask):
                b_mask_area += a

    total_exposed_mm2 = round(f_mask_area + b_mask_area, 2)
    enig_ratio_single_side_bbox_pct = round(total_exposed_mm2 / bbox_area_mm2 * 100.0, 2)
    enig_ratio_two_side_bbox_pct = round(total_exposed_mm2 / (2.0 * bbox_area_mm2) * 100.0, 2)
    enig_ratio_single_side_poly_pct = round(total_exposed_mm2 / poly_area_mm2 * 100.0, 2)
    enig_ratio_two_side_poly_pct = round(total_exposed_mm2 / (2.0 * poly_area_mm2) * 100.0, 2)

    min_track_mm = min(
        (round(to_mm(t.GetWidth()), 4) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"),
        default=0.0,
    )
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    min_via_dia_mm = min((round(to_mm(v.GetWidth(pcbnew.F_Cu)), 4) for v in vias), default=0.0)
    min_via_drill_mm = min((round(to_mm(v.GetDrill()), 4) for v in vias), default=0.0)
    non_through_vias = sum(1 for v in vias if v.GetViaType() != pcbnew.VIATYPE_THROUGH)

    size_ok = (10.0 <= width_mm <= 100.0) and (10.0 <= height_mm <= 100.0)
    process_ok = (
        b.GetCopperLayerCount() == 4
        and min_track_mm >= 0.09
        and min_via_drill_mm >= 0.15
        and min_via_dia_mm >= 0.25
        and non_through_vias == 0
    )
    enig_ok = enig_ratio_single_side_poly_pct < 20.0 and enig_ratio_single_side_bbox_pct < 20.0
    anti_split_ok = bool(stackup["revision"]) and ("Unique Build ID:" in stackup["unique_build_comment"])

    return {
        "board": board_name,
        "pcb_sha256": hashlib.sha256(pcb_path.read_bytes()).hexdigest(),
        "sch_sha256": hashlib.sha256(sch_path.read_bytes()).hexdigest(),
        "copper_layers": b.GetCopperLayerCount(),
        "width_mm": width_mm,
        "height_mm": height_mm,
        "width_cm": round(width_mm / 10.0, 3),
        "height_cm": round(height_mm / 10.0, 3),
        "within_10x10cm_and_ge_1x1cm": size_ok,
        "single_board_no_panelization": True,
        "edge_cuts_segment_count": len(edge_segs),
        "bbox_area_mm2": bbox_area_mm2,
        "polygon_area_mm2": poly_area_mm2,
        "min_track_width_mm": min_track_mm,
        "min_via_diameter_mm": min_via_dia_mm,
        "min_via_drill_mm": min_via_drill_mm,
        "blind_or_buried_vias": non_through_vias,
        "standard_process_compliant": process_ok,
        "stackup": stackup,
        "f_mask_opening_area_mm2": round(f_mask_area, 2),
        "b_mask_opening_area_mm2": round(b_mask_area, 2),
        "total_exposed_gold_area_mm2": total_exposed_mm2,
        "enig_gold_ratio_single_side_bbox_pct": enig_ratio_single_side_bbox_pct,
        "enig_gold_ratio_two_side_bbox_pct": enig_ratio_two_side_bbox_pct,
        "enig_gold_ratio_single_side_poly_pct": enig_ratio_single_side_poly_pct,
        "enig_gold_ratio_two_side_poly_pct": enig_ratio_two_side_poly_pct,
        "enig_under_20pct_compliant": enig_ok,
        "smt_placeable_component_count": smt_part_count,
        "anti_split_order_unique_metadata": anti_split_ok,
        "all_jlc_coupon_checks_passed": (
            size_ok
            and process_ok
            and stackup["four_layer_green_mask_compliant"]
            and stackup["enig_or_osp_ready"]
            and enig_ok
            and anti_split_ok
        ),
    }


def get_candidate_boards(candidate_dir: Path) -> list[str]:
    candidate_dir = Path(candidate_dir).resolve()
    boards = []
    if (candidate_dir / "Single.kicad_pcb").is_file():
        boards.append("Single")
    if (candidate_dir / "Core.kicad_pcb").is_file() and (candidate_dir / "Display.kicad_pcb").is_file():
        boards.extend(["Core", "Display"])
    elif not boards:
        boards = ["Core", "Display"]
    return boards


def export_jlc_orderpack(candidate_dir: Path, orderpack_dir: Path, kcli: str = KCLI_DEFAULT) -> dict:
    """Export single-board JLC Gerbers, Excellon drills, .gbrjob, ZIPs, BOM_JLCPCB.csv, and CPL_JLCPCB.csv."""
    import pcbnew

    if orderpack_dir.exists():
        shutil.rmtree(orderpack_dir)
    orderpack_dir.mkdir(parents=True)

    boards = get_candidate_boards(candidate_dir)
    exports = {}
    for board_name in boards:
        pcb_path = candidate_dir / f"{board_name}.kicad_pcb"
        bdir = orderpack_dir / board_name
        gbr_dir = bdir / "gerber"
        gbr_dir.mkdir(parents=True)

        subprocess.run(
            [
                kcli,
                "pcb",
                "export",
                "gerbers",
                "--layers",
                "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
                "--no-protel-ext",
                "--output",
                str(gbr_dir) + "/",
                str(pcb_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                kcli,
                "pcb",
                "export",
                "drill",
                "--format",
                "excellon",
                "--excellon-units",
                "mm",
                "--generate-map",
                "--map-format",
                "gerberx2",
                "--output",
                str(gbr_dir) + "/",
                str(pcb_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Stamp unique ProjectId in .gbrjob so JLCPCB order hash is uniquely tied to this build
        gbrjob_path = gbr_dir / f"{board_name}-job.gbrjob"
        if gbrjob_path.is_file():
            job = json.loads(gbrjob_path.read_text())
            job.setdefault("Header", {})["ProjectId"] = {
                "Name": f"Panda47-{board_name}-SingleBoard-10x10cm",
                "GUID": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"panda47.{board_name.lower()}.20261029.7684f0cc")),
                "Revision": f"E02-R25-JLC10X10-{board_name.upper()}-20261029",
            }
            gbrjob_path.write_text(json.dumps(job, indent=2) + "\n")

        # Create JLCPCB Gerber ZIP
        zip_path = bdir / f"JLCPCB_{board_name}_Gerber_4L_Green_ENIG.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(gbr_dir.iterdir()):
                if f.is_file():
                    zf.write(f, arcname=f.name)

        # Export JLCPCB BOM & CPL CSVs
        b = pcbnew.LoadBoard(str(pcb_path))
        to_mm = pcbnew.ToMM
        cpl_path = bdir / f"CPL_JLCPCB_{board_name}.csv"
        bom_path = bdir / f"BOM_JLCPCB_{board_name}.csv"

        bom_groups: dict[tuple[str, str, str], list[str]] = {}
        with cpl_path.open("w", newline="", encoding="utf-8") as cf:
            cw = csv.writer(cf)
            cw.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
                ref = fp.GetReference()
                if fp.IsDNP() or (fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES):
                    continue
                pos = fp.GetPosition()
                x_mm = round(to_mm(pos.x), 4)
                y_mm = round(-to_mm(pos.y), 4)  # JLCPCB bottom-left / inverted Y convention
                layer_str = "Bottom" if fp.IsFlipped() else "Top"
                rot = round(fp.GetOrientationDegrees() % 360.0, 2)
                cw.writerow([ref, f"{x_mm}mm", f"{y_mm}mm", layer_str, rot])

                if not (fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM):
                    val = fp.GetValue()
                    fpid = fp.GetFPIDAsString().split(":")[-1]
                    fields = {fld.GetName(): fld.GetText() for fld in fp.GetFields()}
                    lcsc = fields.get("LCSC", "").strip()
                    bom_groups.setdefault((val, fpid, lcsc), []).append(ref)

        with bom_path.open("w", newline="", encoding="utf-8") as bf:
            bw = csv.writer(bf)
            bw.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for (val, fpid, lcsc), refs in sorted(bom_groups.items()):
                bw.writerow([val, ",".join(refs), fpid, lcsc])

        exports[board_name] = {
            "gerber_zip": str(zip_path),
            "gerber_zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "bom_csv": str(bom_path),
            "cpl_csv": str(cpl_path),
        }
    return exports


def verify_candidate(candidate_dir: Path, orderpack_dir: Path | None = None) -> dict:
    candidate_dir = Path(candidate_dir).resolve()
    board_names = get_candidate_boards(candidate_dir)
    boards = {name: inspect_board_native(candidate_dir, name) for name in board_names}

    req1 = all(
        b["within_10x10cm_and_ge_1x1cm"]
        and b["single_board_no_panelization"]
        and b["standard_process_compliant"]
        and b["stackup"]["four_layer_green_mask_compliant"]
        for b in boards.values()
    )
    req2 = all(
        b["stackup"]["enig_or_osp_ready"]
        and b["enig_under_20pct_compliant"]
        for b in boards.values()
    )
    pcb_shas = [b["pcb_sha256"] for b in boards.values()]
    req3 = all(b["anti_split_order_unique_metadata"] for b in boards.values()) and (len(pcb_shas) == len(set(pcb_shas)))

    result = {
        "schema": "panda47-jlc-coupon-compliance-v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requirements_checked": {
            "1_complete_eda_10x10cm_5pcs_single_board_4L_green_mask": req1,
            "2_pcb_smt_enig_under_20pct_or_osp_coupon": req2,
            "3_anti_split_order_unique_files": req3,
        },
        "boards": boards,
        "all_passed": all(b["all_jlc_coupon_checks_passed"] for b in boards.values()) and req1 and req2 and req3,
    }
    if orderpack_dir is not None:
        result["orderpack"] = export_jlc_orderpack(candidate_dir, Path(orderpack_dir).resolve())
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, required=True, help="Path to engineering-candidate directory")
    ap.add_argument("--export-orderpack", type=Path, help="Optional path to export JLCPCB Gerber/Drill/BOM/CPL pack")
    ap.add_argument("--output", type=Path, help="Optional path to write compliance JSON report")
    args = ap.parse_args()
    res = verify_candidate(args.candidate, args.export_orderpack)
    if args.output:
        args.output.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res["all_passed"]:
        raise SystemExit(1)
