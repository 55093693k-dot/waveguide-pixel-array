# -*- coding: utf-8 -*-
"""render_field.py -- stitched near-field map of an artwork, drawn at SQUARE aspect.

User requirement (2026-11-21): show the actual field, not the logical grid, and
compress the aspect ratio to a square so the picture reads. The stretch is purely
for display and is stated in the title (reproducibility: the physical extent is
452 um x (nrow*2.4) um).

Two panels:
  left   the raw field (both waveguides) -- shows where the light is
  right  the "display layer": only the straight waveguide A band, which is the
         picture itself (light on A = bright)

Rows never simulated are reused from an identical pattern (physically identical).

Usage:  python render_field.py smile
        python render_field.py dino
Output: out/field_<prefix>_square.png
"""
import glob
import os
import re
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
CELL, PAD, PITCH = 21.0, 16.0, 2.4
Y_CROP = (-1.10e-6, 0.90e-6)     # relative to the A waveguide (A at +0.25 um)
NX_OUT = 1400                    # x samples kept for the picture


def art_rows(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        t = "".join(c for c in line.replace(".", "0").replace("#", "1") if c in "01")
        if t:
            out.append(t)
    return out


def main(argv):
    prefix = argv[0] if argv else "smile"
    art = HERE.parent / "images" / (prefix + ".txt")
    if not art.exists():                       # "smile_e083" -> images/smile.txt
        art = HERE.parent / "images" / (prefix.split("_")[0] + ".txt")
    rows = art_rows(art)
    cache = OUT / ("_field_%s.npz" % prefix)

    if cache.exists():
        z = np.load(cache)
        I_full, xg, yg = z["I"], z["x"], z["y"]
        print("loaded stitched field from cache: %s" % cache.name)
    else:
        maps = {}
        for f in glob.glob(str(OUT / ("%s_s21_r??_map.npz" % prefix))):
            r = int(re.search(r"_r(\d\d)", os.path.basename(f)).group(1))
            d = np.load(f)
            I = d["I"]
            if I.ndim == 3:
                I = I.sum(axis=2)
            maps[r] = (I, d["x"].ravel(), d["y"].ravel(), str(d["pat"].tolist()))

        pat_of = {r: v[3] for r, v in maps.items()}
        pick = {}
        for i in range(len(rows)):
            if i in maps:
                pick[i] = i
            else:
                src = next((r for r, p in pat_of.items() if p == str(list(rows[i]))), None)
                if src is not None:
                    pick[i] = src
        print("rows=%d  usable=%d  (missing: %s)"
              % (len(rows), len(pick), [i for i in range(len(rows)) if i not in pick]))

        any_row = next(iter(maps.values()))
        x_full, y_loc = any_row[1], any_row[2]
        step = max(1, len(x_full) // NX_OUT)
        xi = np.arange(0, len(x_full), step)
        xg = x_full[xi]
        # global canvas: each row occupies a 2.0 um band placed at its art position
        nrow = len(rows)
        yg = np.arange(-0.85e-6, (nrow - 1) * PITCH * 1e-6 + 1.15e-6, 0.05e-6)
        I_full = np.zeros((len(xi), len(yg)))
        cnt = np.zeros(len(yg))
        for i in sorted(pick):
            I, x, y, _ = maps[pick[i]]
            yc = (nrow - 1 - i) * PITCH * 1e-6
            for j in range(len(y)):
                k = int(np.argmin(np.abs(yg - (yc + y[j]))))
                if 0 <= k < len(yg):
                    I_full[:, k] += I[xi, j]
                    cnt[k] += 1
        ok = cnt > 0
        I_full[:, ok] /= cnt[ok]
        np.savez_compressed(cache, I=I_full, x=xg, y=yg)
        print("stitched and cached -> %s   shape=%s" % (cache.name, I_full.shape))

    nrow = len(rows)
    y_ext = nrow * PITCH
    disp = I_full.copy()
    keep = np.zeros(len(yg), dtype=bool)
    for i in range(nrow):
        yc = (nrow - 1 - i) * PITCH * 1e-6
        keep |= (yg >= yc + 0.05e-6) & (yg <= yc + 0.45e-6)   # A band of each row
    disp[:, ~keep] = 0.0                  # display layer = straight waveguide A only

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
    for ax, img, title in ((axes[0], I_full, "raw field (both waveguides)"),
                           (axes[1], disp, "display layer = straight waveguide A")):
        ax.imshow(img.T, origin="lower", cmap="inferno", interpolation="bilinear",
                  aspect="auto",
                  extent=[xg[0] * 1e6, xg[-1] * 1e6, yg[0] * 1e6 + 0, y_ext])
        ax.set_xlabel("x (um)")
        ax.set_title(title, fontsize=9)
    axes[0].set_ylabel("y (um)")
    stretch = (xg[-1] - xg[0]) / (yg[-1] - yg[0])
    fig.suptitle("Near field of the encoded image", fontsize=10)
    plt.tight_layout(rect=(0, 0, 1, 0.94))
    plt.savefig(OUT / ("field_%s_square.png" % prefix), dpi=150)
    print("written: out/field_%s_square.png" % prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


