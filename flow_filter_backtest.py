#!/usr/bin/env python3
"""
flow_filter_backtest.py  --  Regime Dip v1 + order-flow veto research harness
Owen Crabbe / agentic-quant-lab

PURPOSE
  Test whether order-flow FEATURES (OBV, Chaikin Money Flow, RVOL) improve the
  Regime Dip v1 edge, across the full strong-6 + discovery universe, with a
  walk-forward (out-of-sample) split so we are not fooled by in-sample fitting.

WHY THIS EXISTS
  A single-name, in-sample pilot on SOFI (n=12) hinted that money-flow works as a
  DEFENSIVE VETO ("don't buy a dip while money is leaving"), not as an alpha
  generator. n=12 proves nothing. This harness answers the question at universe
  scale, out-of-sample, with honest multiple-testing awareness.

DATA
  Expects one CSV per symbol in ./data/  named <SYMBOL>.csv with columns:
      date,open,high,low,close,volume
  (Daily bars, split-adjusted. Pull via the Robinhood MCP get_equity_historicals
  and write each series to CSV — that keeps the data pull decoupled from the math
  and avoids hand-transcription.)

RULES (match the live desk)
  Regime gate : close > SMA10 > SMA20   (long only; no shorts, cash account)
  Trigger     : Wilder RSI(2) < 10
  Stop        : entry - 1.5 * ATR(14)
  Target      : entry + 4.0 * ATR(14)
  Time stop   : 10 sessions
  Exit        : first of {RSI(2)>70 close, target, stop, time stop}
  R           : per-trade PnL / initial risk (entry-stop)

FLOW VETOES TESTED (each ON/OFF, plus combos)
  OBV_up   : OBV(t) > OBV(t-5)               money flowing IN over last week
  CMF_pos  : Chaikin Money Flow(21) > 0       net accumulation
  RVOL_ok  : entry-day volume <= 1.5x 20d avg  (avoid capitulation spikes)

OUTPUT
  For baseline and each veto set: n, win%, avg R, profit factor, expectancy,
  and the SAME metrics split IN-SAMPLE vs OUT-OF-SAMPLE (walk-forward).
  Plus a crude deflated-expectancy flag: with K variants tested, treat any single
  variant's edge skeptically (multiple-testing). The bar is: does a veto help
  OUT-OF-SAMPLE, not just in-sample.

NOTE: research only. Nothing here changes live risk limits. A result is not
tradeable until it survives out-of-sample AND clears costs (spread/slippage).
"""
import os, csv, glob, math
from statistics import mean

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
UNIVERSE = ["SPY","QQQ","NVDA","AAPL","AMD","SOFI","PGY","SRAD","QTWO","EGAN","LEU","BKKT","EOSE"]

# ---------- indicators ----------
def wilder_rsi(closes, i, p=2):
    if i < p: return None
    g=[]; l=[]
    for j in range(1, i+1):
        ch = closes[j]-closes[j-1]; g.append(max(ch,0)); l.append(max(-ch,0))
    ag=sum(g[:p])/p; al=sum(l[:p])/p
    for j in range(p,len(g)):
        ag=(ag*(p-1)+g[j])/p; al=(al*(p-1)+l[j])/p
    if al==0: return 100.0
    return 100-100/(1+ag/al)

def atr(highs, lows, closes, i, p=14):
    if i < p: return None
    trs=[]
    for j in range(1,i+1):
        trs.append(max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1])))
    a=sum(trs[:p])/p
    for j in range(p,len(trs)):
        a=(a*(p-1)+trs[j])/p
    return a

def sma(a, i, k): return sum(a[i-k+1:i+1])/k if i>=k-1 else None

def obv_series(closes, vols):
    o=[0.0]*len(closes)
    for i in range(1,len(closes)):
        o[i]=o[i-1]+(vols[i] if closes[i]>closes[i-1] else -vols[i] if closes[i]<closes[i-1] else 0)
    return o

def cmf(highs, lows, closes, vols, i, p=21):
    if i < p: return None
    num=den=0.0
    for j in range(i-p+1, i+1):
        rng=highs[j]-lows[j]
        mfm=((closes[j]-lows[j])-(highs[j]-closes[j]))/rng if rng>0 else 0.0
        num+=mfm*vols[j]; den+=vols[j]
    return num/den if den else 0.0

def rvol(vols, i, k=20):
    if i<k: return None
    base=sum(vols[i-k:i])/k
    return vols[i]/base if base else None

# ---------- backtest ----------
STOP_ATR=1.5; TGT_ATR=4.0; MAXH=10

def backtest(sym, bars, veto):
    o=[b[0] for b in bars]; h=[b[1] for b in bars]; l=[b[2] for b in bars]
    c=[b[3] for b in bars]; v=[b[4] for b in bars]
    obv=obv_series(c,v)
    trades=[]; i=25
    while i < len(c)-1:
        s10=sma(c,i,10); s20=sma(c,i,20); r=wilder_rsi(c,i); a=atr(h,l,c,i)
        take = (s10 and s20 and r is not None and a and c[i]>s10>s20 and r<10)
        if take and veto(i,c,v,h,l,obv):
            entry=c[i]; stop=entry-STOP_ATR*a; tgt=entry+TGT_ATR*a; risk=entry-stop
            exit_px=None
            for hh in range(1,MAXH+1):
                j=i+hh
                if j>=len(c): exit_px=c[-1]; break
                if l[j]<=stop: exit_px=stop; break
                if h[j]>=tgt: exit_px=tgt; break
                if wilder_rsi(c,j)>70: exit_px=c[j]; break
                if hh==MAXH: exit_px=c[j]
            trades.append((entry-exit_px<0 and 1 or 0, (exit_px-entry)/risk, i))
            i+=hh
        else:
            i+=1
    return trades

def stats(trades):
    if not trades: return dict(n=0)
    Rs=[t[1] for t in trades]; n=len(Rs)
    gp=sum(x for x in Rs if x>0); gl=-sum(x for x in Rs if x<0)
    return dict(n=n, win=100*sum(1 for x in Rs if x>0)/n, avgR=mean(Rs),
                pf=(gp/gl if gl>0 else float('inf')))

# veto library
VETOES = {
 "baseline"            : lambda i,c,v,h,l,obv: True,
 "OBV_up"              : lambda i,c,v,h,l,obv: i>=5 and obv[i]>obv[i-5],
 "CMF_pos"             : lambda i,c,v,h,l,obv: (cmf(h,l,c,v,i) or -1)>0,
 "RVOL_ok"             : lambda i,c,v,h,l,obv: (rvol(v,i) or 99)<=1.5,
 "OBV_up & CMF_pos"    : lambda i,c,v,h,l,obv: i>=5 and obv[i]>obv[i-5] and (cmf(h,l,c,v,i) or -1)>0,
}

def load():
    data={}
    for f in glob.glob(os.path.join(DATA_DIR,"*.csv")):
        sym=os.path.splitext(os.path.basename(f))[0].upper()
        rows=[]
        with open(f) as fh:
            for row in csv.DictReader(fh):
                rows.append((float(row["open"]),float(row["high"]),float(row["low"]),
                             float(row["close"]),float(row["volume"])))
        if len(rows)>60: data[sym]=rows
    return data

def main():
    data=load()
    if not data:
        print(f"No CSVs in {DATA_DIR}. Write one <SYMBOL>.csv per name (date,open,high,low,close,volume).")
        return
    print(f"Loaded {len(data)} symbols: {sorted(data)}\n")
    for name,veto in VETOES.items():
        allt=[]; IS=[]; OOS=[]
        for sym,bars in data.items():
            split=int(len(bars)*0.6)  # walk-forward: first 60% in-sample
            t=backtest(sym,bars,veto)
            allt+=t
            IS +=[x for x in t if x[2]<split]
            OOS+=[x for x in t if x[2]>=split]
        a=stats(allt); s_is=stats(IS); s_oos=stats(OOS)
        def fmt(s): return (f"n={s['n']:3d} win={s['win']:4.0f}% avgR={s['avgR']:+.2f} PF={s['pf']:.2f}"
                            if s['n'] else "n=  0")
        print(f"{name:20} ALL[{fmt(a)}]  OOS[{fmt(s_oos)}]")
    print("\nVERDICT RULE: a veto earns a live test ONLY if it lifts avgR/PF OUT-OF-SAMPLE,")
    print("not just ALL/in-sample. With 5 variants tested, treat a lone winner as noise")
    print("until confirmed on fresh data and net of spread/slippage.")

if __name__=="__main__":
    main()
