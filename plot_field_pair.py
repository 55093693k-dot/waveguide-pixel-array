"""plot_field_pair.py -- the near field of two different images.

Two rows, one per image. Left column: the whole field, both waveguides. Right
column: only the straight waveguide, which is where the image sits. All four
panels share one colour scale.

Usage
    python plot_field_pair.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_image as RI                                       # noqa: E402
P = json.loads((HERE / "parameters.json").read_text(encoding="utf-8"))
PITCH = P["pixel"]["row_pitch_um"]
CELL = P["pixel"]["total_um"]
DATA = HERE / "data"
FIG = HERE / "figures"

IMAGES = ("dino", "smile")
FILES = {"dino": "example.txt", "smile": "smile.txt"}


def load(name):
    z = np.load(DATA / ("field_%s.npz" % name))
    rows = [ln.strip() for ln in (HERE / "images" / FILES[name])
            .read_text(encoding="utf-8").splitlines() if ln.strip()]
    return z["I"], z["x"], z["y"], rows


def lanes(field, y_um, n_rows):
    """Where the display waveguide of each row sits, found from the data.

    The assembled field is stitched from per-row runs, so the row grid carries a
    small offset. Rather than assume where a row is, take the highest peak of the
    mean profile inside that row's neighbourhood: the straight waveguide is
    always the upper member of the pair.
    """
    profile = field.mean(axis=0)
    found = []
    for i in range(n_rows):
        guess = (n_rows - 1 - i) * PITCH
        band = (y_um >= guess - 1.8) & (y_um <= guess + 1.2)
        yy, ss = y_um[band], profile[band]
        peaks = [j for j in range(1, len(ss) - 1)
                 if ss[j] >= ss[j - 1] and ss[j] >= ss[j + 1] and ss[j] > 0.05]
        found.append(float(yy[max(peaks)]) if peaks else guess + 0.45)
    return found


def display_only(field, y_um, centres):
    """Keep the straight waveguide of every row; drop the rest."""
    out = np.array(field, copy=True)
    keep = np.zeros(len(y_um), dtype=bool)
    for centre in centres:
        keep |= (y_um >= centre - 0.15) & (y_um <= centre + 0.15)
    out[:, ~keep] = 0.0
    return out


def readout(name, rows):
    """Pixel values read from the straight waveguide, one square per pixel."""
    return RI.assemble(DATA / ("readout_%s.npz" % name), rows)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 9.0))
    fig.subplots_adjust(left=0.08, right=0.985, top=0.93, bottom=0.17,
                        hspace=0.28, wspace=0.20)

    loaded = [load(name) for name in IMAGES]

    for row, (name, (field, x, y, rows)) in enumerate(zip(IMAGES, loaded)):
        x_um, y_um = x * 1e6, y * 1e6
        single = display_only(field, y_um, lanes(field, y_um, len(rows)))

        ax = axes[row][0]
        im0 = ax.imshow(field.T, origin="lower", cmap="inferno", vmin=0.0,
                        vmax=float(np.percentile(field, 99.5)),
                        interpolation="bilinear", aspect="auto",
                        extent=[x_um[0], x_um[-1], y_um[0], len(rows) * PITCH])
        ax.set_title("both waveguides" if row == 0 else "", fontsize=10)

        ax = axes[row][1]
        im1 = ax.imshow(single.T, origin="lower", cmap="inferno", vmin=0.0,
                        vmax=float(np.percentile(single, 99.5)),
                        interpolation="bilinear", aspect="auto",
                        extent=[x_um[0], x_um[-1], y_um[0], len(rows) * PITCH])
        ax.set_title("straight waveguide only" if row == 0 else "", fontsize=10)

        for ax in (axes[row][0], axes[row][1]):
            ax.set_xlabel("x (um)", fontsize=9)
            ax.tick_params(labelsize=8)
        axes[row][0].set_ylabel("%d by %d image\ny (um)" % (len(rows), len(rows)),
                                fontsize=9)

    bar0 = fig.add_axes([0.08, 0.06, 0.38, 0.018])
    fig.colorbar(im0, cax=bar0, orientation="horizontal", label="intensity")
    bar0.tick_params(labelsize=8)
    bar1 = fig.add_axes([0.56, 0.06, 0.38, 0.018])
    fig.colorbar(im1, cax=bar1, orientation="horizontal", label="intensity")
    bar1.tick_params(labelsize=8)

    out = FIG / "fig2_field.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())


