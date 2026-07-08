#!/usr/bin/env python3
"""
run_validation.py  --  runs the deflation gate on the desk's strategies.
Owen Crabbe / agentic-quant-lab

Pipeline: load data/<SYMBOL>.csv (built by market_data.py) -> backtest each
strategy/veto across the universe -> pool trade R-multiples -> push through
validation.evaluate() (Deflated Sharpe, sample gate, out-of-sample sign).

Writes validation_results.json. This is what the GitHub Action runs after the
data pull, so the verdict is reproducible and versioned, not hand-computed.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flow_filter_backtest as B
import validation as V

# how many distinct variants the research program has tried (for honest deflation).
# baseline + 4 flow vetoes + RD-v1 parameter choices -> be generous, not flattering.
NUM_TRIALS = 8

def pooled_returns(data, veto):
    allR, isR, oosR = [], [], []
    for sym, bars in data.items():
        split = int(len(bars) * 0.6)
        for _win, R, idx in B.backtest(sym, bars, veto):
            allR.append(R)
            (isR if idx < split else oosR).append(R)
    return allR, isR, oosR

def main():
    data = B.load()
    if not data:
        print("No data/ CSVs. Run market_data.py first (needs a fetch source)."); return
    report = {"universe": sorted(data), "num_trials_assumed": NUM_TRIALS, "strategies": {}}
    for name, veto in B.VETOES.items():
        allR, isR, oosR = pooled_returns(data, veto)
        report["strategies"][name] = {
            "n_all": len(allR),
            "evaluation": V.evaluate(allR, num_trials=NUM_TRIALS, oos_returns=oosR, min_trades=30),
        }
    print(json.dumps(report, indent=2))
    with open("validation_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nwrote validation_results.json")

if __name__ == "__main__":
    main()
