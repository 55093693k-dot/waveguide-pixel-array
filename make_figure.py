"""make_figure.py -- one image, two states, side by side.

Every panel is a pixel map of the same image, read out of a different simulated
state. All panels share one colour scale, so a loss of contrast shows up as a
loss of contrast instead of being normalised away.

Usage
    python make_figure.py                                  # calibrated, +35 %
    python make_figure.py smile smile_e350 --out figures/fig3_degraded.png

Counts of wrong pixels belong in the caption, not in the panel title.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_image as RI                                       # noqa: E402

DATA = HERE / "data"
FIG = HERE / "figures"


def label(prefix):
    """What the run was, in a few words."""
    if prefix == "ideal":
        return "ideal"
    if "_e" in prefix:
        return "+%g %% coupling length" % (int(prefix.split("_e")[1]) / 10.0)
    return "as simulated"


def read(prefix):
    """Pixel map for one prefix. 'ideal' is the +8.3 % run, taken as reference.

    That run reads every pixel correctly and its absolute levels are the honest
    ones: light that has moved onto the straight waveguide is dimmer than the
    light entering the chip, so a hand-drawn 1.0 would be wrong.
    """
    if prefix == "ideal":
        prefix = "smile_e083"
    return DATA / ("readout_%s.npz" % prefix)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prefix", nargs="*", default=["smile", "smile_e350"])
    ap.add_argument("--image", default=str(HERE / "images" / "smile.txt"))
    ap.add_argument("--out", default=str(FIG / "fig3_degraded.png"))
    args = ap.parse_args(argv)

    rows = RI.load_image(args.image)
    truth = RI.truth_matrix(rows)

    maps, results = [], []
    for prefix in args.prefix:
        values = RI.assemble(read(prefix), rows)
        maps.append(values)
        results.append(RI.report(values, truth))
    vmax = max(0.7, max(float(np.nanpercentile(m, 99.5)) for m in maps))

    fig, axes = plt.subplots(1, len(maps), figsize=(5.6 * len(maps), 5.8))
    axes = np.atleast_1d(axes)
    for ax, values, prefix, res in zip(axes, maps, args.prefix, results):
        ax.imshow(values, cmap="inferno", vmin=0.0, vmax=vmax,
                  interpolation="nearest", aspect="equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(label(prefix), fontsize=10)
        for k in range(1, truth.shape[1]):
            ax.axhline(k - 0.5, color="0.35", lw=0.3)
            ax.axvline(k - 0.5, color="0.35", lw=0.3)
        print("%-14s %3d of %3d pixels correct, contrast %.1f"
              % (prefix, res["correct"], res["pixels"], res["contrast"]))

    fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0.0, vmax), cmap="inferno"),
                 ax=axes.tolist(), fraction=0.030, pad=0.02,
                 label="pixel value, shared scale")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

