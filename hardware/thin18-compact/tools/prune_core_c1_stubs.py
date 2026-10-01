#!/usr/bin/env python3
"""Remove only native-reported copper stubs left by the display-slice ECO."""
from pathlib import Path
import argparse, json, re, subprocess

KICAD = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
ALLOWED = {"GND", "3V3_EPD_LOGIC"} | {f"EPD_D{i}" for i in range(6)}

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
    raise ValueError("unterminated KiCad expression")

def blocks(text, token):
    pos = 0
    while True:
        start = text.find(token, pos)
        if start < 0: return
        if not token[-1].isspace() and text[start+len(token)] not in " \t\r\n(":
            pos = start + len(token)
            continue
        end = balanced(text, start)
        yield start, end, text[start:end]
        pos = end

def remove_uuids(text, ids):
    removed = []
    spans = []
    for token in ["(segment", "(via"]:
        for start, end, block in blocks(text, token):
            uid = re.search(r'\(uuid "([^"]+)"\)', block)
            if uid and uid[1] in ids:
                net = re.search(r'\(net "([^"]+)"\)', block)
                if not net or net[1] not in ALLOWED:
                    raise ValueError("refusing unrelated copper removal")
                removed.append({"uuid": uid[1], "net": net[1]})
                spans.append((start, end))
    if {x["uuid"] for x in removed} != ids:
        raise ValueError("DRC UUIDs did not resolve to allowed copper")
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + text[end:]
    return text, removed

def prune(pcb, report):
    removed = []
    pending = None
    for iteration in range(100):
        subprocess.run([KICAD, "pcb", "drc", "--format", "json",
            "--severity-all", "--schematic-parity", "--output",
            str(report), str(pcb)], check=True, stdout=subprocess.DEVNULL)
        d = json.loads(report.read_text())
        if pending and len(d["unconnected_items"]) > pending[2]:
            pcb.write_text(pending[0])
            del removed[pending[1]:]
            subprocess.run([KICAD, "pcb", "drc", "--format", "json",
                "--severity-all", "--schematic-parity", "--output",
                str(report), str(pcb)], check=True, capture_output=True)
            raise ValueError("leaf removal would disconnect branched copper; restored previous board; split junctions first")
        stubs = [v for v in d["violations"]
                 if v["type"] in {"track_dangling", "via_dangling"}]
        ids = {i["uuid"] for v in stubs for i in v["items"]}
        print(json.dumps({"prune_iteration": iteration,
            "violations": len(d["violations"]),
            "open": len(d["unconnected_items"]), "stubs": len(ids)}),
            flush=True)
        if not ids: break
        original = pcb.read_text()
        pending = (original, len(removed), len(d["unconnected_items"]))
        text, deleted = remove_uuids(original, ids)
        pcb.write_text(text)
        removed.extend(deleted)
    else: raise ValueError("stub cleanup did not converge")
    return removed

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pcb", type=Path)
    ap.add_argument("verification", type=Path)
    a = ap.parse_args()
    a.verification.mkdir(parents=True, exist_ok=True)
    removed = prune(a.pcb, a.verification / "drc.json")
    p = a.verification / "removed-adapter-copper.json"
    prior = json.loads(p.read_text()) if p.exists() else []
    p.write_text(json.dumps(prior + removed, indent=2) + "\n")
    print("removed copper:", len(removed))
