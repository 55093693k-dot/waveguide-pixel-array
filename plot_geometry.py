"""plot_geometry.py -- draw the layout that encode_image.py produces.

Top: the whole device. Bottom: three pixels, close enough to see the two gaps
that carry the image.

The picture is drawn from out/example_geometry.json if it exists, and from the
encoder directly if it does not, so the figure always shows what the encoder
actually wrote.

Usage
    python plot_geometry.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import encode_image as EI                                       # noqa: E402

P = EI.P
CELL = P["unit"]["total_um"]
PAD = P["unit"]["pad_um"]
GAP_ON = P["waveguide"]["gap_coupled_um"]
GAP_OFF = P["waveguide"]["gap_rest_um"]

COLOURS = {"straight": "#2f6fa8", "moving": "#d1741f"}


def load_layout():
    path = HERE / "out" / "example_geometry.json"
    if not path.exists():
        rows = EI.read_image(HERE / P["image"]["example"])
        return EI.image_geometry(rows, P["image"]["example"])
    return json.loads(path.read_text(encoding="utf-8-sig"))


def draw_row(ax, row, y_offset):
    for poly in row["polygons"]:
        centre = y_offset + poly.get("centre_y_um", 0.0)
        xy = [(vx, vy + centre) for vx, vy in poly["vertices"]]
        ax.add_patch(Patch(xy, closed=True, facecolor=COLOURS[poly["name"]],
                           edgecolor="none", lw=0))


def main():
    geo = load_layout()
    rows = geo["layout"]
    x_half = geo["device_um"][0] / 2.0
    y_top = geo["device_um"][1]

    fig = plt.figure(figsize=(12.0, 8.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.8, 1.0], hspace=0.42)

    ax1 = fig.add_subplot(gs[0])
    for row in rows:
        draw_row(ax1, row, row["offset_y_um"])
    ax1.set_xlim(-x_half, x_half)
    ax1.set_ylim(-1.4, y_top + 1.0)
    ax1.set_aspect("auto")
    ax1.set_xlabel("x (um)")
    ax1.set_ylabel("y (um)")
    ax1.set_title("the whole device", fontsize=10)
    ax1.tick_params(labelsize=8)

    ax2 = fig.add_subplot(gs[1])
    row = rows[0]
    draw_row(ax2, row, 0.0)
    x0 = PAD - x_half + 9 * CELL           # start of pixel 9
    ax2.set_xlim(x0 - 6.0, x0 + 5 * CELL + 6.0)
    ax2.set_ylim(-1.35, 0.62)
    ax2.set_aspect("auto")
    for k in range(6):
        ax2.axvline(x0 + k * CELL, color="0.65", lw=0.7, ls=":")
    ax2.set_xlabel("x (um)")
    ax2.set_ylabel("y (um)")
    ax2.set_title("five units of row 0", fontsize=10)
    ax2.tick_params(labelsize=8)

    # the two gaps, each labelled beside its own arrow
    x_r = x0 + 0.5 * CELL
    ax2.annotate("", xy=(x_r, 0.10), xytext=(x_r, -0.7263),
                 arrowprops=dict(arrowstyle="<->", color="k", lw=1.1))
    ax2.text(x_r + 2.0, -0.32, "gap %.2f um" % GAP_OFF, fontsize=9, va="center")

    x_c = x0 + 2.5 * CELL
    ax2.annotate("gap %.2f um" % GAP_ON, xy=(x_c, -0.02),
                 xytext=(x_c + 13.0, -0.40), fontsize=9, va="center",
                 arrowprops=dict(arrowstyle="->", lw=1.0, color="k"))

    ax2.text(x0 + 0.6 * CELL, 0.44, "one unit = %.0f um" % CELL, fontsize=9)

    handles = [Patch([(0, 0), (1, 0), (1, 1)], facecolor=COLOURS[k],
                     label=k + " waveguide")
               for k in ("straight", "moving")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.968),
               ncol=2, frameon=False, fontsize=9)

    fig.suptitle("Layout of the encoded image", fontsize=10, y=0.995)

    out = HERE / "figures" / "fig1_layout_v4.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("written: figures/fig1_layout_v4.png  (%d rows, %d by %d pixels)"
          % (geo["rows"], geo["rows"], geo["columns"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())






