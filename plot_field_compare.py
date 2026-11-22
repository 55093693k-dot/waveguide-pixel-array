"""plot_field_compare.py -- the same image, at the reference length and 35 % off.

Two field maps of the same 21 by 21 image, on one colour scale, so the loss of
contrast is visible rather than normalised away. The 8.3 % run is taken as the
reference: it reads every pixel correctly and its absolute levels are the honest
ones.

Usage
    python plot_field_compare.py
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plot_field_pair as FP                                   # noqa: E402

FIG = HERE / "figures"
PANELS = (("smile_e083", "ideal"), ("smile_e350", "+35 % coupling length"))


def main():
    loaded = [FP.load(name) for name, _ in PANELS]
    vmax = float(np.percentile(loaded[0][0], 99.5))

    # The two runs describe the same device, so the waveguides sit in the same
    # places. The positions are taken from the reference run, where both members
    # of every pair are visible, and reused for the degraded one.
    _, x0, y0, rows0 = loaded[0]
    centres = FP.lanes(loaded[0][0], y0 * 1e6, len(rows0))

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 6.2))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.24, wspace=0.18)

    for ax, (name, title), (field, x, y, rows) in zip(axes, PANELS, loaded):
        x_um, y_um = x * 1e6, y * 1e6
        single = FP.display_only(field, y_um, centres)
        im = ax.imshow(single.T, origin="lower", cmap="inferno", vmin=0.0, vmax=vmax,
                       interpolation="bilinear", aspect="auto",
                       extent=[x_um[0], x_um[-1], y_um[0], len(rows) * FP.PITCH])
        ax.set_box_aspect(1)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("x (um)", fontsize=9)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("21 by 21 image\ny (um)", fontsize=9)
    print("lanes taken from the reference run: %d" % len(centres))

    bar = fig.add_axes([0.06, 0.08, 0.88, 0.020])
    fig.colorbar(im, cax=bar, orientation="horizontal", label="intensity")
    bar.tick_params(labelsize=8)

    out = FIG / "fig4_field_compare.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

