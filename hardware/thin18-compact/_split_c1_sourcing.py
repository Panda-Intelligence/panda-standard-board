#!/usr/bin/env python3
"""Apply reviewed exact-part library IDs without changing CAD geometry or MPNs."""
from pathlib import Path
import hashlib, json, re, uuid

ROOT = Path(__file__).resolve().parent

def balanced(text, start):
    depth = 0
    quoted = escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quoted:
            if escaped: escaped = False
            elif c == "\\": escaped = True
            elif c == '"': quoted = False
        elif c == '"': quoted = True
        elif c == "(": depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0: return i + 1
    raise ValueError("Unterminated CAD expression")

def blocks(text, pattern):
    pos = 0
    while True:
        match = re.search(pattern, text[pos:])
        if not match: return
        start = pos + match.start()
        end = balanced(text, start)
        yield start, end, text[start:end]
        pos = end

def property_value(block, name):
    match = re.search(r'\(property\s+' + re.escape(json.dumps(name)) + r'\s+("(?:\\.|[^"\\])*")', block)
    return json.loads(match.group(1)) if match else None

def without_properties(text):
    for start, end, _ in reversed(list(blocks(text, r"\(property\s"))):
        text = text[:start] + text[end:]
    return re.sub(r"\s+", " ", text).strip()

def geometry_digest(text):
    return hashlib.sha256(without_properties(text).encode()).hexdigest()

def patch_block(block, ref, item, pcb):
    for field in ("Manufacturer", "MPN"):
        if property_value(block, field) != item[field.lower()]:
            raise ValueError(f"{ref}: {field} differs from reviewed exact part")
    old = property_value(block, "LCSC")
    if old not in (None, "", item["library_id"]):
        raise ValueError(f"{ref}: existing library ID conflicts")
    props = list(blocks(block, r"\(property\s"))
    for start, end, prop in props:
        if property_value(prop, "LCSC") is not None:
            prop = re.sub(r'(\(property\s+"LCSC"\s+)("(?:\\.|[^"\\])*")',
                          lambda m: m.group(1) + json.dumps(item["library_id"]), prop, count=1)
            return block[:start] + prop + block[end:]
    templates = [(start, end, prop) for start, end, prop in props
                 if property_value(prop, "Datasheet") is not None]
    if not templates:
        templates = [(start, end, prop) for start, end, prop in props
                     if property_value(prop, "MPN") is not None]
    if len(templates) != 1: raise ValueError(f"{ref}: Property template missing")
    _, end, template = templates[0]
    new = re.sub(r'\(property\s+"(?:Datasheet|MPN)"\s+("(?:\\.|[^"\\])*")',
                 '(property "LCSC" ' + json.dumps(item["library_id"]), template, count=1)
    if "(hide yes)" not in new:
        if "(hide no)" in new: new = new.replace("(hide no)", "(hide yes)")
        else: new = new.replace("(effects", "(hide yes) (effects", 1)
    if pcb:
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"panda/split-c1/sourcing/{item['board']}/{ref}/LCSC"))
        new = re.sub(r'\(uuid "[^"]+"\)', '(uuid "' + uid + '")', new, count=1)
    return block[:end] + "\n" + new + block[end:]

def apply_sourcing(candidate, board_id):
    candidate = Path(candidate)
    registry = json.loads((ROOT / "split-c1-sourcing-evidence.json").read_text())
    items = {ref: item for item in registry["entries"] if item["board"] == board_id
             for ref in item["refs"]}
    if board_id == "Core-C1":
        folder = candidate / "eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16"
    elif board_id == "Display-C1": folder = candidate
    else: raise ValueError("Unknown split board")
    paths = sorted(folder.glob("*.kicad_sch")) + sorted(folder.glob("*.kicad_pcb"))
    staged, seen = [], {True: set(), False: set()}
    for path in paths:
        original = path.read_text()
        pcb = path.suffix == ".kicad_pcb"
        pattern = r"\(footprint\s" if pcb else r"\(symbol\s+\(lib_id\s"
        text = original
        for start, end, block in reversed(list(blocks(original, pattern))):
            ref = property_value(block, "Reference")
            if ref in items:
                if ref in seen[pcb]: raise ValueError(f"Duplicate {ref} in native project")
                seen[pcb].add(ref)
                text = text[:start] + patch_block(block, ref, items[ref], pcb) + text[end:]
        before, after = geometry_digest(original), geometry_digest(text)
        if before != after: raise ValueError("Sourcing patch changed non-property CAD data")
        staged.append((path, text, before))
    for pcb in (False, True):
        expected={ref for ref,item in items.items() if not pcb or not item.get("manual")}
        if seen[pcb] != expected: raise ValueError(f"Missing {'PCB' if pcb else 'schematic'} refs: {expected-seen[pcb]}")
    for path, text, _ in staged: path.write_text(text)
    report = {"schema": "panda-split-c1-sourcing-patch-v1", "board": board_id,
              "identity_verified_refs": sorted(items), "manufacturer_mpn_unchanged": True,
              "non_property_cad_digest_unchanged": True,
              "non_property_digests": {str(p.relative_to(candidate)): digest for p, _, digest in staged},
              "evidence_sha256": hashlib.sha256((ROOT / "split-c1-sourcing-evidence.json").read_bytes()).hexdigest(),
              "stock_reserved": False, "manufacturing_release": False}
    (candidate / "sourcing-patch-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--board", choices=["Core-C1", "Display-C1"], required=True)
    args = parser.parse_args()
    report = apply_sourcing(args.candidate.resolve(), args.board)
    print(json.dumps({"board": args.board, "refs": len(report["identity_verified_refs"]),
                      "non_property_cad_digest_unchanged": True}, indent=2))
