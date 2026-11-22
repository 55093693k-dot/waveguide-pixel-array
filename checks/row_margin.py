# -*- coding: utf-8 -*-
"""row_margin.py -- per-row decision margin, so a weak row cannot hide in an average.

Why (user, 2026-11-22): in the shared-scale figure the DESIGN-VALUE panel showed an
orange (mid-brightness) pixel around the mouth corner, and the +8.3 % panel looked
BETTER. That is possible only if the calibrated coupling length is not at the margin
optimum. This script prints, row by row, the lowest lit pixel and the highest dark
pixel for each tier, so the claim is checked instead of guessed.

Usage:  python row_margin.py smile smile_e083 [smile_e350]
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"


def art_rows(prefix):
    p = HERE.parent / "images" / (prefix + ".txt")
    if not p.exists():
        p = HERE.parent / "images" / (prefix.split("_")[0] + ".txt")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        t = "".join(c for c in line.replace(".", "0").replace("#", "1") if c in "01")
        if t:
            rows.append(t)
    return rows


def matrix(prefix):
    rows = art_rows(prefix)
    z = np.load(OUT / ("readout_%s.npz" % prefix), allow_pickle=True)
    d = {}
    for k in z.files:
        if k.startswith("v_"):
            d[int(k[2:])] = (z[k], str(z["p_" + k[2:]].tolist()))
    pat_of = {r: p for r, (v, p) in d.items()}
    M = np.full((len(rows), len(rows[0])), np.nan)
    for i, rw in enumerate(rows):
        src = i if i in d else next((r for r, p in pat_of.items()
                                     if p == str(list(rw))), None)
        if src is not None:
            M[i, :len(d[src][0])] = d[src][0]
    ideal = np.array([[int(c) for c in r] for r in rows], dtype=float)
    flips = [sum(1 for a, b in zip("0" + r, r) if a != b) for r in rows]
    return M, ideal, flips


def main(argv):
    prefixes = argv or ["smile", "smile_e083"]
    data = [matrix(p) for p in prefixes]
    M0, ideal, flips = data[0]
    nrow, npix = M0.shape

    hdr = "row flips | " + " | ".join("%-22s" % p for p in prefixes)
    print("=" * len(hdr))
    print("lowest LIT pixel (higher = better) / highest DARK pixel (lower = better)")
    print(hdr)
    print("-" * len(hdr))
    order = sorted(range(nrow), key=lambda i: np.nanmin(
        M0[i][ideal[i].astype(bool)]) if np.any(ideal[i]) else 9)
    for i in order:
        cells = []
        for (M, idl, _f) in data:
            lit = M[i][idl[i].astype(bool)]
            dark = M[i][~idl[i].astype(bool)]
            lit = lit[~np.isnan(lit)]
            dark = dark[~np.isnan(dark)]
            if lit.size == 0:
                cells.append("   (no lit pixel)    ")
                continue
            lo = float(np.nanmin(lit))
            hi = float(np.nanmax(dark)) if dark.size else float("nan")
            cells.append("lit %.3f  dark %.3f   " % (lo, hi))
        print("%3d %5d | %s" % (i, flips[i], " | ".join(cells)))
    print("-" * len(hdr))

    # global worst cases
    for p, (M, idl, _f) in zip(prefixes, data):
        ok = ~np.isnan(M)
        lit = M[idl.astype(bool) & ok]
        dark = M[(~idl.astype(bool)) & ok]
        print("%-14s  global lit_min=%.4f  dark_max=%.4f  margin=%+.4f"
              % (p, lit.min(), dark.max(), lit.min() - dark.max()))
    print("=" * len(hdr))
    print("If a LATER tier has a LARGER margin, the calibrated L_ACT is not at the")
    print("margin optimum -- state it as a fact, do not hide it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


