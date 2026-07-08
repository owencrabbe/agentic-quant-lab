# Strategy Registry

The single source of truth for every strategy the desk has touched. No strategy
reaches live size without a row here showing it cleared `validation.py`
(deflated Sharpe > 0.95, sample >= 30, positive out-of-sample). Winning streaks
never loosen a limit. Every repeated mistake becomes a rule.

Status ladder: `IDEA` -> `RESEARCH` -> `PAPER-ELIGIBLE` -> `LIVE (small)` -> `LIVE (full)` -> `RETIRED`.

| id | name | hypothesis | status | sample (n) | OOS | deflated-Sharpe | live-eligible? | notes |
|---|---|---|---|---|---|---|---|---|
| RD-v1 | Regime Dip v1 | Oversold RSI2<10 dips inside an uptrend (close>SMA10>SMA20) snap back | RESEARCH (DEMOTED — unvalidated) | SOFI 13mo: strict n=0; relaxed n=12 | negative (OOS mean -0.066R) | DSR 0.025 (relaxed SOFI) | NO until it clears the universe gate | 2026-07-07 deflation test: strict gate produced ZERO signals on SOFI in 13mo; relaxed (RSI2<15) gave n=12, avgR -0.129, DSR 0.025, verdict RESEARCH (sample too small) + fails OOS. On-record +0.44R/PF2.09 remains UNVERIFIED. Demoted from LIVE to RESEARCH: paper/min-size only until run_validation.py passes it on the full 13-name universe. |
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
