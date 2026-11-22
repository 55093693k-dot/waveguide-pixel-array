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
RED = "#d62728"
GREEN = "#2ca02c"


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
    start = PAD + k * CELL - BEND / 2.0 - x_half    # where the ramp begins
    reach = BEND + P["unit"]["active_um"] + BEND    # length of the exchange
    xc = start + reach / 2.0                        # its centre
    draw_row(ax2, row, 0.0)
    ax2.set_xlim(xc - 16.0, xc + 16.0)
    ax2.set_ylim(-1.40, 0.70)
    ax2.set_aspect("auto")
    for edge in (start, start + CELL):
        ax2.axvline(edge, color="black", lw=1.0, ls="--")
    ax2.set_xlabel("x (um)")
    ax2.set_ylabel("y (um)")
    ax2.set_title("one exchange unit", fontsize=10)
    ax2.tick_params(labelsize=8)

    y_straight = 0.5 * (row["lanes"]["straight"][0] + row["lanes"]["straight"][1])
    y_rest = 0.5 * (row["lanes"]["moving_rest"][0] + row["lanes"]["moving_rest"][1])

    def arrow(start_xy, end_xy, colour, bend=0.0):
        patch = FancyArrowPatch(start_xy, end_xy, arrowstyle="-|>", mutation_scale=17,
                                color=colour, lw=1.9, zorder=6, shrinkA=0, shrinkB=0,
                                connectionstyle="arc3,rad=%g" % bend)
        patch.set_path_effects([pe.withStroke(linewidth=3.2, foreground="white")])
        ax2.add_patch(patch)

    def note(x, y, text, colour, ha="center", va="center"):
        label = ax2.text(x, y, text, color=colour, fontsize=9, ha=ha, va=va,
                         zorder=7)
        label.set_path_effects([pe.withStroke(linewidth=3.2, foreground="white")])

    # red: in on the moving waveguide, out on the straight one
    arrow((xc - 12.0, y_rest), (xc - 7.4, y_rest), RED)
    note(xc - 12.0, y_rest - 0.22, "in", RED, ha="left")
    arrow((xc + 7.4, y_straight), (xc + 12.6, y_straight), RED)
    note(xc + 12.6, y_straight + 0.22, "out", RED, ha="right")
    arrow((xc - 1.4, y_rest + 0.12), (xc - 1.4, y_straight - 0.12), RED, bend=0.35)

    # green: the same unit the other way round, light in on the straight one
    arrow((xc - 12.0, y_straight), (xc - 7.4, y_straight), GREEN)
    note(xc - 12.0, y_straight + 0.22, "in", GREEN, ha="left")
    arrow((xc + 7.4, y_rest), (xc + 12.6, y_rest), GREEN)
    note(xc + 12.6, y_rest - 0.22, "out", GREEN, ha="right")
    arrow((xc + 1.4, y_straight - 0.12), (xc + 1.4, y_rest + 0.12), GREEN, bend=0.35)

    handles = [Patch([(0, 0), (1, 0), (1, 1)], facecolor=COLOURS[k],
                     label=k + " waveguide")
               for k in ("straight", "moving")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.968),
               ncol=2, frameon=False, fontsize=9)

    fig.suptitle("Layout of the encoded image", fontsize=10, y=0.995)

    out = HERE / "figures" / "fig1_layout_v7.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("written: figures/fig1_layout_v7.png  (%d rows, %d by %d pixels)"
          % (geo["rows"], geo["rows"], geo["columns"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())









