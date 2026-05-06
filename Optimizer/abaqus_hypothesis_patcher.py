#!/usr/bin/env python3
"""Patch Abaqus .inp files with controlled anchor-constraint hypotheses.

This script is intentionally keyword-level so it works even when CAE model APIs are limited.
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple


HYPOTHESES: Dict[str, Dict[str, bool]] = {
    "h1_none": {"embed": False, "tie_wa": False, "tie_aj": False},
    "h2_embed": {"embed": True, "tie_wa": False, "tie_aj": False},
    "h3_tie_aj": {"embed": False, "tie_wa": False, "tie_aj": True},
    "h4_tie_wa": {"embed": False, "tie_wa": True, "tie_aj": False},
    "h5_embed_tie_aj": {"embed": True, "tie_wa": False, "tie_aj": True},
    "h6_embed_tie_wa": {"embed": True, "tie_wa": True, "tie_aj": False},
    "h7_tie_wa_tie_aj": {"embed": False, "tie_wa": True, "tie_aj": True},
    "h8_all": {"embed": True, "tie_wa": True, "tie_aj": True},
}


def parse_part_counts(lines: List[str]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.lower().startswith("*part"):
            m = re.search(r"name\s*=\s*([^,]+)", line, flags=re.IGNORECASE)
            part = m.group(1).strip() if m else "UNKNOWN"
            max_node = 0
            max_elem = 0
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                sl = s.lower()
                if sl.startswith("*end part"):
                    break
                if sl.startswith("*node"):
                    i += 1
                    while i < len(lines) and not lines[i].lstrip().startswith("*"):
                        rec = lines[i].split(",", 1)[0].strip()
                        if rec.isdigit():
                            max_node = max(max_node, int(rec))
                        i += 1
                    continue
                if sl.startswith("*element"):
                    i += 1
                    while i < len(lines) and not lines[i].lstrip().startswith("*"):
                        rec = lines[i].split(",", 1)[0].strip()
                        if rec.isdigit():
                            max_elem = max(max_elem, int(rec))
                        i += 1
                    continue
                i += 1
            counts[part] = {"max_node": max_node, "max_elem": max_elem}
        i += 1
    return counts


def parse_instances(lines: List[str]) -> Dict[str, str]:
    inst_to_part: Dict[str, str] = {}
    for line in lines:
        s = line.strip()
        if s.lower().startswith("*instance"):
            mi = re.search(r"name\s*=\s*([^,]+)", s, flags=re.IGNORECASE)
            mp = re.search(r"part\s*=\s*([^,]+)", s, flags=re.IGNORECASE)
            if mi and mp:
                inst_to_part[mi.group(1).strip()] = mp.group(1).strip()
    return inst_to_part


def find_primary_instances(inst_to_part: Dict[str, str]) -> Tuple[str, str, str]:
    wall = "Wall-1"
    joist = "Joist-1"
    anchor = ""
    for inst in inst_to_part:
        if "anchor" in inst.lower():
            anchor = inst
            break
    if not anchor:
        raise ValueError("Could not find anchor instance in assembly")
    return wall, joist, anchor


def build_assembly_inserts(
    wall_inst: str,
    joist_inst: str,
    anchor_inst: str,
    joist_nodes: int,
    wall_nodes: int,
    anchor_nodes: int,
    modes: Dict[str, bool],
) -> List[str]:
    out: List[str] = []
    out.append("** --- injected sets/surfaces for hypothesis sweep ---")
    out.append(f"*Nset, nset=JOIST_ALL, instance={joist_inst}, generate")
    out.append(f"1, {max(1, joist_nodes)}, 1")
    out.append(f"*Nset, nset=WALL_ALL, instance={wall_inst}, generate")
    out.append(f"1, {max(1, wall_nodes)}, 1")
    out.append(f"*Nset, nset=ANCHOR_ALL, instance={anchor_inst}, generate")
    out.append(f"1, {max(1, anchor_nodes)}, 1")

    out.append("*Surface, type=NODE, name=SURF_JOIST_N")
    out.append("JOIST_ALL,")
    out.append("*Surface, type=NODE, name=SURF_WALL_N")
    out.append("WALL_ALL,")
    out.append("*Surface, type=NODE, name=SURF_ANCHOR_N")
    out.append("ANCHOR_ALL,")

    if modes["embed"]:
        out.append(f"*EMBEDDED ELEMENT, HOST ELSET={wall_inst}._G2, ROUNDOFF TOLERANCE=1e-6")
        out.append(f"{anchor_inst}._G2")

    if modes["tie_wa"]:
        out.append("*Tie, name=TIE_WALL_ANCHOR, adjust=yes")
        out.append("SURF_WALL_N, SURF_ANCHOR_N")

    if modes["tie_aj"]:
        out.append("*Tie, name=TIE_ANCHOR_JOIST, adjust=yes")
        out.append("SURF_ANCHOR_N, SURF_JOIST_N")

    return out


def inject_before_end_assembly(lines: List[str], inserts: List[str]) -> List[str]:
    out: List[str] = []
    inserted = False
    for line in lines:
        if not inserted and line.strip().lower().startswith("*end assembly"):
            out.extend(i + "\n" for i in inserts)
            inserted = True
        out.append(line)
    if not inserted:
        raise ValueError("*End Assembly not found")
    return out


def inject_load(lines: List[str], force_n: float, joist_nodes: int) -> List[str]:
    out: List[str] = []
    inserted = False
    per_node = force_n / max(1, joist_nodes)
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if not inserted and lines[i].strip().startswith("** LOADS"):
            out.append("** Name: UpliftInjected Type: Concentrated force\n")
            out.append("*Cload\n")
            out.append(f"JOIST_ALL, 2, {per_node:.6f}\n")
            inserted = True
        i += 1
    if not inserted:
        # fallback: inject into step block before output requests
        tmp: List[str] = []
        inserted = False
        for line in out:
            if (not inserted) and line.strip().startswith("** OUTPUT REQUESTS"):
                tmp.append("** Name: UpliftInjected Type: Concentrated force\n")
                tmp.append("*Cload\n")
                tmp.append(f"JOIST_ALL, 2, {per_node:.6f}\n")
                inserted = True
            tmp.append(line)
        out = tmp
    return out


def sanitize(lines: List[str]) -> List[str]:
    clean: List[str] = []
    skip_next_data = False
    for line in lines:
        lower = line.strip().lower()
        if skip_next_data and (not line.lstrip().startswith("*")):
            continue
        skip_next_data = False

        if lower.startswith("*conflicts"):
            continue
        if lower.startswith("*embedded element"):
            skip_next_data = True
            continue
        clean.append(line)
    return clean


def patch_one(inp_path: Path, out_path: Path, force_n: float, hypothesis: str) -> None:
    if hypothesis not in HYPOTHESES:
        raise ValueError(f"Unknown hypothesis: {hypothesis}")
    lines = inp_path.read_text(errors="ignore").splitlines(keepends=True)
    counts = parse_part_counts([l.rstrip("\n") for l in lines])
    inst = parse_instances([l.rstrip("\n") for l in lines])
    wall_inst, joist_inst, anchor_inst = find_primary_instances(inst)

    joist_nodes = counts[inst[joist_inst]]["max_node"]
    wall_nodes = counts[inst[wall_inst]]["max_node"]
    anchor_nodes = counts[inst[anchor_inst]]["max_node"]

    inserts = build_assembly_inserts(
        wall_inst,
        joist_inst,
        anchor_inst,
        joist_nodes,
        wall_nodes,
        anchor_nodes,
        HYPOTHESES[hypothesis],
    )

    patched = sanitize(lines)
    patched = inject_before_end_assembly(patched, inserts)
    patched = inject_load(patched, force_n=force_n, joist_nodes=joist_nodes)

    out_path.write_text("".join(patched), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input .inp path")
    ap.add_argument("--output", required=True, help="Output .inp path")
    ap.add_argument("--force-n", type=float, required=True, help="Total uplift force in N")
    ap.add_argument("--hypothesis", required=True, choices=sorted(HYPOTHESES.keys()))
    args = ap.parse_args()

    patch_one(Path(args.input), Path(args.output), args.force_n, args.hypothesis)
    print(f"Patched {args.input} -> {args.output} using {args.hypothesis}")


if __name__ == "__main__":
    main()
