"""simulate_row.py -- run one row of the device in a wave solver.

Takes a row of the image, builds the layout from encode_image.py, sends light
in at one end, and writes what comes out: the four port powers and the near
field above the row.

This step needs Ansys Lumerical FDTD, which is commercial. Everything else in
this repository runs without it.

Usage
    python simulate_row.py --row 0
    python simulate_row.py --row 0 --image images/smile.txt --out out/
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import encode_image as EI                                       # noqa: E402

P = EI.P
SLAB = P["optical"]["slab_thickness_um"]
MAT = P["optical"]["material"]
DX = P["mesh"]["dx_um"]
ACC = P["mesh"]["mesh_accuracy"]
T_SIM = P["mesh"]["simulation_time_s"]
DOMAIN_H = P["mesh"]["domain_height_um"]
PAD = P["pixel"]["pad_um"]

UM = 1e-6
PORTS = ("straight_in", "moving_in", "straight_out", "moving_out")


def design():
    """The two gaps. The rest gap is set by how much the light must be left alone.

    A guided mode beside another waveguide couples over an exponential tail, so
    a separation of gap_rest leaves exp(-gamma * (gap_rest - gap_on)) of the
    coupling that the coupled gap gives. With the numbers in parameters.json
    that is one part in 200.
    """
    gap_on = P["waveguide"]["gap_coupled_um"]
    gamma = P["waveguide"]["gamma_per_um"]
    supp = P["waveguide"]["suppression_ratio"]
    gap_rest = gap_on + np.log(supp) / gamma
    return {"gap_on": gap_on, "gap_rest": round(float(gap_rest), 4),
            "active_um": P["pixel"]["active_um"]}


def build(fdtd, row, index=0, nfreq=51, port_span=0.55):
    """Place the layout, the ports, the monitors and the solver region."""
    geo = EI.row_polygons(row, index)
    x_total = len(row) * EI.CELL + 2 * PAD
    xc = x_total / 2.0
    y_offset = geo["offset_y_um"]

    for poly in geo["polygons"]:
        vertices = np.array(poly["vertices"], dtype=float) * UM
        # The moving waveguide is stored about its own mean line, so its centre
        # offset has to be added back when it is placed.
        y_centre = y_offset + poly.get("centre_y_um", 0.0)
        fdtd.addpoly({"name": "row%02d_%s" % (index, poly["name"]), "material": MAT,
                      "x": 0.0, "y": y_centre * UM, "z": 0.0, "z span": SLAB * UM,
                      "vertices": vertices})

    fdtd.addfdtd({"name": "FDTD", "dimension": "2D",
                  "x": 0.0, "x span": x_total * UM,
                  "y": y_offset * UM, "y span": DOMAIN_H * UM,
                  "z": 0.0, "z span": 0.0})
    for key, value in (("mesh accuracy", ACC),
                       ("background index", P["optical"]["n_background"]),
                       ("simulation time", T_SIM)):
        fdtd.setnamed("FDTD", key, value)
    for face in ("x min bc", "x max bc", "y min bc", "y max bc"):
        fdtd.setnamed("FDTD", face, "PML")

    fdtd.addmesh({"name": "fine", "x": 0.0, "x span": (x_total - 0.4) * UM,
                  "y": y_offset * UM, "y span": 5.0 * UM,
                  "z": 0.0, "z span": SLAB * UM})
    for key, value in (("override x mesh", 1), ("override y mesh", 1),
                       ("override z mesh", 0), ("dx", DX * UM), ("dy", DX * UM)):
        fdtd.setnamed("fine", key, value)

    fdtd.setglobalsource("wavelength start", 1.45e-6)
    fdtd.setglobalsource("wavelength stop", 1.65e-6)
    fdtd.setglobalmonitor("use source limits", True)
    fdtd.setglobalmonitor("frequency points", nfreq)

    lanes = geo["lanes"]
    y_straight = 0.5 * (lanes["straight"][0] + lanes["straight"][1])
    y_moving = 0.5 * (lanes["moving_rest"][0] + lanes["moving_rest"][1])
    x_in, x_out = -xc + PAD / 4.0, xc - PAD / 4.0
    for name, y, x, direction in (
            ("straight_in", y_straight, x_in, "Forward"),
            ("moving_in", y_moving, x_in, "Forward"),
            ("straight_out", y_straight, x_out, "Backward"),
            ("moving_out", y_moving, x_out, "Backward")):
        fdtd.addport({"name": name, "injection axis": "x-axis", "direction": direction,
                      "mode selection": "fundamental TE mode",
                      "x": x * UM, "y": (y + y_offset) * UM,
                      "y span": port_span * UM, "z": 0.0, "z span": 0.0})
        fdtd.setnamed("FDTD::ports::" + name, "frequency points", nfreq)
    fdtd.setnamed("FDTD::ports", "source port", "moving_in")
    fdtd.setnamed("FDTD::ports", "source mode", "mode 1")

    fdtd.addpower({"name": "field", "monitor type": "2D Z-normal",
                   "x": 0.0, "x span": x_total * UM, "y": y_offset * UM,
                   "y span": DOMAIN_H * UM, "z": 0.0, "z span": 0.0})
    fdtd.setnamed("field", "override global monitor settings", 1)
    fdtd.setnamed("field", "wavelength center", 1.55e-6)
    fdtd.setnamed("field", "wavelength span", 0.002e-6)
    fdtd.setnamed("field", "frequency points", 1)
    return x_total



def run(fdtd, row, index, out_dir, nfreq=51):
    """Run one row and write the port record and the field dump."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = "row%02d" % index
    fdtd.newproject()
    x_total = build(fdtd, row, index, nfreq=nfreq)
    fdtd.save(str(out_dir / (tag + ".fsp")))

    started = time.time()
    fdtd.run()
    elapsed = round(time.time() - started, 1)

    s = {}
    for name in PORTS:
        got = fdtd.getresult("FDTD::ports::" + name, "S")
        lam = np.asarray(got["lambda"]).ravel()
        val = np.asarray(got["S"]).ravel()
        s[name] = complex(val[int(np.argmin(np.abs(lam - 1.55e-6)))])

    straight = abs(s["straight_out"]) ** 2
    moving = abs(s["moving_out"]) ** 2
    back = abs(s["straight_in"]) ** 2 + abs(s["moving_in"]) ** 2

    field = fdtd.getresult("field", "E")
    e = np.asarray(field["E"]).reshape(len(np.asarray(field["x"]).ravel()),
                                       len(np.asarray(field["y"]).ravel()), -1, 3)
    intensity = (np.abs(e[:, :, 0, :]) ** 2).sum(axis=2)
    np.savez_compressed(out_dir / (tag + "_map.npz"), I=intensity,
                        x=np.asarray(field["x"]).ravel(),
                        y=np.asarray(field["y"]).ravel())

    record = {
        "tag": tag, "row": index, "pattern": row, "art_rows": [index],
        "exchanges": sum(EI.exchanges(row)),
        "pixel_um": EI.CELL, "device_um": round(x_total, 1),
        "straight_out": round(straight, 4),
        "moving_out": round(moving, 4),
        "back": round(back, 5),
        "total": round(straight + moving + back, 4),
        "run_s": elapsed,
    }
    (out_dir / (tag + ".json")).write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--row", type=int, default=0)
    ap.add_argument("--image", default=str(HERE / P["image"]["example"]))
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args(argv)

    rows = EI.read_image(args.image)
    if not 0 <= args.row < len(rows):
        print("the image has %d rows, row %d does not exist" % (len(rows), args.row))
        return 2

    print("design   %s" % design())
    try:
        import lumapi
    except ImportError:
        print("Ansys Lumerical is not installed, so the layout can be written but not run.")
        print("The layout alone is produced by:  python encode_image.py %s" % args.image)
        return 3

    fdtd = lumapi.FDTD(hide=True)
    try:
        record = run(fdtd, rows[args.row], args.row, Path(args.out))
    finally:
        fdtd.close()
    print(json.dumps(record, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

