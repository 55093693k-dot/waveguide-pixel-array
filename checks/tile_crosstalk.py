# -*- coding: utf-8 -*-
"""tile_crosstalk.py -- per-row output power of the whole-array run, from the saved maps.

Why this exists (2026-11-21)
    tile_run.py stores, for every row, a flux number T read as `T[0]` from the
    T_XX monitor. That element is the FIRST wavelength of the monitor (1.45 um),
    not 1550 nm, so the numbers are not the transmitted power at the design point
    (row 0 gave 0.93 while rows 1-9 gave ~1e-3). They cannot go into a table.

    This script recomputes the per-row power directly from the saved field map
    (|E|^2 integrated over each row's band in the last part of the device), which
    is the quantity we actually want, and prints it next to the stored T so the
    discrepancy stays visible instead of being silently replaced.

Coordinate convention (measured, not assumed)
    The monitor data y is centred on the MONITOR, while Y_of is the absolute
    layout coordinate. The shift is (max(Y_of)+min(Y_of))/2. This script prints
    both so the convention is on the record.

Usage
    python tile_crosstalk.py                      # all chunk maps found in out/
    python tile_crosstalk.py out/tile_p2.40_r00-09_map.npz
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
BAND = 1.2e-6        # half width of a row band, m  (row pitch 2.4 um)
TAIL = 8e-6          # output region used for the readout, m


def one(map_path):
    stem = map_path.name.replace("_map.npz", "")
    jpath = map_path.with_name(stem + ".json")
    d = np.load(map_path)
    I, x, y = d["I"], d["x"], d["y"]
    Yo, rows = d["Y_of"], d["rows"]
    # Y_of is in MICROMETRES (layout units); the monitor's y is in METRES and is
    # already absolute, so no shift is applied (verified 2026-11-21: y spans
    # -1.3..22.9 um for a 10-row chunk whose Y_of spans 0..21.6 um).
    T = json.load(open(jpath, encoding="utf-8")).get("T", {}) if jpath.exists() else {}

    sel = x > x[-1] - TAIL
    sel_in = (x > 30e-6) & (x < 38e-6)          # just after the input, before any pixel
    print("== %s ==  y data: %.1f..%.1f um, Y_of: %.1f..%.1f um"
          % (stem, y.min() * 1e6, y.max() * 1e6, Yo.min(), Yo.max()))
    print("row   y_center   T(stored)   P(out)/sum   P(in)/sum")
    P, Pin = {}, {}
    for i, a in enumerate(rows):
        yc = Yo[i] * 1e-6
        m = np.abs(y - yc) <= BAND
        P[int(a)] = float(I[sel, :][:, m].sum())
        Pin[int(a)] = float(I[sel_in, :][:, m].sum())
    tot = sum(P.values()) or 1.0
    tin = sum(Pin.values()) or 1.0
    for i, a in enumerate(rows):
        a = int(a)
        print("%3d   %+6.1f um   %8.4f   %8.3f     %8.3f"
              % (a, Yo[i], T.get(str(a), float("nan")), P[a] / tot, Pin[a] / tin))
    return {"stem": stem, "P": P, "sum": tot, "P_in": Pin, "sum_in": tin,
            "T": {str(k): v for k, v in T.items()}}


def main(argv):
    maps = ([Path(argv[0])] if argv
            else sorted(OUT.glob("tile_p2.40_r*_map.npz")))
    if not maps:
        raise SystemExit("no chunk maps in %s" % OUT)
    res = [one(mp) for mp in maps]
    (OUT / "tile_crosstalk_from_map.json").write_text(
        json.dumps(res, indent=1), encoding="utf-8")
    print("written: out/tile_crosstalk_from_map.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

