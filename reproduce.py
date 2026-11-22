"""reproduce.py -- recompute every number the paper quotes, from data/.

No wave solver is needed. Each check reads a shipped file, recomputes the
number, and compares it with the value written in the paper. The exit code is
non-zero if any check fails.

Usage
    python reproduce.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_image as RI                                          # noqa: E402

DATA = HERE / "data"
IMAGES = HERE / "images"
FAILED = []


def check(name, got, want, tol):
    ok = abs(float(got) - float(want)) <= tol
    print("  %-46s %10.4f  expected %8.4f  %s"
          % (name, float(got), float(want), "ok" if ok else "MISMATCH"))
    if not ok:
        FAILED.append(name)


def image_report(image, readout):
    rows = RI.load_image(IMAGES / image)
    truth = RI.truth_matrix(rows)
    values = RI.assemble(DATA / readout, rows)
    return RI.report(values, truth), truth


def main():
    print("one image, 20 by 20")
    res, truth = image_report("example.txt", "readout_dino.npz")
    check("pixels read", res["pixels"], 400, 0)
    check("pixels correct", res["correct"], 400, 0)
    check("dim bright pixel", res["dim_bright"], 0.5676, 5e-4)
    check("brightest dark pixel", res["bright_dark"], 0.1661, 5e-4)
    print("  %-46s %10s  expected %8s  %s"
          % ("the two groups do not overlap", res["separated"], "True",
             "ok" if res["separated"] else "MISMATCH"))
    if not res["separated"]:
        FAILED.append("no overlap")

    print("the same image at three coupling lengths")
    for tag, want_ok, want_contrast in (("readout_smile.npz", 441, 80.8),
                                        ("readout_smile_e083.npz", 441, 241.8),
                                        ("readout_smile_e350.npz", 283, 2.7)):
        res, _ = image_report("smile.txt", tag)
        print("  %s" % tag)
        check("    pixels correct", res["correct"], want_ok, 0)
        check("    contrast", res["contrast"], want_contrast, 0.1)
        if tag == "readout_smile_e350.npz":
            check("    pixels wrong", res["wrong"], 158, 0)

    print("how far the addressed row leaks into its neighbours")
    tiles = json.loads((DATA / "tile_crosstalk_from_map.json").read_text(encoding="utf-8"))
    adjacent, far = -np.inf, -np.inf
    for tile in tiles:
        t = np.array([tile["T"][k] for k in sorted(tile["T"], key=int)], dtype=float)
        ref = t[0]
        if len(t) > 1:
            adjacent = max(adjacent, 10 * np.log10(max(t[1], 1e-12) / ref))
        for value in t[3:]:
            far = max(far, 10 * np.log10(max(value, 1e-12) / ref))
    check("worst neighbour, one row away, dB", adjacent, -21.9, 0.1)
    check("worst neighbour, three rows away, dB", far, -28.2, 0.1)

    print("")
    if FAILED:
        print("FAILED: %s" % ", ".join(FAILED))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
