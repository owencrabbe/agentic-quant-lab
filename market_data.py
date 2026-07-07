#!/usr/bin/env python3
"""
market_data.py  --  universe definition + daily-bar CSV writer  (zero deps)
Owen Crabbe / agentic-quant-lab

WHY SOURCE-AGNOSTIC
  A script running in a sandbox cannot reach the Robinhood connector; only the
  Cowork agent can. So this module OWNS the universe + CSV format, and the actual
  bar fetch is INJECTED as a function. Two ways to feed it:

  (A) Cowork agent path (what runs in-session):
        The agent calls the Robinhood MCP get_equity_historicals for each symbol
        and passes the bars straight into write_symbol_csv(). No creds in code.

  (B) Repo / CI path (runs in your environment with your Robinhood auth):
        Provide a fetch_fn(symbol, start, end) -> list of bar dicts and call
        write_universe(fetch_fn). Plug in robin_stocks or a urllib REST call.
        Data plumbing is infrastructure; all STRATEGY math stays in our own
        modules (regime_engine.py, flow_filter_backtest.py).

CSV FORMAT (what regime_engine.py and flow_filter_backtest.py read):
  date,open,high,low,close,volume
"""
import os, csv

# The desk universe. Strong-6 are Regime-Dip eligible; discovery names are
# monitoring / Tier-1-2 candidates. Keep in sync with the watchlists.
STRONG6   = ["SPY", "QQQ", "NVDA", "AAPL", "AMD", "SOFI"]
DISCOVERY = ["PGY", "SRAD", "QTWO", "EGAN", "LEU", "BKKT", "EOSE"]
UNIVERSE  = STRONG6 + DISCOVERY

def write_symbol_csv(symbol, bars, out_dir="data"):
    """bars: iterable of dicts/tuples with open,high,low,close,volume (+optional date).
    Accepts the Robinhood MCP bar shape (open_price/high_price/... ) or plain keys."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{symbol.upper()}.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for b in bars:
            if isinstance(b, dict):
                date = b.get("begins_at") or b.get("date") or ""
                o = b.get("open_price",  b.get("open"))
                h = b.get("high_price",  b.get("high"))
                l = b.get("low_price",   b.get("low"))
                c = b.get("close_price", b.get("close"))
                v = b.get("volume")
            else:  # tuple (date,o,h,l,c,v) or (o,h,l,c,v)
                if len(b) == 6: date, o, h, l, c, v = b
                else: date = ""; o, h, l, c, v = b
            w.writerow([date, o, h, l, c, v])
    return path

def write_universe(fetch_fn, symbols=UNIVERSE, out_dir="data", start=None, end=None):
    """fetch_fn(symbol, start, end) -> iterable of bars. Repo/CI path."""
    written = []
    for s in symbols:
        bars = fetch_fn(s, start, end)
        if bars:
            written.append(write_symbol_csv(s, bars, out_dir))
    return written

# --- reference REST fetch (stdlib urllib; needs a Robinhood bearer token) ------
def robinhood_fetch(symbol, start=None, end=None, token=None, span="year", interval="day"):
    """Best-effort stdlib pull. token from arg or env RH_TOKEN. Returns [] on failure
    so the caller can fall back to the agent/MCP path. No third-party client."""
    import json, urllib.request
    token = token or os.environ.get("RH_TOKEN")
    if not token:
        return []
    url = (f"https://api.robinhood.com/marketdata/historicals/{symbol}/"
           f"?interval={interval}&span={span}&bounds=regular")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        return data.get("historicals", [])
    except Exception:
        return []

if __name__ == "__main__":
    # Repo/CI smoke: try the REST fetch if a token is present.
    n = write_universe(robinhood_fetch)
    print(f"wrote {len(n)} csv(s): {n}" if n else
          "No token (set RH_TOKEN) — in Cowork the agent feeds bars via write_symbol_csv().")
