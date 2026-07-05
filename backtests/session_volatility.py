import os
import yfinance as yf, pandas as pd, numpy as np, json, warnings
warnings.filterwarnings("ignore")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
os.makedirs(OUT, exist_ok=True)

TICKERS = ["SPY","QQQ","NVDA","TSLA","AAPL","AMD"]

def fetch(t, period, interval):
    d = yf.download(t, period=period, interval=interval, prepost=True,
                    progress=False, auto_adjust=False)
    if d is None or len(d)==0: return None
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.title)
    idx = d.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    d.index = idx.tz_convert("America/New_York")
    return d

# 5-min bars, last ~55 days, extended hours, 30-min-of-day volatility clock
rows = []
for t in TICKERS:
    d = fetch(t, "55d", "5m")
    if d is None:
        print("no data", t); continue
    d = d[(d["High"]>0)&(d["Low"]>0)&(d["Open"]>0)&(d["Close"]>0)].copy()
    d["ret"] = np.log(d["Close"]/d["Close"].shift(1))
    d["range_bp"] = (d["High"]-d["Low"])/d["Close"]*1e4
    d["absret_bp"] = d["ret"].abs()*1e4
    d = d.dropna(subset=["ret"])
    d["slot30"] = (d.index.floor("30min")).strftime("%H:%M")
    g = d.groupby("slot30").agg(avg_absret_bp=("absret_bp","mean"),
                                avg_range_bp=("range_bp","mean"),
                                n=("absret_bp","size"))
    g["ticker"]=t
    rows.append(g.reset_index())

allslots = pd.concat(rows)
clock = allslots.groupby("slot30").agg(avg_absret_bp=("avg_absret_bp","mean"),
                                       avg_range_bp=("avg_range_bp","mean"),
                                       n=("n","sum")).reset_index()
clock = clock.sort_values("slot30")

def session_label(hhmm):
    h,m = map(int, hhmm.split(":"))
    t = h*60+m
    if 4*60 <= t < 9*60+30: return "US pre-market (London/overlap)"
    if 9*60+30 <= t < 11*60: return "NY OPEN killzone"
    if 11*60 <= t < 13*60: return "NY lunch / midday"
    if 13*60 <= t < 15*60: return "Early PM"
    if 15*60 <= t < 16*60: return "NY CLOSE / power hour"
    if 16*60 <= t < 20*60: return "US post-market"
    return "Overnight (Asia)"

clock["session"]=clock["slot30"].apply(session_label)
clock_r = clock[clock["n"]>50].copy().sort_values("avg_range_bp", ascending=False)

print("=== TOP 12 HIGHEST-VOLATILITY 30-MIN SLOTS (ET), 5-min data last 55 sessions ===")
print(clock_r.head(12)[["slot30","session","avg_range_bp","avg_absret_bp","n"]].to_string(index=False))

print("\n=== VOLATILITY BY SESSION BLOCK (regular+ext hours) ===")
sess = clock_r.groupby("session").agg(avg_range_bp=("avg_range_bp","mean"),
                                      slots=("slot30","size")).sort_values("avg_range_bp",ascending=False)
print(sess.to_string())

clock.to_csv(os.path.join(OUT,"volatility_clock.csv"), index=False)
print("\nsaved results/volatility_clock.csv")
