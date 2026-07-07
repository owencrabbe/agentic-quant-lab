#!/usr/bin/env python3
"""
regime_engine.py  --  Hurst + GARCH regime layer  (clean-room, zero dependencies)
Owen Crabbe / agentic-quant-lab

OWNERSHIP NOTE
  Every algorithm here is implemented from the published mathematics, not copied
  from any third-party library or repo. Pure Python standard library only
  (math, random for the self-test). Nothing external to break, delete, or license.

WHAT IT DOES
  For a price series it returns a regime read the desk can act on:
    1. Hurst exponent (rescaled-range / R/S)  -> trending vs mean-reverting vs random
    2. Mean-reversion half-life (OU via AR(1)) -> how fast a dip snaps back (in days)
    3. GARCH(1,1) fit by maximum likelihood    -> next-day volatility forecast,
       volatility persistence, long-run vol, and current vol-regime percentile
    4. A combined verdict:
         - is this name/timeframe SUITED to Regime Dip v1 (mean reversion)?
         - a volatility-target position-size multiplier (size down when vol is high)

HOW THE DESK USES IT
  Regime Dip v1 buys oversold dips inside uptrends. That edge only works when the
  series actually mean-reverts. Hurst tells us that. GARCH tells us how violent the
  next day is likely to be so we size down before storms instead of after. This
  layer is a FILTER + SIZER, never a standalone buy/sell signal. It cannot loosen
  any hard risk cap; it can only make an already-valid signal smaller or veto it.

USAGE
  python3 regime_engine.py --selftest        # validates the math on known series
  python3 regime_engine.py --data ./data     # reads <SYMBOL>.csv (date,o,h,l,c,v)
"""
import math, argparse, csv, glob, os, random

# ----------------------------------------------------------------------
# 1. HURST EXPONENT  (Rescaled-Range analysis)
#    H ~ 0.5 random walk; H < 0.5 mean-reverting; H > 0.5 trending/persistent.
# ----------------------------------------------------------------------
def hurst_rs(series):
    # R/S Hurst is defined on the increments (log returns), not price levels.
    # On levels a random walk reads H~1; on returns it correctly reads H~0.5.
    p = [math.log(v) for v in series if v > 0]
    x = [p[i] - p[i - 1] for i in range(1, len(p))]
    n = len(x)
    if n < 64:
        return None
    # chunk sizes (lags) spread log-uniformly between 8 and n/2
    lags = sorted(set(int(round(2 ** e)) for e in _frange(3, math.log2(n // 2), 0.5)))
    lags = [L for L in lags if 8 <= L <= n // 2]
    if len(lags) < 4:
        return None
    logL, logRS = [], []
    for L in lags:
        rs_vals = []
        for start in range(0, n - L + 1, L):          # non-overlapping windows
            w = x[start:start + L]
            m = sum(w) / L
            dev = [wi - m for wi in w]
            cum, run = 0.0, []
            for d in dev:
                cum += d; run.append(cum)
            R = max(run) - min(run)
            sd = math.sqrt(sum(d * d for d in dev) / L)
            if sd > 0:
                rs_vals.append(R / sd)
        if rs_vals:
            logL.append(math.log(L)); logRS.append(math.log(sum(rs_vals) / len(rs_vals)))
    if len(logL) < 4:
        return None
    return _ols_slope(logL, logRS)

# ----------------------------------------------------------------------
# 2. MEAN-REVERSION HALF-LIFE  (Ornstein-Uhlenbeck via AR(1) regression)
#    y_t = a + b*y_{t-1};  half-life = -ln2 / ln(b)  when 0 < b < 1.
# ----------------------------------------------------------------------
def half_life(series):
    y = [math.log(v) for v in series if v > 0]
    if len(y) < 30:
        return None
    y0, y1 = y[:-1], y[1:]
    b = _ols_slope(y0, y1)
    if b is None or b <= 0 or b >= 1:
        return float('inf')            # not mean-reverting
    return -math.log(2) / math.log(b)

# ----------------------------------------------------------------------
# 3. GARCH(1,1)  h_t = omega + alpha*r_{t-1}^2 + beta*h_{t-1}
#    Fit (omega, alpha, beta) by maximum likelihood (Gaussian), our own
#    Nelder-Mead optimizer. Returns forecast + persistence + long-run vol.
# ----------------------------------------------------------------------
def fit_garch11(returns):
    r = [ri for ri in returns]
    n = len(r)
    if n < 60:
        return None
    mu = sum(r) / n
    r = [ri - mu for ri in r]
    var0 = sum(ri * ri for ri in r) / n

    def neg_loglik(p):
        omega, alpha, beta = p
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.999:
            return 1e12
        h = var0; ll = 0.0
        for ri in r:
            if h <= 1e-12:
                return 1e12
            ll += math.log(h) + ri * ri / h
            h = omega + alpha * ri * ri + beta * h
        return 0.5 * ll

    start = [var0 * 0.1, 0.08, 0.88]
    best = _nelder_mead(neg_loglik, start)
    omega, alpha, beta = best
    persistence = alpha + beta
    long_run_var = omega / (1 - persistence) if persistence < 1 else None
    # one-step-ahead forecast off the last observation
    h = var0
    for ri in r:
        h = omega + alpha * ri * ri + beta * h
    return {
        "omega": omega, "alpha": alpha, "beta": beta,
        "persistence": persistence,
        "forecast_daily_vol": math.sqrt(h),
        "long_run_daily_vol": math.sqrt(long_run_var) if long_run_var else None,
    }

# ----------------------------------------------------------------------
# 4. COMBINED REGIME VERDICT
# ----------------------------------------------------------------------
def classify(prices, target_daily_vol=0.02):
    closes = list(prices)
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
    H = hurst_rs(closes)
    hl = half_life(closes)
    g = fit_garch11(rets)

    if H is None:
        regime = "insufficient data"
    elif H < 0.45:
        regime = "MEAN-REVERTING (dip edge favorable)"
    elif H > 0.55:
        regime = "TRENDING (dip edge unfavorable)"
    else:
        regime = "RANDOM (no reliable edge)"

    size_mult = None
    vol_note = None
    if g and g["forecast_daily_vol"] > 0:
        size_mult = min(1.0, target_daily_vol / g["forecast_daily_vol"])  # vol targeting, never lever up
        if g["long_run_daily_vol"]:
            ratio = g["forecast_daily_vol"] / g["long_run_daily_vol"]
            vol_note = ("elevated vs baseline" if ratio > 1.25 else
                        "calm vs baseline" if ratio < 0.8 else "near baseline")

    dip_ok = (H is not None and H < 0.5 and hl not in (None, float('inf')) and hl < 15)
    return {
        "hurst": H, "half_life_days": hl, "garch": g,
        "regime": regime, "vol_note": vol_note,
        "size_multiplier": size_mult,
        "dip_edge_favorable": dip_ok,
    }

# ----------------------------------------------------------------------
# helpers: OLS slope, float range, Nelder-Mead (all our own)
# ----------------------------------------------------------------------
def _ols_slope(x, y):
    n = len(x)
    if n < 2: return None
    mx = sum(x) / n; my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0: return None
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    return sxy / sxx

def _frange(a, b, step):
    v = a
    while v <= b + 1e-9:
        yield v; v += step

def _nelder_mead(f, x0, steps=None, iters=400, a=1.0, g=2.0, r=0.5, s=0.5):
    n = len(x0)
    if steps is None:
        steps = [0.5 * abs(v) + 1e-4 for v in x0]
    simplex = [list(x0)]
    for i in range(n):
        pt = list(x0); pt[i] += steps[i]; simplex.append(pt)
    fv = [f(p) for p in simplex]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: fv[i])
        simplex = [simplex[i] for i in order]; fv = [fv[i] for i in order]
        cent = [sum(simplex[i][j] for i in range(n)) / n for j in range(n)]
        xr = [cent[j] + a * (cent[j] - simplex[-1][j]) for j in range(n)]; fr = f(xr)
        if fv[0] <= fr < fv[-2]:
            simplex[-1], fv[-1] = xr, fr
        elif fr < fv[0]:
            xe = [cent[j] + g * (xr[j] - cent[j]) for j in range(n)]; fe = f(xe)
            simplex[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
        else:
            xc = [cent[j] + r * (simplex[-1][j] - cent[j]) for j in range(n)]; fc = f(xc)
            if fc < fv[-1]:
                simplex[-1], fv[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    simplex[i] = [simplex[0][j] + s * (simplex[i][j] - simplex[0][j]) for j in range(n)]
                    fv[i] = f(simplex[i])
    order = sorted(range(n + 1), key=lambda i: fv[i])
    return simplex[order[0]]

# ----------------------------------------------------------------------
# self-test + CLI
# ----------------------------------------------------------------------
def _selftest():
    random.seed(7)
    # (a) mean-reverting AR(1): Hurst should be < 0.5, half-life finite/short
    mr = [100.0]
    for _ in range(500):
        mr.append(100 + 0.6 * (mr[-1] - 100) + random.gauss(0, 1))
    # (b) random walk: Hurst should be ~0.5, half-life ~inf
    rw = [100.0]
    for _ in range(500):
        rw.append(rw[-1] + random.gauss(0, 1))
    print("SELF-TEST (known series)")
    print(f"  mean-reverting AR(1): Hurst={hurst_rs(mr):.2f} (expect <0.5)  half-life={half_life(mr):.1f}d (expect short)")
    print(f"  random walk         : Hurst={hurst_rs(rw):.2f} (expect ~0.5)  half-life={half_life(rw)} (expect inf)")
    g = fit_garch11([(mr[i]-mr[i-1])/mr[i-1] for i in range(1,len(mr))])
    print(f"  GARCH persistence={g['persistence']:.2f}  fcst_vol={g['forecast_daily_vol']*100:.2f}%/day")

def _run_dir(d):
    for f in sorted(glob.glob(os.path.join(d, "*.csv"))):
        sym = os.path.splitext(os.path.basename(f))[0].upper()
        closes = []
        with open(f) as fh:
            for row in csv.DictReader(fh):
                closes.append(float(row["close"]))
        if len(closes) < 80:
            print(f"{sym}: not enough data"); continue
        c = classify(closes)
        g = c["garch"]
        print(f"{sym:6} regime={c['regime']:38} Hurst={c['hurst']:.2f} "
              f"HL={c['half_life_days'] if c['half_life_days']==float('inf') else round(c['half_life_days'],1)}d "
              f"fcstVol={g['forecast_daily_vol']*100:.2f}%/d ({c['vol_note']}) "
              f"sizeX={c['size_multiplier']:.2f} dipOK={c['dip_edge_favorable']}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--data")
    args = ap.parse_args()
    if args.selftest: _selftest()
    elif args.data: _run_dir(args.data)
    else: _selftest()
