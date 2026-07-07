# Quant stack (clean-room, zero-dependency)

Pure-Python implementations of the mathematics, written from the published
algorithms — not copied from any third-party library or repo. Nothing external to
break, delete, or license. Research/scan only: none of this loosens a live risk cap.

## Files

| file | role |
|---|---|
| `regime_engine.py` | Hurst exponent (R/S on returns), OU mean-reversion half-life, GARCH(1,1) by maximum likelihood (own Nelder-Mead). Returns a regime label, a vol-target size multiplier, and a `dip_edge_favorable` flag. FILTER + SIZER, never a standalone signal. |
| `flow_filter_backtest.py` | Tests whether order-flow vetoes (OBV / Chaikin Money Flow / RVOL) improve the Regime Dip edge, universe-wide, with a 60/40 walk-forward split. A veto only counts if it helps OUT-OF-SAMPLE. |
| `market_data.py` | Universe definition + daily-bar CSV writer. Source-agnostic: the Cowork agent feeds bars from the Robinhood connector, or a repo/CI job injects its own fetch. |
| `scan.py` | The orchestrator. Runs the whole pipeline and prints one ranked, actionable board. This is what "check the market / scan for trades" executes. |

## Pipeline (scan.py)

1. **Regime Dip gate** — close > SMA10 > SMA20, Wilder RSI(2) < 10.
2. **regime_engine** — Hurst says whether the name actually mean-reverts; GARCH forecasts next-day vol and sets a vol-target size multiplier (<= 1, never levers up).
3. **Order-flow veto** — OBV(5d) rising and CMF(21) > 0; never buy a dip while money is leaving.
4. **Sizing + risk caps** — 3% max-loss/trade, 30% single-name, options premium <= 23% budget, whole-share native-stop feasibility.

A name is a **LONG-CANDIDATE** only if the dip trigger is live **and** Hurst says mean-reverting **and** money is not leaving. Everything else is STAND ASIDE / WATCH.

## Run

```bash
python3 regime_engine.py --selftest       # validate the math on known series
python3 market_data.py                     # populate data/<SYMBOL>.csv (needs a fetch source)
python3 scan.py --equity 215.30            # the market scan
python3 flow_filter_backtest.py            # OBV/CMF/RVOL veto research, walk-forward
```

## Discipline

Every feature is a hypothesis until it survives **out-of-sample** and clears costs
(spread/slippage). With multiple variants tested, a lone in-sample winner is treated
as noise. Capital survival beats activity.
