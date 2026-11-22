"""make_figure.py -- target against measurement, on one colour scale.

Left: the image that was encoded. Right: the pixel values that come back out of
the simulation. Both panels share one colour scale, so a loss of contrast shows
up as a loss of contrast instead of being normalised away.

Usage
    python make_figure.py dino --image images/example.txt --out figures/fig3_readout.png
    python make_figure.py smile_e350 --image images/smile.txt --out figures/fig4_degraded.png

Numbers such as the count of wrong pixels belong in the caption, not in the
panel title.
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
    if "_e" in prefix:
        return "+%g %% coupling length" % (int(prefix.split("_e")[1]) / 10.0)
    return "measured"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prefix", nargs="?", default="smile_e350")
    ap.add_argument("--image", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    image = Path(args.image) if args.image else None
    if image is None:
        stem = args.prefix.split("_")[0]
        image = HERE / "images" / (stem + ".txt")
        if not image.exists():
            image = HERE / "images" / "example.txt"

    rows = RI.load_image(image)
    ideal = RI.truth_matrix(rows)
    values = RI.assemble(DATA / ("readout_%s.npz" % args.prefix), rows)
    res = RI.report(values, ideal)

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.4))
    for ax, data, title in ((axes[0], ideal.astype(float), "target"),
                            (axes[1], values, label(args.prefix))):
        ax.imshow(data, cmap="inferno", vmin=0.0, vmax=1.0,
                  interpolation="nearest", aspect="equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=10)
        for k in range(1, ideal.shape[1]):
            ax.axhline(k - 0.5, color="0.25", lw=0.3)
            ax.axvline(k - 0.5, color="0.25", lw=0.3)
    fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0.0, 1.0), cmap="inferno"),
                 ax=axes.tolist(), fraction=0.028, pad=0.02,
                 label="pixel value, shared scale")

    out = Path(args.out) if args.out else FIG / ("fig_%s.png" % args.prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("written: %s" % out)
    print("  %d of %d pixels correct, dim bright %.3f, bright dark %.3f, contrast %.1f"
          % (res["correct"], res["pixels"], res["dim_bright"] or 0.0,
             res["bright_dark"] or 0.0, res["contrast"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
