---
name: agentic-trading-loop
description: The self-contained runbook the scheduled desk executes each session. Walks the full maker-checker-executor loop: observe, research, signal, risk-gate, execution-verify, place-or-reject, monitor, and log. Use this as the master checklist whenever a scheduled trading run fires or the user asks to run the loop.
---

# Agentic Trading Loop

A disciplined loop for a live, funded account. Capital survival beats activity. No trade is a valid and often the best output. Never claim guaranteed profit.

## 0. Preconditions

- Trade only the designated agentic account. Confirm it is the correct account before any order.
- Confirm the Robinhood MCP tools are responding and quotes are fresh. If anything is ambiguous, stand down and alert.

## 1. Observe

- Pull account value, buying power, settled vs unsettled cash, open positions, and open orders.
- Pull the watchlist and live quotes.
- Note the session window from the session-clock skill. If outside an edge window, go to Monitor only.

## 2. Research

- For each watchlist name compute the daily regime (close vs SMA10 vs SMA20).
- Check the earnings calendar and any major scheduled news for the day. Flag names reporting within the holding window as no-trade.

## 3. Signal

- Apply the regime-filtered-momentum skill. Generate at most a few candidate tickets, each with entry, stop, target, direction, and size.
- Always include the no-trade alternative and prefer it when setups are marginal.

## 4. Risk gate (independent)

- Reject or resize against fixed-dollar guardrails while equity is small: capped risk per position, capped concurrent positions, capped new trades per day, and a daily loss stop.
- If max loss is unknown or a stop cannot be enforced (for example a fractional share with no native stop and no monitoring plan), reject or switch to a defined-risk long option.
- Never loosen limits after a win streak.

## 5. Execution verify (independent)

- Confirm the asset, order type, and any option level are supported and permitted.
- Confirm buying power and settled cash. In a cash account, do not recycle unsettled proceeds into a same-day round trip (good-faith violation risk).
- Prefer limit orders. Check for duplicate or conflicting open orders. Use one intended order per setup.

## 6. Place or reject

- Place the live order only if Signal, Risk, and Execution all pass. Log the full ticket before sending and the result after.
- If any gate fails, reject and log the blocking reason.

## 7. Monitor

- Track fills, open risk, and PnL. Enforce manual exits for positions without a native stop.
- Watch kill-switch conditions: daily or weekly loss limits, drawdown from high-water mark, three consecutive losers, stale quotes, degraded broker connection, or an ambiguous order status. On any trigger, stop new entries, cancel resting entry orders, and alert.

## 8. Review and log

- Grade every closed trade on process and outcome separately. Record it.
- Add only testable lessons. Every repeated mistake becomes a rule.

## Output style

Lead with the action: PLACE, REJECT, MONITOR, HOLD, EXIT, or KILL SWITCH. Numbers first. For any live decision, show the ticket summary and the three independent approvals. No hype.
