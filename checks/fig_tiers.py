# -*- coding: utf-8 -*-
"""fig_tiers.py -- side-by-side tiers on ONE shared colour scale.

Why this exists (user, 2026-11-22)
    The per-image normalised views made the 8.3 % tier look identical to the design
    value, because each panel was divided by its own peak -- which hides an 81 %
    change in the analogue values. With a SHARED scale the reader sees the same
    shape in different colours, which is the truthful picture.

Usage:  python fig_tiers.py smile smile_e083 [smile_e350]
Output: out/fig_tiers.png
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
    return M, ideal


def label(prefix):
    if "_e" in prefix:
        v = prefix.split("_e")[1]
        return "+%d.%d %%" % (int(v[0]), int(v[1:])) if len(v) > 1 else "+%s %%" % v
    return "design value"


def main(argv):
    prefixes = argv or ["smile", "smile_e083"]
    mats, ideals = [], []
    vmax = 0.0
    for p in prefixes:
        M, ideal = matrix(p)
        mats.append(M)
        ideals.append(ideal)
        vmax = max(vmax, float(np.nanmax(M)))
    print("shared vmax = %.4f (taken over all tiers)" % vmax)

    n = len(prefixes)
    fig, axes = plt.subplots(2, n, figsize=(4.2 * n, 8.4),
                             gridspec_kw={"height_ratios": [3, 1]})
    axes = np.atleast_2d(axes)
    for j, (p, M, ideal) in enumerate(zip(prefixes, mats, ideals)):
        ax = axes[0, j]
        im = ax.imshow(M, cmap="inferno", vmin=0.0, vmax=vmax,
                       interpolation="nearest", aspect="equal")
        ok = ~np.isnan(M)
        thr = 0.5 * (np.nanpercentile(M, 20) + np.nanpercentile(M, 80))
        wrong = int(np.sum(((M > thr) != ideal.astype(bool)) & ok))
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(label(p), fontsize=11)
        # histogram of the analogue values, same bins for every tier
        ax2 = axes[1, j]
        ax2.hist(M[ok].ravel(), bins=40, range=(0.0, vmax), color="0.35")
        ax2.set_xlim(0.0, vmax)
        ax2.tick_params(labelsize=8)
        ax2.set_xlabel("readout value (shared scale)", fontsize=8)
    fig.colorbar(im, ax=axes[0, :].tolist(), fraction=0.025, pad=0.02,
                 label="readout value (shared across panels)")
    fig.suptitle("figure of merit: pixel brightness", fontsize=9)
    plt.savefig(OUT / "fig_tiers.png", dpi=150, bbox_inches="tight")
    print("written: out/fig_tiers.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


