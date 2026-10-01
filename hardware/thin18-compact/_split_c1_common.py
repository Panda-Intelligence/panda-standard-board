#!/usr/bin/env python3
"""Portable KiCad discovery and minimal replay inputs from immutable Git history."""
from pathlib import Path
import hashlib, os, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
BASELINE_COMMIT = "60de7135de31d4e49fd8351565e4e34d60a4af96"
BASELINE_PATH = "hardware/thin18-compact/c4d20-96x68-production-bom"
REL = Path("eda/core/PANDA-STD-CORE-EVT/PANDA-THIN16")
STEM = "PANDA-STD-CORE-EVT-quilter-j501-merged"

def discover(env, executable, mac):
    selected = os.environ.get(env) or shutil.which(executable)
    if selected:
        return selected
    if Path(mac).is_file():
        return mac
    raise RuntimeError(f"Set {env} to the installed {executable}")

def kicad_cli():
    return discover("KICAD_CLI", "kicad-cli", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

def kicad_python():
    selected = os.environ.get("KICAD_PYTHON")
    if selected:
        return selected
    mac = Path("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3")
    return str(mac) if mac.is_file() else sys.executable

def git_bytes(path):
    try:
        return subprocess.check_output(["git", "show", f"{BASELINE_COMMIT}:{BASELINE_PATH}/{path}"], cwd=REPO, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Replay baseline {BASELINE_COMMIT} is missing; retrieve the original PR history with: git fetch origin refs/pull/7/head") from exc

def native_input(path):
    return (path.suffix in {".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_sym", ".kicad_mod"}
            or path.name in {"fp-lib-table", "sym-lib-table", "circuit-contract.json", "frontlight-firmware-contract.json"}
            or (path.parent.name == "models" and path.name in {"README.md", "LICENSE.txt"}))

def copy_baseline(target, subpath=""):
    prefix = BASELINE_PATH + ("/" + subpath if subpath else "") + "/"
    try:
        names = subprocess.check_output(["git", "ls-tree", "-rz", "--name-only", BASELINE_COMMIT, "--", prefix], cwd=REPO).decode().split("\0")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Replay needs the immutable baseline in Git history") from exc
    selected = []
    for name in names:
        if not name:
            continue
        relative = Path(name[len(prefix):])
        if not subpath and relative.parts[0] == "display":
            continue
        if native_input(relative):
            selected.append((name, relative))
    if not selected:
        raise RuntimeError("Replay baseline contains no native CAD inputs")
    target.mkdir(parents=True)
    for name, relative in selected:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(git_bytes(str(Path(name).relative_to(BASELINE_PATH))))
    return len(selected)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def repo_entry(path):
    relative = path.resolve().relative_to(REPO.resolve())
    return {"path": relative.as_posix(), "sha256": sha(path)}
