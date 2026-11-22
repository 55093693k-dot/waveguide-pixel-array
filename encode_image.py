"""encode_image.py -- turn a binary image into a waveguide layout.

Reads a text image (one line per row, '#' bright, '.' dark) and writes
geometry.json: every polygon, ready to be imported into a layout editor or
sent to the wave solver.

Nothing here needs a wave solver. Only numpy is used, and only for the
raised-cosine ramp along the moving waveguide.

Usage
    python encode_image.py images/example.txt
    python encode_image.py images/smile.txt -o out/smile_geometry.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / "parameters.json").read_text(encoding="utf-8"))

W = P["waveguide"]["width_um"]
G_ON = P["waveguide"]["gap_coupled_um"]
G_OFF = P["waveguide"]["gap_rest_um"]
BEND = P["pixel"]["bend_um"]
ACT = P["pixel"]["active_um"]
CELL = P["pixel"]["total_um"]
PAD = P["pixel"]["pad_um"]
PITCH = P["pixel"]["row_pitch_um"]
SMOOTH = P["pixel"]["transition"] == "smooth"

BRIGHT = "#1"


def read_image(path):
    """Return the image as a list of strings, one per row."""
    rows = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r]
    if not rows:
        raise ValueError("%s holds no rows" % path)
    width = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != width:
            raise ValueError("row %d has %d characters, row 0 has %d" % (i, len(r), width))
    return rows


def bit(row, col):
    return 1 if row[col] in BRIGHT else 0


def exchanges(row):
    """Where the light has to cross from one waveguide to the other.

    Light enters on the moving waveguide. It crosses at the first bright
    pixel, and then wherever two neighbouring pixels differ.
    """
    out, previous = [], 0
    for c in range(len(row)):
        b = bit(row, c)
        out.append(1 if b != previous else 0)
        previous = b
    return out


def moving_centreline(n_pix, flips):
    """Centreline of the moving waveguide, as (x, y) in micrometres.

    At rest the waveguide sits far from the straight one. Across a pixel that
    has to exchange, it is pulled in to the coupling gap and held there for the
    active length. The ramp is a raised cosine, so the slope is continuous at
    both ends.
    """
    x_total = n_pix * CELL + 2 * PAD
    x = np.linspace(0.0, x_total, 4000)

    y_inner = G_ON / 2.0                     # inner edge of the straight waveguide
    y_coupled = -(G_ON / 2.0 + W / 2.0)
    y_rest = y_inner - G_OFF - W / 2.0

    state = np.zeros_like(x)
    for i, f in enumerate(flips):
        if f:
            x0 = PAD + i * CELL
            state[(x >= x0 - BEND / 2.0) & (x <= x0 + ACT + BEND / 2.0)] = 1.0

    n = max(1, int(round(BEND / (x[1] - x[0]))))
    kernel = np.hanning(n) if SMOOTH else np.ones(n)
    kernel = kernel / kernel.sum()
    weight = np.convolve(state, kernel, mode="same")

    return x, y_rest + (y_coupled - y_rest) * weight, y_rest, y_coupled


def row_polygons(row, index):
    """Both waveguides of one row, as polygons in micrometres.

    Coordinates are local to the row: x = 0 at the middle of the row,
    y = 0 halfway between the two waveguides.
    """
    x_span = len(row) * CELL
    x_total = x_span + 2 * PAD
    xc = x_total / 2.0

    y_straight = G_ON / 2.0 + W / 2.0
    straight = [
        [0.0 - xc, y_straight - W / 2.0],
        [x_total - xc, y_straight - W / 2.0],
        [x_total - xc, y_straight + W / 2.0],
        [0.0 - xc, y_straight + W / 2.0],
    ]

    flips = exchanges(row)
    x, y, y_rest, y_coupled = moving_centreline(len(row), flips)

    # The access at both ends must sit on the rest position, or the port would
    # launch light beside the waveguide.
    for probe in (PAD / 4.0, x_total - PAD / 4.0):
        here = float(np.interp(probe, x, y))
        if abs(here - y_rest) > 0.005:
            raise AssertionError(
                "the moving waveguide is at y = %.3f at x = %.1f, but its rest "
                "position is %.3f" % (here, probe, y_rest))

    yc = float(np.mean(y))
    upper = [[float(a - xc), float(b + W / 2.0 - yc)] for a, b in zip(x, y)]
    lower = [[float(a - xc), float(b - W / 2.0 - yc)] for a, b in zip(x[::-1], y[::-1])]

    return {
        "row": index,
        "pattern": row,
        "exchanges": flips,
        "offset_y_um": round(index * PITCH, 4),
        "polygons": [
            {"name": "straight",
             "vertices": [[round(a, 4), round(b, 4)] for a, b in straight]},
            {"name": "moving", "centre_y_um": round(yc, 4),
             "vertices": [[round(a, 4), round(b, 4)] for a, b in upper + lower]},
        ],
        "lanes": {
            "straight": [round(y_straight - W / 2.0, 4), round(y_straight + W / 2.0, 4)],
            "moving_rest": [round(y_rest - W / 2.0, 4), round(y_rest + W / 2.0, 4)],
            "moving_coupled": [round(y_coupled - W / 2.0, 4), round(y_coupled + W / 2.0, 4)],
        },
    }


def image_geometry(rows, source=""):
    """The whole image: one polygon set per row, stacked at the row pitch."""
    return {
        "source": str(source),
        "rows": len(rows),
        "columns": len(rows[0]),
        "image_um": [round(len(rows[0]) * CELL, 4), round(len(rows) * PITCH, 4)],
        "device_um": [round(len(rows[0]) * CELL + 2 * PAD, 4),
                      round(len(rows) * PITCH, 4)],
        "parameters": P,
        "layout": [row_polygons(r, i) for i, r in enumerate(rows)],
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src = Path(argv[1])
    if len(argv) > 3 and argv[2] in ("-o", "--out"):
        out = Path(argv[3])
    else:
        out = HERE / "out" / (src.stem + "_geometry.json")
    rows = read_image(src)
    geo = image_geometry(rows, src)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(geo, indent=1), encoding="utf-8")
    n_ex = sum(sum(r["exchanges"]) for r in geo["layout"])
    print("image    %d by %d" % (geo["rows"], geo["columns"]))
    print("size     %.1f by %.1f um, device %.1f um wide with access"
          % (geo["image_um"][0], geo["image_um"][1], geo["device_um"][0]))
    print("pixels   %d, exchanges %d" % (geo["rows"] * geo["columns"], n_ex))
    print("written  %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

