# Strategy Registry

The single source of truth for every strategy the desk has touched. No strategy
reaches live size without a row here showing it cleared `validation.py`
(deflated Sharpe > 0.95, sample >= 30, positive out-of-sample). Winning streaks
never loosen a limit. Every repeated mistake becomes a rule.

Status ladder: `IDEA` -> `RESEARCH` -> `PAPER-ELIGIBLE` -> `LIVE (small)` -> `LIVE (full)` -> `RETIRED`.

| id | name | hypothesis | status | sample (n) | OOS | deflated-Sharpe | live-eligible? | notes |
|---|---|---|---|---|---|---|---|---|
| RD-v1 | Regime Dip v1 | Oversold RSI2<10 dips inside an uptrend (close>SMA10>SMA20) snap back | LIVE (small) — under review | thin | not confirmed | NOT RUN | yes, but under-supported | On-record +0.44R/PF2.09 is UNVERIFIED; independent backtest showed edge thin (+0.10-0.12R). Signal is very rare per-name (0 valid signals on SOFI in 8mo). Needs the deflation gate run on the full universe. |
| RR-v0 | Regime Rip Short v0 | Overbought RSI2>90 rips inside a downtrend (close<SMA10<SMA20) fade, via long puts only | RESEARCH | none | none | NOT RUN | NO | Short-side mirror. Cash account cannot short shares -> puts only. Unsizable under ~$49 premium at $215. Backtest before any use. |
| FLOW-veto | Order-flow veto (OBV/CMF) | Do not buy a dip while money is leaving (OBV falling / CMF<0) | RESEARCH (promising) | n=12 (SOFI pilot) | not confirmed | NOT RUN | NO (as overlay only) | Pilot: all 12 losing SOFI dips had falling OBV; veto blocked 100% of losers. Defensive overlay, not an alpha source. Run flow_filter_backtest.py universe-wide + deflate. |
| REGIME-filter | Hurst + GARCH regime layer | Only take mean-reversion trades when Hurst<0.5; size by GARCH vol-target | LIVE overlay (filter+sizer) | n/a (not a standalone signal) | n/a | n/a | yes, as filter only | regime_engine.py. Cannot generate trades or loosen caps; only shrinks/vetoes. Self-tested. |

## Promotion rule
A strategy moves one rung only on evidence:
- IDEA -> RESEARCH: written as measurable rules (entry, invalidation, stop, exit, sizing).
- RESEARCH -> PAPER-ELIGIBLE: `validation.evaluate()` returns PAPER-ELIGIBLE on the full universe (deflated for every variant tried).
- PAPER-ELIGIBLE -> LIVE (small): 20+ paper trades hold the expectancy; size at the floor of the risk policy.
- LIVE (small) -> LIVE (full): live expectancy matches backtest within tolerance over 30+ trades.
- any -> RETIRED: rolling expectancy decays below zero, or the edge's premise breaks. Retire fast; do not average down on a dying edge.
