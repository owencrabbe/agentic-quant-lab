---
name: session-clock
description: Decides WHEN the agentic trading loop should scan and act. Encodes the measured intraday volatility clock so the desk concentrates on the highest-edge windows and stands down during the midday lull. Use at the start of every loop run to decide whether this is a scan-and-act window or a stand-down window.
---

# Session Clock

Built from measured 5-minute data across SPY, QQQ, NVDA, TSLA, AAPL, AMD (see /results/volatility_clock.csv). Times are US Eastern. This clock is for a US equity and options account. If you later trade futures or FX, rebuild it, because the Asia and London killzones only matter for near-24-hour instruments.

## The windows

1. Pre-open prep, 09:00 to 09:29 ET. Do not trade. Gather account state, overnight news, the daily regime for each watchlist name, and mark the levels. Build candidate tickets so you are ready at the bell.
2. NY OPEN killzone, 09:30 to 11:00 ET. This is the engine: the 09:30 slot alone shows two to three times the directional movement of any other regular-hours slot. Almost all A-plus setups live here. Prioritize the first hour.
3. Midday lull, 11:00 to 14:00 ET. Lowest directional movement of the day. Stand down by default. Only manage open positions. Do not initiate new risk unless a scheduled catalyst hits.
4. Power hour, 15:00 to 16:00 ET. Secondary window. Trend continuation and end-of-day positioning. Lighter size than the open.
5. Post-market, after 16:00 ET. Do not trade. The apparent volatility here is illiquid earnings-print noise on wide spreads, not opportunity, and fills are unreliable in a small cash account.

## How to use in the loop

- If the current time is in window 1: run research and stage tickets, place nothing.
- If in window 2 or 4: run the full signal, risk, and execution-verify gates; place only if all pass.
- If in window 3 or 5: monitor and manage only; reject new entries with reason "outside edge window".

## Rebuild cadence

Re-run backtests/session_volatility.py monthly. The clock rolls with a trailing 55-session window and should be re-measured, not memorized.
