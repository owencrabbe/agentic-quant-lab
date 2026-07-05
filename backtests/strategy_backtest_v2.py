import os
import yfinance as yf, pandas as pd, numpy as np, json, warnings
warnings.filterwarnings("ignore")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
os.makedirs(OUT, exist_ok=True)
TICKERS=["SPY","QQQ","NVDA","TSLA","AAPL","AMD"]

def fetch5(t):
    d=yf.download(t,period="55d",interval="5m",prepost=False,progress=False,auto_adjust=False)
    if d is None or len(d)==0: return None
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d=d.rename(columns=str.title); idx=d.index
    if idx.tz is None: idx=idx.tz_localize("UTC")
    d.index=idx.tz_convert("America/New_York")
    d=d.between_time("09:30","16:00")
    return d[(d[["Open","High","Low","Close"]]>0).all(axis=1)]

def daily_regime(t):
    d=yf.download(t,period="120d",interval="1d",progress=False,auto_adjust=False)
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d=d.rename(columns=str.title)
    d["sma10"]=d.Close.rolling(10).mean()
    d["sma20"]=d.Close.rolling(20).mean()
    reg={}
    for i in range(len(d)):
        c,s10,s20=d.Close.iloc[i],d.sma10.iloc[i],d.sma20.iloc[i]
        if np.isnan(s20): r=0
        elif c>s10>s20: r=1
        elif c<s10<s20: r=-1
        else: r=0
        reg[d.index[i].date()]=r
    return reg

def summarize(trades,name):
    if not trades: print(f"{name}: no trades"); return None
    df=pd.DataFrame(trades); wr=(df.R>0).mean(); exp=df.R.mean()
    pf=df.loc[df.R>0,"R"].sum()/(-df.loc[df.R<0,"R"].sum() or 1e-9)
    eq=df.R.cumsum(); dd=(eq-eq.cummax()).min()
    print(f"\n=== {name} ===")
    print(f"trades={len(df)}  win_rate={wr:.1%}  expectancy={exp:.3f}R  profit_factor={pf:.2f}  maxDD={dd:.1f}R  totalR={df.R.sum():.1f}")
    print(df.groupby('side').R.agg(['count','mean']).to_string())
    return dict(strategy=name,trades=int(len(df)),win_rate=round(float(wr),4),
                expectancy_R=round(float(exp),4),profit_factor=round(float(pf),2),
                maxDD_R=round(float(dd),2),totalR=round(float(df.R.sum()),2))

REG={t:daily_regime(t) for t in TICKERS}
results=[]

# V2a: Regime-filtered ORB (only breakout in trend direction, 1:2 R)
orb=[]
for t in TICKERS:
    d=fetch5(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        reg=REG[t].get(day,0)
        if reg==0: continue
        g=g.sort_index(); o=g.between_time("09:30","09:44")
        if len(o)<2: continue
        orh,orl=o.High.max(),o.Low.min(); rng=orh-orl
        if rng<=0: continue
        win=g.between_time("09:45","11:29"); entry=side=None
        for ts,bar in win.iterrows():
            if entry is None:
                if reg==1 and bar.High>=orh: entry,side,stop,tgt=orh,"long",orl,orh+2*rng
                elif reg==-1 and bar.Low<=orl: entry,side,stop,tgt=orl,"short",orh,orl-2*rng
                continue
            if side=="long":
                if bar.Low<=stop: orb.append(dict(t=t,side="long",R=-1.0));break
                if bar.High>=tgt: orb.append(dict(t=t,side="long",R=2.0));break
            else:
                if bar.High>=stop: orb.append(dict(t=t,side="short",R=-1.0));break
                if bar.Low<=tgt: orb.append(dict(t=t,side="short",R=2.0));break
        else:
            if entry is not None:
                last=win.Close.iloc[-1]; R=(last-entry)/rng if side=="long" else (entry-last)/rng
                orb.append(dict(t=t,side=side,R=float(np.clip(R,-1,2))))
results.append(summarize(orb,"V2a Regime-filtered ORB (1:2 R)"))

# V2b: Regime-filtered OTE 0.705 retracement
ote=[]
for t in TICKERS:
    d=fetch5(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        reg=REG[t].get(day,0)
        if reg==0: continue
        g=g.sort_index(); imp=g.between_time("09:30","10:14")
        if len(imp)<4: continue
        hi,lo=imp.High.max(),imp.Low.min(); hi_t,lo_t=imp.High.idxmax(),imp.Low.idxmin()
        rng=hi-lo
        if rng<=0: continue
        bull=hi_t>lo_t
        if reg==1 and bull: ent=hi-0.705*rng; stop=lo-0.1*rng; tgt=ent+2*(ent-stop); side="long"
        elif reg==-1 and not bull: ent=lo+0.705*rng; stop=hi+0.1*rng; tgt=ent-2*(stop-ent); side="short"
        else: continue
        win=g.between_time("10:15","15:30"); filled=False; risk=abs(ent-stop)
        if risk<=0: continue
        for ts,bar in win.iterrows():
            if not filled:
                if side=="long" and bar.Low<=ent: filled=True
                elif side=="short" and bar.High>=ent: filled=True
                if not filled: continue
            if side=="long":
                if bar.Low<=stop: ote.append(dict(t=t,side="long",R=-1.0));break
                if bar.High>=tgt: ote.append(dict(t=t,side="long",R=2.0));break
            else:
                if bar.High>=stop: ote.append(dict(t=t,side="short",R=-1.0));break
                if bar.Low<=tgt: ote.append(dict(t=t,side="short",R=2.0));break
        else:
            if filled:
                last=win.Close.iloc[-1]; R=(last-ent)/risk if side=="long" else (ent-last)/risk
                ote.append(dict(t=t,side=side,R=float(np.clip(R,-1,2))))
results.append(summarize(ote,"V2b Regime-filtered ICT-OTE (1:2 R)"))

# V2c: Open-drive momentum, LONG-only in uptrend (hold to close, stop = opening-range low)
mom=[]
for t in TICKERS:
    d=fetch5(t)
    if d is None: continue
    for day,g in d.groupby(d.index.date):
        reg=REG[t].get(day,0)
        if reg!=1: continue
        g=g.sort_index(); first30=g.between_time("09:30","09:59")
        if len(first30)<4: continue
        op=first30.Open.iloc[0]; c30=first30.Close.iloc[-1]
        if c30<=op: continue
        ent=c30; stop=first30.Low.min(); risk=ent-stop
        if risk<=0: continue
        rest=g.between_time("10:00","15:55"); exitpx=rest.Close.iloc[-1] if len(rest) else ent
        hit=False
        for ts,bar in rest.iterrows():
            if bar.Low<=stop: mom.append(dict(t=t,side="long",R=-1.0)); hit=True; break
        if not hit:
            mom.append(dict(t=t,side="long",R=float((exitpx-ent)/risk)))
results.append(summarize(mom,"V2c Open-drive momentum LONG-only uptrend (hold to close, stop=OR low)"))

json.dump([r for r in results if r],open(os.path.join(OUT,"strategy_results_v2.json"),"w"),indent=2)
print("\nsaved results/strategy_results_v2.json")
