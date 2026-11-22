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
PAD = P["pixel"]["pad_um"]
DATA = HERE / "data"
FIG = HERE / "figures"

IMAGES = ("dino", "smile_e083")
FILES = {"dino": "example.txt", "smile": "smile.txt",
         "smile_e083": "smile.txt", "smile_e350": "smile.txt"}


def load(name):
    z = np.load(DATA / ("field_%s.npz" % name))
    rows = [ln.strip() for ln in (HERE / "images" / FILES[name])
            .read_text(encoding="utf-8").splitlines() if ln.strip()]
    return z["I"], z["x"], z["y"], rows


def peaks_in(field, y_um, lo, hi, thr=0.03):
    """Local maxima of the profile between two y values.

    The profile is the maximum over x, not the mean. A row that is nearly dark
    still has one or two bright pixels, and only a maximum keeps those; a mean
    over x would leave such a row with no peak at its straight waveguide, and the
    row would then be read off the other waveguide, pattern inverted.
    """
    profile = np.convolve(field.max(axis=0), np.ones(3) / 3.0, mode="same")
    band = (y_um >= lo) & (y_um <= hi)
    yy, ss = y_um[band], profile[band]
    idx = [j for j in range(1, len(ss) - 1)
           if ss[j] >= ss[j - 1] and ss[j] >= ss[j + 1] and ss[j] > thr]
    groups = []
    for j in idx:
        if groups and yy[j] - yy[groups[-1][0]] < 0.25:
            if ss[j] > ss[groups[-1][0]]:
                groups[-1] = [j]
        else:
            groups.append([j])
    return sorted((float(yy[g[0]]), float(ss[g[0]])) for g in groups)


def lanes(field, y_um, n_rows):
    """Where the display waveguide of each row sits.

    The straight waveguide is the upper member of each pair. When a row is dark
    its straight waveguide carries almost nothing, so only the other one shows a
    peak; that row's position is then taken from the spacing measured on the rows
    where both peaks are visible. Picking the bright peak instead would read that
    row's pattern inverted, which is exactly the mistake this guard prevents.
    """
    found, spacings = [], []
    for i in range(n_rows):
        guess = (n_rows - 1 - i) * PITCH
        peaks = peaks_in(field, y_um, guess - 1.8, guess + 1.2)
        found.append(peaks)
        if len(peaks) >= 2:
            spacings.append(peaks[-1][0] - peaks[-2][0])

    step = float(np.median(spacings)) if spacings else 0.30
    out = []
    for peaks in found:
        if len(peaks) >= 2:
            out.append(peaks[-1][0])
        elif len(peaks) == 1:
            out.append(peaks[0][0] + step)
        else:
            out.append(float("nan"))
    return out


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


def check(field, y_um, centres, rows, x_um):
    """Read each row back and report any row whose pattern is inverted.

    This is the guard for the mistake described in lanes(): if a row comes back
    anticorrelated with the image, the wrong waveguide was kept.
    """
    truth = RI.truth_matrix(rows)
    bad = []
    for i, centre in enumerate(centres):
        band = (y_um >= centre - 0.15) & (y_um <= centre + 0.15)
        values = np.array([
            field[np.ix_((x_um >= PAD + (c + 0.5) * CELL - 8.0) &
                         (x_um <= PAD + (c + 0.5) * CELL + 8.0), band)].mean()
            for c in range(len(rows[0]))])
        r = float(np.corrcoef(values, truth[i])[0, 1])
        if r < 0:
            bad.append((i, round(r, 2)))
    return bad


def main():
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 11.0))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.94, bottom=0.10,
                        hspace=0.22, wspace=0.22)

    loaded = [load(name) for name in IMAGES]

    for row, (name, (field, x, y, rows)) in enumerate(zip(IMAGES, loaded)):
        x_um, y_um = x * 1e6, y * 1e6
        centres = lanes(field, y_um, len(rows))
        bad = check(field, y_um, centres, rows, x_um)
        print("%-6s lanes %d, inverted rows %s" % (name, len(centres), bad or "none"))
        single = display_only(field, y_um, centres)

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
            ax.set_box_aspect(1)
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

    out = FIG / "fig2_field_v2.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())




