#!/usr/bin/env python3
"""
validation.py  --  the anti-self-deception gate  (clean-room, zero dependencies)
Owen Crabbe / agentic-quant-lab

WHY THIS IS THE MOST IMPORTANT FILE IN THE REPO
  At our scale the enemy is not a shortage of strategies. It is fooling ourselves
  with strategies that only worked in the past by luck. Every idea we test looks
  good on SOME parameter set by chance. This module is the referee that decides
  whether a measured edge is real or noise, correcting for how many things we tried.

  Nothing gets promoted toward live trading until it clears this gate. Ever.

WHAT IT COMPUTES (all from the published mathematics, implemented ourselves)
  1. Sharpe ratio of a per-trade (or per-period) return series.
  2. Probabilistic Sharpe Ratio (PSR): P(true Sharpe > benchmark), adjusted for
     sample length, skew, and fat tails (Bailey & Lopez de Prado).
  3. Deflated Sharpe Ratio (DSR): PSR where the benchmark is raised to the expected
     maximum Sharpe you'd see from pure luck after K trials. This is the
     multiple-testing correction. DSR > 0.95 => the edge survives the number of
     things we tried.
  4. A verdict: REJECT / RESEARCH / PAPER-ELIGIBLE, combining DSR, sample size,
     and out-of-sample sign agreement.

Reference: Bailey & Lopez de Prado, "The Deflated Sharpe Ratio" (2014).
"""
import math

EULER = 0.5772156649015329

# ---- our own normal CDF / inverse CDF ----
def _phi(x):                      # standard normal CDF via stdlib erf
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def _phi_inv(p):                  # Acklam's rational approximation
    if p <= 0: return -1e9
    if p >= 1: return 1e9
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
    pl=0.02425
    if p < pl:
        q=math.sqrt(-2*math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1-pl:
        q=math.sqrt(-2*math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q=p-0.5; r=q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

def _moments(x):
    n=len(x); m=sum(x)/n
    s2=sum((xi-m)**2 for xi in x)/(n-1)
    s=math.sqrt(s2) if s2>0 else 0.0
    if s==0: return m,0.0,0.0,3.0
    sk=sum(((xi-m)/s)**3 for xi in x)/n
    ku=sum(((xi-m)/s)**4 for xi in x)/n     # non-excess kurtosis
    return m,s,sk,ku

def sharpe(returns):
    m,s,_,_=_moments(returns)
    return m/s if s>0 else 0.0

def psr(returns, benchmark_sr=0.0):
    """P(true Sharpe > benchmark_sr), skew/kurtosis-adjusted."""
    n=len(returns)
    if n<3: return None
    m,s,sk,ku=_moments(returns)
    sr=m/s if s>0 else 0.0
    denom=math.sqrt(max(1e-12, 1 - sk*sr + (ku-1)/4*sr*sr))
    return _phi((sr-benchmark_sr)*math.sqrt(n-1)/denom)

def expected_max_sharpe(num_trials, sr_variance):
    """E[max Sharpe] from pure luck after K independent trials (per-period units)."""
    K=max(2,num_trials); v=math.sqrt(max(1e-12,sr_variance))
    return v*((1-EULER)*_phi_inv(1-1.0/K) + EULER*_phi_inv(1-1.0/(K*math.e)))

def deflated_sharpe(returns, num_trials, sr_variance=None):
    """DSR: PSR against the luck-inflated benchmark. >0.95 => survives K trials."""
    n=len(returns)
    if n<3: return None
    sr=sharpe(returns)
    if sr_variance is None:
        sr_variance=(1+0.5*sr*sr)/n     # variance of a single Sharpe estimate (fallback)
    sr0=expected_max_sharpe(num_trials, sr_variance)
    return psr(returns, benchmark_sr=sr0)

def evaluate(returns, num_trials=1, oos_returns=None, min_trades=30):
    """Combine DSR + sample size + OOS sign into a promotion verdict."""
    n=len(returns)
    out={"n":n,"sharpe":round(sharpe(returns),3),
         "psr_vs0":round(psr(returns) or 0,3),
         "dsr":round(deflated_sharpe(returns,num_trials) or 0,3),
         "num_trials":num_trials}
    oos_ok=True
    if oos_returns is not None and len(oos_returns)>=5:
        out["oos_mean_R"]=round(sum(oos_returns)/len(oos_returns),3)
        oos_ok = out["oos_mean_R"]>0
    if n<min_trades:
        out["verdict"]="RESEARCH (sample too small: need %d+)"%min_trades
    elif (out["dsr"] or 0)<0.95:
        out["verdict"]="REJECT (edge not distinguishable from luck after %d trials)"%num_trials
    elif not oos_ok:
        out["verdict"]="REJECT (fails out-of-sample)"
    else:
        out["verdict"]="PAPER-ELIGIBLE (survives deflation + OOS; paper-trade before any live size)"
    return out

def _selftest():
    import random; random.seed(3)
    strong=[random.gauss(0.45,1.0) for _ in range(300)]   # strong edge, SR~0.45
    null  =[random.gauss(0.00,1.0) for _ in range(300)]   # pure noise
    print("SELF-TEST")
    print("  strong edge, K=20 trials:", evaluate(strong, num_trials=20,
          oos_returns=[random.gauss(0.30,1.0) for _ in range(60)]))
    print("  null series, K=20 trials:", evaluate(null, num_trials=20,
          oos_returns=[random.gauss(0.00,1.0) for _ in range(60)]))

if __name__=="__main__":
    _selftest()
