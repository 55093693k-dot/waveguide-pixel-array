# -*- coding: utf-8 -*-
"""fig_pixels_pair.py -- pixel-map pair: IDEAL target vs a simulated degraded tier.

Figure 4 as the user wants it (2026-11-22): the PIXEL map (21 x 21 readout values),
not the near field. The left panel is the target pattern drawn directly from the
artwork (1 = bright, 0 = dark) because we define the calibrated design as the
reference; the right panel is the simulation of a large deviation. Both panels share
ONE colour scale, so the loss of contrast is visible rather than normalised away.

Usage:  python make_figure.py smile_e350
Output: figures/fig4_degraded.png
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FIG = HERE / "figures"
THRESHOLD = json.loads((HERE / "parameters.json").read_text(encoding="utf-8"))["readout"]["threshold"]


def art_rows(prefix):
    p = HERE / "images" / (prefix + ".txt")
    if not p.exists():
        p = HERE / "images" / (prefix.split("_")[0] + ".txt")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        t = "".join(c for c in line.replace(".", "0").replace("#", "1") if c in "01")
        if t:
            rows.append(t)
    return rows


def measured(prefix, rows):
    z = np.load(DATA / ("readout_%s.npz" % prefix), allow_pickle=True)
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
    return M


def label(prefix):
    if "_e" in prefix:
        tag = prefix.split("_e")[1]
        return "+%g %% coupling length" % (int(tag) / 10.0)
    return "calibrated design"


def main(argv):
    prefix = argv[0] if argv else "smile_e350"
    rows = art_rows(prefix)
    ideal = np.array([[1.0 if c == "1" else 0.0 for c in r] for r in rows])
    M = measured(prefix, rows)

    ok = ~np.isnan(M)
    thr = THRESHOLD                     # one fixed threshold, set on the calibrated design
    wrong = int(np.sum(((M > thr) != ideal.astype(bool)) & ok))
    contrast = (np.nanpercentile(M, 80) / max(np.nanpercentile(M, 20), 1e-12))

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 6.4))
    for ax, D, ttl in ((axes[0], ideal, "target"),
                       (axes[1], M, "%s" % label(prefix))):
        im = ax.imshow(D, cmap="inferno", vmin=0.0, vmax=1.0,
                       interpolation="nearest", aspect="equal")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(ttl, fontsize=11)
        for k in range(len(rows) + 1):
            ax.axhline(k - 0.5, color="0.25", lw=0.3)
            ax.axvline(k - 0.5, color="0.25", lw=0.3)
    fig.colorbar(im, ax=axes.tolist(), fraction=0.028, pad=0.02,
                 label="pixel readout value (shared scale)")
    plt.savefig(FIG / "fig4_degraded.png", dpi=150, bbox_inches="tight")
    print("written: figures/fig4_degraded.png  (wrong bits=%d of %d, contrast=%.1fx)"
          % (wrong, int(ok.sum()), contrast))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

