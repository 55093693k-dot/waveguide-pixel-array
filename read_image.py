"""read_image.py -- recover the pixels from simulated data.

Two kinds of input are accepted.

A reduced readout, as produced by simulate_row.py: one array of pixel values
per row, keyed by the row pattern it came from.

    data/readout_smile_e350.npz

A field dump, as produced by the solver's field monitor: the intensity on a
plane, one row of the device.

    out/dino_s21_r00_map.npz

Both are turned into a two-dimensional map of pixel values, in units of the
input power, and compared with the image that was encoded.

Usage
    python read_image.py data/readout_smile_e350.npz images/smile.txt
    python read_image.py out/dino_s21_r00_map.npz images/example.txt --row 0
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / "parameters.json").read_text(encoding="utf-8"))

CELL = P["pixel"]["total_um"]
PAD = P["pixel"]["pad_um"]
LANE = P["readout"]["display_lane_offset_um"]
XW = P["readout"]["x_half_window_um"]
YW = P["readout"]["y_half_window_um"]
THR = P["readout"]["threshold"]

BRIGHT = "#1"


def load_image(path):
    rows = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if r]


def truth_matrix(rows):
    return np.array([[1 if ch in BRIGHT else 0 for ch in r] for r in rows], dtype=int)


def bitstring(row):
    """The row as 0 and 1, whichever characters the file uses."""
    return "".join("1" if ch in "#1" else "0" for ch in row)


def pixels_from_field(path, n_pix, row_in_scene=0):
    """One row of pixel values from a field dump.

    A pixel is the mean of the intensity over the middle of the pixel, taken on
    the straight waveguide. The middle is used so that the ramps at either end
    of a pixel, where the two waveguides are still moving apart, do not enter
    the number.
    """
    z = np.load(path)
    intensity = z["I"]
    x = (z["x"] if z["x"].ndim == 1 else z["x"][:, 0]) * 1e6
    y = (z["y"] if z["y"].ndim == 1 else z["y"][0, :]) * 1e6

    band = (y >= LANE + 2.4 * row_in_scene - YW) & (y <= LANE + 2.4 * row_in_scene + YW)
    values = np.zeros(n_pix)
    for c in range(n_pix):
        centre = PAD + (c + 0.5) * CELL
        window = (x >= centre - XW) & (x <= centre + XW)
        values[c] = intensity[np.ix_(window, band)].mean()
    return values


def readout_map(path):
    """Bit pattern -> pixel values, from a reduced readout.

    Two layouts are accepted: one array per row (keys v_ / p_), or one matrix
    plus its row patterns (keys values / patterns).
    """
    z = np.load(path)
    out = {}
    if "values" in z.files and "patterns" in z.files:
        values = np.atleast_2d(z["values"])
        for pattern, row in zip(z["patterns"], values):
            out[bitstring(str(pattern))] = np.asarray(row, dtype=float)
        return out
    for key in z.files:
        if not key.startswith("v_"):
            continue
        raw = "".join(str(x) for x in np.asarray(z["p_" + key[2:]]).ravel())
        out["".join(ch for ch in raw if ch in "01")] = np.asarray(z[key], dtype=float)
    return out


def field_map(folder, image_rows):
    """Bit pattern -> pixel values, from the per-row field dumps of one image.

    A record is used only if it says which image rows it covers and its field
    dump is next to it, so pointing this at a folder of mixed files is safe. A
    simulation may stand in for several image rows when those rows carry the same
    pattern; the record says which rows it covers.
    """
    out = {}
    for js in sorted(Path(folder).glob("*.json")):
        # utf-8-sig: a hand-edited record on Windows often carries a byte-order mark.
        rec = json.loads(js.read_text(encoding="utf-8-sig"))
        rows = rec.get("art_rows")
        if not rows:
            continue
        npz = js.with_name(js.stem + "_map.npz")
        if not npz.exists():
            continue
        values = pixels_from_field(npz, len(image_rows[0]))
        for r in rows:
            out[bitstring(image_rows[r])] = values
    return out


def assemble(source, image_rows):
    """Two-dimensional map of pixel values, NaN where a row is missing."""
    if isinstance(source, dict):
        table = source
    elif str(source).endswith(".npz"):
        table = readout_map(source)
    else:
        table = field_map(source, image_rows)
    out = np.full((len(image_rows), len(image_rows[0])), np.nan)
    for i, pattern in enumerate(image_rows):
        key = bitstring(pattern)
        if key in table:
            out[i, :] = table[key]
    return out


def report(values, truth, threshold=None):
    """Errors, the two extremes, and the contrast."""
    threshold = THR if threshold is None else threshold
    ok = np.isfinite(values)
    wrong = int(((values > threshold) != (truth == 1))[ok].sum())
    bright = values[(truth == 1) & ok]
    dark = values[(truth == 0) & ok]
    contrast = (np.nanpercentile(values, 80)
                / max(np.nanpercentile(values, 20), 1e-12))
    return {
        "pixels": int(ok.sum()),
        "wrong": wrong,
        "correct": int(ok.sum()) - wrong,
        "dim_bright": round(float(bright.min()), 4) if bright.size else None,
        "bright_dark": round(float(dark.max()), 4) if dark.size else None,
        "separated": bool(bright.size and dark.size and bright.min() > dark.max()),
        "contrast": round(float(contrast), 1),
        "threshold": threshold,
    }


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    source, image = argv[1], argv[2]
    rows = load_image(image)
    truth = truth_matrix(rows)
    values = assemble(source, rows)

    if "--row" in argv:
        r = int(argv[argv.index("--row") + 1])
        print("row %d  %s" % (r, rows[r]))
        print("values  " + " ".join("%.3f" % v for v in values[r]))
        print("bits    " + "".join("1" if v > THR else "0" for v in values[r]))
        return 0

    res = report(values, truth)
    print("pixels       %d" % res["pixels"])
    print("correct      %d of %d" % (res["correct"], res["pixels"]))
    print("dim bright   %s" % res["dim_bright"])
    print("bright dark  %s" % res["bright_dark"])
    print("separated    %s" % res["separated"])
    print("contrast     %.1f x" % res["contrast"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
