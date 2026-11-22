# -*- coding: utf-8 -*-
"""verify_tier.py -- is a tier really unchanged, or is the readout just forgiving?

Question (user, 2026-11-22): the 8.3 % tier reports 0/441 pixel errors. Is the field
truly unchanged, or did the threshold absorb a large analogue change?

This compares the cached readout vectors of two tiers and reports, side by side:
    * the analogue change: correlation and mean/max relative change per pixel
    * the decision margin: lowest lit vs highest dark, under the SAME threshold rule
    * the differing bits

If the analogue values move a lot while the bits stay identical, that is genuine
robustness (the pattern survives a big offset). If the analogue values are identical,
the tier did not actually change the device and the 0/441 means nothing.

Usage:  python verify_tier.py smile smile_e083
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"


def art_rows(prefix):
    p = HERE.parent / "images" / (prefix + ".txt")
    if not p.exists():
        p = HERE.parent / "images" / (prefix.split("_")[0] + ".txt")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        t = "".join(c for c in line.replace(".", "0").replace("#", "1") if c in "01")
        if t:
            rows.append(t)
    return rows


def cache(prefix):
    z = np.load(OUT / ("readout_%s.npz" % prefix), allow_pickle=True)
    d = {}
    for k in z.files:
        if k.startswith("v_"):
            d[int(k[2:])] = (z[k], str(z["p_" + k[2:]].tolist()))
    return d


def matrix(prefix, rows):
    d = cache(prefix)
    pat_of = {r: p for r, (v, p) in d.items()}
    M = np.full((len(rows), len(rows[0])), np.nan)
    for i, rw in enumerate(rows):
        src = i if i in d else next((r for r, p in pat_of.items()
                                     if p == str(list(rw))), None)
        if src is not None:
            M[i, :len(d[src][0])] = d[src][0]
    return M


def report(name, M, ideal):
    v = M[~np.isnan(M)]
    lo, hi = np.percentile(v, 20), np.percentile(v, 80)
    thr = 0.5 * (lo + hi)
    bits = M > thr
    ok = ~np.isnan(M)
    err = int(np.sum((bits != ideal.astype(bool)) & ok))
    lit = M[(ideal.astype(bool)) & ok]
    dark = M[(~ideal.astype(bool)) & ok]
    print("  %-14s thr=%.4f  lit_min=%.4f  dark_max=%.4f  margin=%+.4f  bits_wrong=%d"
          % (name, thr, lit.min(), dark.max(), lit.min() - dark.max(), err))
    return bits, thr


def main(argv):
    a = argv[0] if argv else "smile"
    b = argv[1] if len(argv) > 1 else "smile_e083"
    rows = art_rows(a)
    ideal = np.array([[int(c) for c in r] for r in rows], dtype=float)

    MA, MB = matrix(a, rows), matrix(b, rows)
    print("=" * 78)
    print("%s   vs   %s     rows=%d width=%d" % (a, b, len(rows), len(rows[0])))
    print("=" * 78)
    bitsA, thrA = report(a, MA, ideal)
    bitsB, thrB = report(b, MB, ideal)

    ok = ~np.isnan(MA) & ~np.isnan(MB)
    x, y = MA[ok], MB[ok]
    corr = float(np.corrcoef(x, y)[0, 1])
    rel = np.abs(y - x) / np.maximum(np.abs(x), 1e-30)
    print("-" * 78)
    print("ANALOGUE CHANGE (this is the real question):")
    print("  correlation            %.6f" % corr)
    print("  mean |relative change| %.2f %%" % (100 * rel.mean()))
    print("  max  |relative change| %.1f %%" % (100 * rel.max()))
    print("  pixels with >10%% change: %d / %d" % (int((rel > 0.10).sum()), rel.size))
    print("  BITS that differ between the two tiers: %d"
          % int(np.sum((bitsA != bitsB) & ok)))
    print("-" * 78)
    if corr > 0.9999 and rel.max() < 0.01:
        print("VERDICT: the tiers are essentially identical -> the 0/441 is meaningless")
    elif int(np.sum((bitsA != bitsB) & ok)) == 0 and rel.max() > 0.10:
        print("VERDICT: analogue values moved a lot, all bits survived -> GENUINE robustness")
    else:
        print("VERDICT: mixed, read the numbers above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


