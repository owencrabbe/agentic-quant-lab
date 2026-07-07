#!/usr/bin/env python3
"""
scan.py  --  the market scan.  Reads data/<SYMBOL>.csv, runs the full stack, and
prints one ranked, actionable table. THIS is what "check the market / scan for
trades / scheduled run" executes.

PIPELINE (all our own code, no external deps):
  1. Regime Dip v1 gate   : close>SMA10>SMA20 (regime) + Wilder RSI(2)<10 (trigger)
  2. regime_engine.py      : Hurst + half-life (is it actually mean-reverting?)
                             GARCH(1,1) next-day vol -> vol-target size multiplier
  3. Order-flow vetoes     : OBV(5d) direction, Chaikin Money Flow(21) sign
  4. Sizing + risk caps    : 3% max-loss/trade, 30% single-name cap, whole-share
                             native-stop feasibility, options-budget note

A name is a LONG CANDIDATE only if ALL agree: dip trigger live AND Hurst says
mean-reverting AND money-flow is not leaving. Anything less = STAND ASIDE / WATCH.
Nothing here can loosen a hard risk cap. Research/scan output only.

USAGE: python3 scan.py --equity 215.30 --data ./data
"""
import os, csv, glob, argparse, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regime_engine as RE

def sma(a,i,k): return sum(a[i-k+1:i+1])/k if i>=k-1 else None
def _rsi(c,i,p=2):
    if i<p: return None
    g=[];l=[]
    for j in range(1,i+1):
        d=c[j]-c[j-1]; g.append(max(d,0)); l.append(max(-d,0))
    ag=sum(g[:p])/p; al=sum(l[:p])/p
    for j in range(p,len(g)):
        ag=(ag*(p-1)+g[j])/p; al=(al*(p-1)+l[j])/p
    return 100.0 if al==0 else 100-100/(1+ag/al)
def atr(h,l,c,i,p=14):
    if i<p or not h: return None
    tr=[max(h[j]-l[j],abs(h[j]-c[j-1]),abs(l[j]-c[j-1])) for j in range(1,i+1)]
    a=sum(tr[:p])/p
    for j in range(p,len(tr)): a=(a*(p-1)+tr[j])/p
    return a
def obv_dir(c,v,i,k=5):
    if i<k: return 0
    o=0.0
    for j in range(i-k+1,i+1):
        o += v[j] if c[j]>c[j-1] else -v[j] if c[j]<c[j-1] else 0
    return o
def cmf(h,l,c,v,i,p=21):
    if i<p or not h: return None
    num=den=0.0
    for j in range(i-p+1,i+1):
        rng=h[j]-l[j]; mfm=((c[j]-l[j])-(h[j]-c[j]))/rng if rng>0 else 0
        num+=mfm*v[j]; den+=v[j]
    return num/den if den else 0.0

def load(d):
    out={}
    for f in sorted(glob.glob(os.path.join(d,"*.csv"))):
        sym=os.path.splitext(os.path.basename(f))[0].upper()
        o=[];h=[];l=[];c=[];v=[]
        with open(f) as fh:
            for row in csv.DictReader(fh):
                o.append(float(row["open"]));h.append(float(row["high"]))
                l.append(float(row["low"]));c.append(float(row["close"]));v.append(float(row["volume"]))
        # detect degenerate OHLC (close-only smoke data)
        has_ohlc = any(h[i]!=c[i] or l[i]!=c[i] for i in range(len(c)))
        if len(c)>=60: out[sym]=dict(o=o,h=h,l=l,c=c,v=v,has_ohlc=has_ohlc)
    return out

def scan(data, equity):
    rows=[]
    risk_pt = 0.03*equity; cap_amt = 0.30*equity; opt_budget = 0.23*equity
    for sym,d in data.items():
        c=d["c"]; h=d["h"] if d["has_ohlc"] else None; l=d["l"] if d["has_ohlc"] else None; v=d["v"]
        i=len(c)-1
        s10=sma(c,i,10); s20=sma(c,i,20); r=_rsi(c,i); a=atr(h,l,c,i) if h else None
        reg = "UP" if (s10 and s20 and c[i]>s10>s20) else ("DOWN" if s10 and c[i]<s10 else "NEUTRAL")
        cl = RE.classify(c)
        trig = (reg=="UP" and r is not None and r<10)
        obv5 = obv_dir(c,v,i); money = cmf(h,l,c,v,i) if h else None
        flow_ok = (obv5>0) and (money is None or money>0)
        candidate = trig and cl["dip_edge_favorable"] and flow_ok
        # sizing
        size_note=""
        if a and a>0:
            base_sh = risk_pt/(1.5*a)
            sh = base_sh*(cl["size_multiplier"] or 1.0)
            notional = min(sh*c[i], cap_amt)
            whole_ok = (c[i] <= cap_amt) and (int(sh)>=1)
            size_note = (f"~{sh:.2f}sh ${notional:.0f}"+("" if whole_ok else " frac/too-big"))
        elif not h:
            size_note="need OHLC"
        action = "LONG-CANDIDATE" if candidate else ("WATCH" if reg=="UP" else "STAND ASIDE")
        rows.append(dict(sym=sym,px=c[i],reg=reg,rsi=r,hurst=cl["hurst"],
                         hl=cl["half_life_days"],dipok=cl["dip_edge_favorable"],
                         fvol=cl["garch"]["forecast_daily_vol"] if cl["garch"] else None,
                         sizeX=cl["size_multiplier"],obv=obv5,cmf=money,
                         action=action,size=size_note))
    # rank: candidates first, then favorable-regime by RSI
    rows.sort(key=lambda x:(x["action"]!="LONG-CANDIDATE", x["rsi"] if x["rsi"] is not None else 999))
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--equity",type=float,default=215.30)
    ap.add_argument("--data",default=os.path.join(os.path.dirname(__file__),"data"))
    args=ap.parse_args()
    data=load(args.data)
    if not data:
        print(f"No CSVs in {args.data}. Populate via market_data.write_symbol_csv (agent feeds MCP bars)."); return
    rows=scan(data,args.equity)
    print(f"MARKET SCAN  equity=${args.equity:.2f}  risk/trade=${0.03*args.equity:.2f}  names={len(rows)}\n")
    hdr=f"{'SYM':6}{'px':>9}{'reg':>8}{'RSI2':>6}{'Hurst':>7}{'HL':>6}{'dipOK':>6}{'fvol%':>7}{'szX':>5}  {'ACTION':16} size/flow"
    print(hdr); print("-"*len(hdr))
    for x in rows:
        hl = "inf" if x["hl"]==float('inf') else (f"{x['hl']:.0f}" if x["hl"] else "-")
        fv = f"{x['fvol']*100:.1f}" if x["fvol"] else "-"
        hu = f"{x['hurst']:.2f}" if x["hurst"] is not None else "-"
        rs = f"{x['rsi']:.0f}" if x["rsi"] is not None else "-"
        sx = f"{x['sizeX']:.2f}" if x["sizeX"] else "-"
        flow = f"OBV{'+' if x['obv']>0 else '-'}" + (f" CMF{x['cmf']:+.2f}" if x['cmf'] is not None else "")
        print(f"{x['sym']:6}{x['px']:9.2f}{x['reg']:>8}{rs:>6}{hu:>7}{hl:>6}{str(x['dipok']):>6}{fv:>7}{sx:>5}  {x['action']:16} {x['size']} | {flow}")
    print("\nLONG-CANDIDATE = dip trigger AND Hurst mean-reverting AND money not leaving.")
    print("Everything else is STAND ASIDE / WATCH. Scan output only — no order is placed here.")

if __name__=="__main__": main()
