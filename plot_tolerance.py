"""plot_tolerance.py -- how far the critical dimension may drift.

One image is built from N exchanges. Each exchange is a half beat of coupling,
so an error in the critical dimension turns into a phase error that accumulates
along the row. This script turns that into a curve of contrast against that
error, and reads off the error at which the contrast falls to 2.

The two levels (a bright pixel and a dark pixel) and the contrast at zero error
are measured, not assumed: they come from data/readout_dino.npz. The rest is
geometry. No simulation is run here, and no claim is made that the curve
predicts a device that was not measured.

Usage
    python plot_tolerance.py
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FIG = HERE / "figures"

SENSITIVITY = 16.8        # phase error per unit strain; 16.8 per micrometre of CD error
TARGET = 2.0              # the contrast below which a row is taken to have failed
FRACTION = {18: 0.52, 24: 0.39, 30: 0.31, 36: 0.25}   # bend fraction of the pixel


def levels():
    """Bright and dark level of one pixel, from the measured image."""
    z = np.load(DATA / "readout_dino.npz")
    values, truth = z["values"], z["truth"]
    return float(values[truth == 1].mean()), float(values[truth == 0].mean())


def contrast(bright, dark, dcd_nm, n_exchanges, cell=21.0):
    """Contrast of a row that makes n_exchanges half beats, with a CD error.

    The bend fraction sets how much of the pixel is spent moving between the two
    waveguides rather than sitting in the coupling gap.
    """
    eps = (SENSITIVITY * np.asarray(dcd_nm, dtype=float) / 1000.0)[:, None]
    n = np.arange(0, n_exchanges + 1)[None, :]
    intensity = dark + (bright - dark) * np.cos(n * (np.pi / 2) * (1 + eps)) ** 2
    even, odd = (n[0] % 2 == 0), (n[0] % 2 == 1)
    lit = intensity[:, even].mean(axis=1)
    unlit = intensity[:, odd].mean(axis=1) if odd.any() else np.full(len(intensity), dark)
    f = np.interp(cell, list(FRACTION), list(FRACTION.values()))
    scale = (1 - 0.5 * f) / (0.5 * f) / 3.40
    return lit / unlit * scale


def crossing(bright, dark, n_exchanges, grid, cell=21.0):
    curve = contrast(bright, dark, grid, n_exchanges, cell=cell)
    below = np.where(curve < TARGET)[0]
    return float(grid[below[0]]) if below.size else float(grid[-1])


def main():
    bright, dark = levels()
    grid = np.linspace(0.0, 40.0, 801)

    print("bright %.3f  dark %.4f  contrast at zero error %.1f"
          % (bright, dark, bright / dark))

    ns = np.arange(2, 13)
    tol = np.array([crossing(bright, dark, int(n), grid) for n in ns])
    fit = float(np.exp(np.mean(np.log(tol * ns))))        # tolerance = fit / N
    print("tolerance at contrast %.0f: %.1f / N nanometres" % (TARGET, fit))

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4))

    ax = axes[0]
    for n, colour in zip((3, 6, 8, 10), ("#1b5e20", "#2e7d32", "#ef6c00", "#c62828")):
        ax.plot(grid, contrast(bright, dark, grid, n), color=colour, lw=1.8,
                label="%d exchanges" % n)
    ax.axhline(TARGET, color="k", ls="--", lw=1)
    ax.text(38.0, TARGET * 1.12, "contrast 2", ha="right", fontsize=8)
    ax.set_xlabel("critical-dimension error (nm)", fontsize=9)
    ax.set_ylabel("contrast", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlim(0, 40)
    ax.set_title("one row", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, lw=0.5)

    ax = axes[1]
    ax.plot(ns, tol, "o", color="#1e88e5", ms=4, label="computed")
    ax.plot(ns, fit / ns, "-", color="k", lw=1.0,
            label="%.0f / N" % fit)
    ax.set_xlabel("exchanges in the row", fontsize=9)
    ax.set_ylabel("tolerance (nm)", fontsize=9)
    ax.set_title("where contrast reaches 2", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, lw=0.5)

    fig.tight_layout()
    out = FIG / "fig5_tolerance_v2.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)

    (DATA / "tolerance.json").write_text(json.dumps({
        "bright_level": round(bright, 4),
        "dark_level": round(dark, 4),
        "contrast_at_zero_error": round(bright / dark, 2),
        "target_contrast": TARGET,
        "tolerance_nanometres_times_exchanges": round(fit, 1),
        "note": "tolerance = %.1f / (exchanges in the row), in nanometres; "
                "computed from the model above, levels measured" % fit,
    }, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

