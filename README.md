# agentic-quant-lab

An open research desk for an AI agent that trades a live, funded brokerage account with discipline instead of hope.

This repo does not sell signals and does not promise alpha. It documents a reproducible process: measure when the market actually moves, test whether a strategy has an edge, discard what does not survive, and keep only what a backtest supports. Every number below was produced by the scripts in `backtests/` and can be regenerated on your machine with free data.

## Thesis: evidence over folklore

Retail trading runs on confident claims with no measurement behind them. This project inverts that. Two pieces of common folklore were tested here and corrected:

1. "The ICT killzones (Asia open, London open, New York open) are where the money is." For an account that can only trade US equities and options, the Asia and London killzones happen while US stocks are closed or nearly illiquid. We measured the real intraday volatility clock and the tradeable edge sits almost entirely in the first 90 minutes of the New York session.
2. "Opening range breakouts and OTE retracements are edges." Traded blindly over the last 55 sessions, both lost money. The edge did not live in the entry pattern. It lived in only trading in the direction of the daily trend. Adding a regime filter flipped the same breakout from negative to positive expectancy.

## Result 1: the intraday volatility clock

Mean high-low range (basis points) and mean absolute 5-minute return (basis points) by 30-minute slot in US Eastern time, averaged across SPY, QQQ, NVDA, TSLA, AAPL, AMD over the last 55 sessions. Directional move is the honest measure of tradeable opportunity; raw range can be inflated by illiquid wide spreads.

| ET slot | Session block | Range (bp) | Directional move (bp) |
|--------:|---------------|-----------:|----------------------:|
| 09:30 | NY open | 64.4 | 34.2 |
| 10:00 | NY open | 41.7 | 21.1 |
| 10:30 | NY open | 36.1 | 18.4 |
| 11:00 | Lunch begins | 30.3 | 15.2 |
| 15:30 | Power hour | 25.6 | 13.2 |
| 13:00 | Early PM (lull) | 22.6 | 11.5 |
| 16:30 | Post-market | 116.6 | 11.2 |

Reading it: the 09:30 open shows roughly two to three times the directional movement of any other regular-hours slot. It is the engine. The 16:30 post-market row shows a huge range but tiny directional move: that is illiquid earnings-print noise on wide spreads, not opportunity, and it is excluded from scheduling. Midday (13:00 to 14:30) is the measured lull, exactly as the killzone model predicts.

Conclusion for a US-equity or options account: concentrate attention on 09:30 to 11:00 ET, keep a lighter watch on the 15:00 to 16:00 power hour, and stand down midday.

## Result 2: strategy backtests

Same universe and window (6 tickers, last 55 sessions, 5-minute bars, regular hours). Results are in R multiples, where 1R is the initial risk per trade. No commissions or slippage modeled; treat these as directional evidence, not a live-fill promise.

### Vanilla strategies, traded blindly

| Strategy | Trades | Win rate | Expectancy | Profit factor | Max DD | Total R |
|----------|-------:|---------:|-----------:|--------------:|-------:|--------:|
| Opening range breakout 15m (1:1) | 322 | 47.5% | -0.06R | 0.82 | -28.7R | -19.9R |
| ICT OTE 0.705 retracement (1:2) | 192 | 31.2% | -0.25R | 0.62 | -47.7R | -48.7R |
| Midday VWAP fade (2 ATR) | 316 | 28.5% | -0.16R | 0.78 | -56.7R | -49.8R |

All three lose. Every one bleeds worse on the short side, because the sample window was a strong uptrend. That loss pattern is the clue.

### The same strategies with a daily-trend regime filter

Regime is defined per symbol per day: uptrend when close > SMA10 > SMA20, downtrend when close < SMA10 < SMA20, otherwise no trade. Trades are only taken in the regime direction.

| Strategy | Trades | Win rate | Expectancy | Profit factor | Max DD | Total R |
|----------|-------:|---------:|-----------:|--------------:|-------:|--------:|
| Regime-filtered ORB (1:2) | 171 | 58.5% | +0.21R | 1.84 | -4.8R | +36.6R |
| Regime-filtered ICT-OTE (1:2) | 66 | 39.4% | -0.05R | 0.90 | -6.8R | -3.6R |
| Open-drive momentum, long-only in uptrend | 118 | 50.8% | +0.30R | 1.69 | -6.0R | +35.2R |

The regime filter turned the breakout from -0.06R to +0.21R and cut max drawdown from 28.7R to 4.8R. The open-drive momentum rule posted the highest expectancy at +0.30R. The OTE retracement stayed negative even filtered, so it is not promoted to live use.

The single most important finding in this repo: the entry pattern was not the edge. Trading only with the daily trend was the edge.

## Honest caveats

- Sample size is 55 recent sessions, not a decade. Both winning strategies are long-heavy and benefit from an uptrending sample. They are not yet proven across a bear or chop regime.
- The regime filter should protect in a downtrend by flipping to shorts or standing aside, but that behavior is under-tested here because the sample had few sustained downtrend days.
- No commissions or slippage are modeled. Opening-bar fills in particular can slip.
- Past performance does not predict future results. This is research tooling, not investment advice.

## Account-aware execution design

This desk was built for a small, live cash account with Level 2 options and no fractional-share stop orders. That constraint shapes everything:

- On low-priced liquid names (for example F near 13 and SOFI near 18) you can hold whole shares and attach a real protective stop.
- On higher-priced names (SPY, NVDA, TSLA) a small account can only hold fractional shares, which cannot carry a native stop on this broker. For those, risk is expressed either through a manually monitored exit at each scheduled loop run, or through a long option where max loss equals the premium paid.
- Hard guardrails while equity is small: fixed-dollar risk per position, a small number of concurrent positions, a daily loss stop, no averaging down, and no shorting against the regime.

## Reproduce

```bash
pip install -r requirements.txt
python backtests/session_volatility.py     # rebuilds results/volatility_clock.csv
python backtests/strategy_backtest.py      # vanilla strategies
python backtests/strategy_backtest_v2.py   # regime-filtered strategies
```

Data comes from Yahoo Finance via yfinance, so results shift as the trailing 55-session window rolls forward. That is intended: the clock and the edge are meant to be re-measured, not memorized.

## Repository layout

```
backtests/   reproducible Python backtests
results/     machine-generated outputs (CSV, JSON)
skills/      installable agent skills (session clock, the edge, the loop runbook)
```

## Roadmap

- Walk-forward validation across multiple regimes and a longer history via a paid intraday source.
- A downtrend and chop stress test of the regime filter.
- An order-flow and volume-profile confirmation layer on top of the regime gate.
- A futures and FX build where the Asia and London killzones become genuinely tradeable.

## Disclaimer

This project is for research and education. It is not financial advice and it does not guarantee profit. Trading involves risk of loss. You are responsible for your own capital and your own decisions.

## License

MIT. See LICENSE.
