import os
import yfinance as yf, pandas as pd, numpy as np, json, warnings
warnings.filterwarnings("ignore")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
os.makedirs(OUT, exist_ok=True)
TICKERS = ["SPY","QQQ","NVDA","TSLA","AAPL","AMD"]

def fetch(t):
    d = yf.download(t, period="55d", interval="5m", prepost=False,
                    progress=False, auto_adjust=False)
    if d is None or len(d)==0: return None
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.title)
    idx = d.index
    if idx.tz is None: idx = idx.tz_localize("UTC")
    d.index = idx.tz_convert("America/New_York")
    d = d.between_time("09:30","16:00")
    return d[(d[["Open","High","Low","Close"]]>0).all(axis=1)]

def summarize(trades, name):
    if not trades:
        print(f"{name}: no trades"); return None
    df = pd.DataFrame(trades)
    wr = (df.R>0).mean(); exp = df.R.mean()
    pf = df.loc[df.R>0,"R"].sum() / (-df.loc[df.R<0,"R"].sum() or 1e-9)
    eq = df.R.cumsum(); dd = (eq - eq.cummax()).min()
    print(f"\n=== {name} ===")
    print(f"trades={len(df)}  win_rate={wr:.1%}  expectancy={exp:.3f}R  "
          f"profit_factor={pf:.2f}  maxDD={dd:.1f}R  totalR={df.R.sum():.1f}")
    print(df.groupby('side').R.agg(['count','mean']).to_string())
    return dict(strategy=name, trades=int(len(df)), win_rate=round(float(wr),4),
                expectancy_R=round(float(exp),4), profit_factor=round(float(pf),2),
                maxDD_R=round(float(dd),2), totalR=round(float(df.R.sum()),2))

results=[]

# STRATEGY 1: Opening Range Breakout (first 15m OR, trade 9:45-11:00, 1:1 R)
orb=[]
for t in TICKERS:
    d=fetch(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        g=g.sort_index(); o=g.between_time("09:30","09:44")
        if len(o)<2: continue
        orh,orl=o.High.max(),o.Low.min(); rng=orh-orl
        if rng<=0: continue
        win=g.between_time("09:45","10:59"); entry=side=None
        for ts,bar in win.iterrows():
            if entry is None:
                if bar.High>=orh: entry,side,stop,tgt=orh,"long",orl,orh+rng
                elif bar.Low<=orl: entry,side,stop,tgt=orl,"short",orh,orl-rng
                continue
            if side=="long":
                if bar.Low<=stop: orb.append(dict(t=t,side="long",R=-1.0)); break
                if bar.High>=tgt: orb.append(dict(t=t,side="long",R=1.0)); break
            else:
                if bar.High>=stop: orb.append(dict(t=t,side="short",R=-1.0)); break
                if bar.Low<=tgt: orb.append(dict(t=t,side="short",R=1.0)); break
        else:
            if entry is not None:
                last=win.Close.iloc[-1]
                R=(last-entry)/rng if side=="long" else (entry-last)/rng
                orb.append(dict(t=t,side=side,R=float(np.clip(R,-1,1))))
results.append(summarize(orb,"ORB 15m open-range breakout (1:1 R, exit by 11:00)"))

# STRATEGY 2: ICT OTE 0.705 retracement (impulse off open, 1:2 R)
ote=[]
for t in TICKERS:
    d=fetch(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        g=g.sort_index(); imp=g.between_time("09:30","10:14")
        if len(imp)<4: continue
        hi,lo=imp.High.max(),imp.Low.min(); hi_t,lo_t=imp.High.idxmax(),imp.Low.idxmin()
        rng=hi-lo
        if rng<=0: continue
        bull = hi_t>lo_t
        if bull: ent=hi-0.705*rng; stop=lo-0.1*rng; tgt=ent+2*(ent-stop); side="long"
        else: ent=lo+0.705*rng; stop=hi+0.1*rng; tgt=ent-2*(stop-ent); side="short"
        win=g.between_time("10:15","15:30"); filled=False; risk=abs(ent-stop)
        if risk<=0: continue
        for ts,bar in win.iterrows():
            if not filled:
                if side=="long" and bar.Low<=ent: filled=True
                elif side=="short" and bar.High>=ent: filled=True
                if not filled: continue
            if side=="long":
                if bar.Low<=stop: ote.append(dict(t=t,side="long",R=-1.0)); break
                if bar.High>=tgt: ote.append(dict(t=t,side="long",R=2.0)); break
            else:
                if bar.High>=stop: ote.append(dict(t=t,side="short",R=-1.0)); break
                if bar.Low<=tgt: ote.append(dict(t=t,side="short",R=2.0)); break
        else:
            if filled:
                last=win.Close.iloc[-1]
                R=(last-ent)/risk if side=="long" else (ent-last)/risk
                ote.append(dict(t=t,side=side,R=float(np.clip(R,-1,2))))
results.append(summarize(ote,"ICT OTE 0.705 retracement (1:2 R, exit by 15:30)"))

# STRATEGY 3: Midday VWAP mean-reversion fade
mr=[]
for t in TICKERS:
    d=fetch(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        g=g.sort_index().copy()
        tp=(g.High+g.Low+g.Close)/3
        g["vwap"]=(tp*g.Volume).cumsum()/g.Volume.cumsum().replace(0,np.nan)
        g["atr"]=(g.High-g.Low).rolling(6).mean()
        win=g.between_time("11:00","13:59")
        for ts,bar in win.iterrows():
            if np.isnan(bar.vwap) or np.isnan(bar.atr) or bar.atr<=0: continue
            dev=(bar.Close-bar.vwap)/bar.atr
            if dev>=2 or dev<=-2:
                side="short" if dev>0 else "long"
                ent=bar.Close; stop=ent+(1.2*bar.atr if side=="short" else -1.2*bar.atr)
                tgt=bar.vwap; risk=abs(ent-stop)
                if risk<=0: continue
                fut=g[g.index>ts].between_time("11:00","15:45")
                for ts2,b2 in fut.iterrows():
                    if side=="long":
                        if b2.Low<=stop: mr.append(dict(t=t,side="long",R=-1.0)); break
                        if b2.High>=tgt: mr.append(dict(t=t,side="long",R=abs(tgt-ent)/risk)); break
                    else:
                        if b2.High>=stop: mr.append(dict(t=t,side="short",R=-1.0)); break
                        if b2.Low<=tgt: mr.append(dict(t=t,side="short",R=abs(ent-tgt)/risk)); break
                break
results.append(summarize(mr,"Midday VWAP fade (2 ATR extension, target VWAP)"))

json.dump([r for r in results if r], open(os.path.join(OUT,"strategy_results.json"),"w"), indent=2)
print("\nsaved results/strategy_results.json")
