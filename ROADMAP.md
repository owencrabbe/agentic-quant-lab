# The Edge Machine — Action Plan for the Agentic Desk

## The thesis (read this first)

No one holds a permanent edge. Every edge decays as the market adapts. So the goal
is not to find one magic signal — it is to build a **machine that manufactures edges
faster than they die**: discover, prove honestly, deploy small, measure, kill the
rotten ones, compound the survivors. The trader who owns that loop beats the trader
hunting the next hot setup, every year, without exception.

"Best trader" is therefore a **process claim, not a returns promise**. We measure it
by expectancy, profit factor, risk-adjusted return, drawdown control, and process
compliance — never by a single lucky run. Capital survival beats activity. Always.

## The loop (this runs forever)

```
DISCOVER  ->  BACKTEST  ->  WALK-FORWARD  ->  DEFLATE (validation.py)  ->  PAPER
   ^                                                                          |
   |                                                                          v
 RETIRE  <-  MONITOR DECAY  <-  LIVE (full)  <-  LIVE (small)  <-  PROMOTE  <-'
```

Every strategy lives in `STRATEGY_REGISTRY.md` and moves one rung only on evidence.
The gate that matters: `validation.evaluate()` must return PAPER-ELIGIBLE — deflated
Sharpe > 0.95 after correcting for *every variant we tried*, sample >= 30, positive
out-of-sample. Nothing skips the gate. Winning streaks never loosen a limit.

## What "best" is measured by (the scoreboard)

| metric | why it matters | target direction |
|---|---|---|
| Expectancy (avg R) | the engine of compounding | > 0, stable |
| Profit factor | gross win / gross loss | > 1.3 sustained |
| Probabilistic / Deflated Sharpe | is the edge real after multiple testing | DSR > 0.95 |
| Max drawdown | survival | < kill-switch (25% micro / 5% institutional) |
| Process-compliance rate | did we follow our own rules | > 95% |
| Hit rate | context only (not a goal by itself) | informational |

Returns are an OUTPUT of getting the above right, not the target we chase.

## Phased plan by capital

Sizing tightens as capital grows — the opposite of what most blowups do.

### Phase 0 — NOW ( < $1,000 ) : Infrastructure + discipline
The account is too small for most edges to be sizable, so this phase is about
building the machine and the habit, not chasing PnL.
- Finish the data layer: build 13-month CSVs for all 13 names (see Immediate Steps).
- Run `flow_filter_backtest.py` and the `scan.py` regime board universe-wide.
- Run `validation.py` on Regime Dip v1 across the universe — settle whether the
  promoted edge actually survives deflation. If it does not, demote it. Honesty first.
- Journal every trade (thesis, ticket, outcome, grade). Build the expectancy record.
- Milestone to exit Phase 0: 20+ logged trades and a measured, deflation-tested
  expectancy on at least one edge.

### Phase 1 — $1,000 to $5,000 : Breadth (a portfolio of edges)
Core insight from the scaling model: one thin edge yields under 2%/yr at ANY size.
The business is breadth — a stable of decorrelated, individually-gated edges.
- Validate 3 to 5 edges across distinct behaviors: mean-reversion dip (RD-v1),
  trend continuation, volatility-regime expansion, cross-sectional relative strength.
- Each must clear `validation.py` independently before it trades a dollar.
- Combine only edges that are lowly correlated — that is where the free lunch is.
- Begin reverting sizing from micro-aggressive toward the 0.25% institutional floor.

### Phase 2 — $5,000 to $25,000 : The structural edge (options income)
At this capital the most durable, mathematically-grounded edge finally becomes
sizable and it fits a Level 2 cash account natively:
- Volatility risk premium harvesting via cash-secured puts and covered calls
  (implied vol persistently exceeds realized vol). Collateral becomes affordable here.
- Full scheduled automation of the loop (pre-open scan, intraday window, post-close review).
- Institutional 0.25% risk sizing throughout.

### Phase 3 — $25,000+ : Richer data + advanced models + track record
- Authorize deeper feeds (FMP for Commitment-of-Traders and options data; IBKR for
  deeper price history) as research inputs. Execution stays on the approved account.
- Options-flow (put/call, OI change, IV skew), cross-sectional PCA residual reversion,
  HMM regime allocation across the edge portfolio.
- The desk is now a documented, reproducible track record — the asset that feeds the
  Ivy application narrative and any future fund conversation. Evidence over folklore.

## Weekly operating cadence

- Daily (market days): pre-open scan (`scan.py`), intraday window monitor, post-close
  review and journal. Overwrite the regime map.
- Weekly: one research sprint — one new edge hypothesis written as measurable rules and
  pushed through the validation gate. Review the registry; retire anything decaying.
- Monthly: expectancy and drawdown review across all live edges; correlation check;
  confirm no edge is quietly rotting.

## Guardrails (non-negotiable)

Capital survival first. Hard caps and kill switches always apply and are never loosened
by a win streak: max loss per trade, daily/weekly loss halts, drawdown kill switch,
3-consecutive-loss cooldown, no market orders except emergency exits, no averaging down,
no revenge trading. If data is stale, the broker is degraded, or an order status is
ambiguous — stop and reconcile before acting.

## Immediate next steps (the next five moves)

1. Build the 13-name, 13-month CSV data layer (`market_data.py`): in Cowork I pull each
   name's daily bars via the Robinhood connector and write `data/<SYMBOL>.csv`; or run
   `market_data.py` once with your Robinhood token in the repo/CI. This unlocks the full
   Hurst/GARCH board and the universe-wide backtests.
2. Run `flow_filter_backtest.py` on the full universe; feed each variant's trades through
   `validation.evaluate()` with the correct trial count. Decide the OBV/CMF veto's fate.
3. Run the same deflation test on Regime Dip v1. Confirm or demote it honestly in the registry.
4. Stand up a trade journal (one row per trade: ticket, thesis, grade, R) and start logging.
5. Schedule the daily loop (pre-open / intraday / post-close) once an edge is PAPER-ELIGIBLE.

Bring the ambition of Alexander and the discipline of Aurelius to the same desk:
aim at owning the whole game, and never let a single trade break the machine that wins it.
