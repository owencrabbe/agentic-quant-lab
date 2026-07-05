---
name: regime-filtered-momentum
description: The one backtested edge with positive expectancy in this repo. A daily-trend regime gate combined with either an opening-range breakout or an open-drive momentum entry, taken only in the direction of the trend. Use when generating an intraday equity or long-option signal for a watchlist name during the NY open window. This is the Signal Agent's primary playbook.
---

# Regime-Filtered Momentum

The core finding: the entry pattern is not the edge. Trading only in the direction of the daily trend is the edge. A blind opening-range breakout lost money (-0.06R). The same breakout, filtered to trade only with the daily trend, produced +0.21R expectancy, profit factor 1.84, and cut max drawdown from 28.7R to 4.8R. Open-drive momentum long-only in an uptrend produced the highest expectancy at +0.30R.

## Step 1: the regime gate (mandatory, checked first)

For each symbol, using daily bars:
- Uptrend if close > SMA10 > SMA20. Longs allowed. Shorts forbidden.
- Downtrend if close < SMA10 < SMA20. Shorts or long puts allowed. Longs forbidden.
- Otherwise no trade. Stand aside.

Never take a trade against the regime. Most of the historical losses came from fighting the trend.

## Step 2a: Opening-Range Breakout entry (two-sided)

- Opening range = high and low of 09:30 to 09:44 ET (first 15 minutes).
- In an uptrend: buy a break above the OR high. Stop at the OR low. Target = entry plus 2x the OR range (1:2).
- In a downtrend: sell or buy a put on a break below the OR low. Stop at the OR high. Target = entry minus 2x the OR range.
- Only look for the breakout between 09:45 and 11:29 ET. If no clean break, no trade.

## Step 2b: Open-Drive Momentum entry (long-only, highest expectancy)

- Only in an uptrend regime.
- Require an up-open drive: the 09:30 to 09:59 ET window must close above its open.
- Enter at the 10:00 ET price. Stop at the low of the first 30 minutes. Hold toward the close; exit on the stop or at 15:55 ET.

## Step 3: sizing and risk (micro account)

- Risk a fixed small dollar amount per trade while equity is small. Position size = risk dollars divided by (entry minus stop) per share.
- Whole-share names with a real attachable stop (for example F, SOFI) are preferred for clean risk.
- For higher-priced names, express the trade as a long call or put so max loss equals the premium, since fractional shares cannot carry a native stop on this broker.
- One setup per symbol per day. No averaging down. No adding to lose.

## Step 4: no-trade conditions

Reject the signal if any are true: regime is neutral; the move already ran past the entry; spread is wide or liquidity is thin; a scheduled catalyst (earnings) hits within the holding window; or the daily or weekly loss limit is already reached.

## Honest limits

Validated on 55 recent, mostly uptrending sessions. Not yet proven in a bear or chop regime. Re-run backtests/strategy_backtest_v2.py before relying on it, and treat every live trade as a test that updates the record.
