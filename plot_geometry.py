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
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, Polygon as Patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import encode_image as EI                                       # noqa: E402

P = EI.P
CELL = P["unit"]["total_um"]
PAD = P["unit"]["pad_um"]
BEND = P["unit"]["bend_um"]
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
    k = row["exchanges"].index(1)          # the first unit that has to exchange
    x0 = PAD + k * CELL - BEND / 2.0 - x_half   # cut the period where the exchange starts
    draw_row(ax2, row, 0.0)
    ax2.set_xlim(x0 - 5.0, x0 + CELL + 5.0)
    ax2.set_ylim(-1.40, 0.86)
    ax2.set_aspect("auto")
    for edge in (x0, x0 + CELL):
        ax2.axvline(edge, color="0.55", lw=0.9, ls=":")
    ax2.set_xlabel("x (um)")
    ax2.set_ylabel("y (um)")
    ax2.set_title("one exchange unit", fontsize=10)
    ax2.tick_params(labelsize=8)

    y_straight = 0.5 * (row["lanes"]["straight"][0] + row["lanes"]["straight"][1])
    y_rest = 0.5 * (row["lanes"]["moving_rest"][0] + row["lanes"]["moving_rest"][1])

    def red_arrow(start, end, bend=0.0):
        arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=17,
                                color="red", lw=1.9, zorder=6, shrinkA=0, shrinkB=0,
                                connectionstyle="arc3,rad=%g" % bend)
        arrow.set_path_effects([pe.withStroke(linewidth=3.2, foreground="white")])
        ax2.add_patch(arrow)

    def red_text(x, y, text, ha="center"):
        label = ax2.text(x, y, text, color="red", fontsize=9, ha=ha, va="center",
                         zorder=7)
        label.set_path_effects([pe.withStroke(linewidth=3.2, foreground="white")])

    # light goes in on the moving waveguide, and comes out on the straight one
    red_arrow((x0 - 4.2, y_rest), (x0 + 1.5, y_rest))
    red_text(x0 - 4.0, y_rest - 0.20, "in", ha="left")
    red_arrow((x0 + CELL - 1.5, y_straight), (x0 + CELL + 4.2, y_straight))
    red_text(x0 + CELL + 4.0, y_straight + 0.20, "out", ha="right")

    # and it changes waveguide inside the unit
    red_arrow((x0 + 0.5 * CELL, y_rest + 0.12), (x0 + 0.5 * CELL, y_straight - 0.12),
              bend=0.35)
    red_text(x0 + 0.5 * CELL + 1.4, 0.5 * (y_rest + y_straight) - 0.02, "exchange",
             ha="left")

    # the width of the unit, above everything
    ax2.annotate("", xy=(x0, 0.60), xytext=(x0 + CELL, 0.60),
                 arrowprops=dict(arrowstyle="<->", color="0.25", lw=1.3,
                                 shrinkA=2, shrinkB=2))
    ax2.text(x0 + 0.5 * CELL, 0.72, "%.0f um" % CELL, fontsize=9, ha="center",
             va="bottom", color="0.2")

    handles = [Patch([(0, 0), (1, 0), (1, 1)], facecolor=COLOURS[k],
                     label=k + " waveguide")
               for k in ("straight", "moving")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.968),
               ncol=2, frameon=False, fontsize=9)

    fig.suptitle("Layout of the encoded image", fontsize=10, y=0.995)

    out = HERE / "figures" / "fig1_layout_v5.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("written: figures/fig1_layout_v5.png  (%d rows, %d by %d pixels)"
          % (geo["rows"], geo["rows"], geo["columns"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())







