# Definitive: exact known columns. Validate RAW composite vs barrier outcomes. Read-only.
import pandas as pd, numpy as np
P = "data/interim/model1_replication/oos_predictions.parquet"
df = pd.read_parquet(P)
df["tradedate"] = pd.to_datetime(df["tradedate"])
df["comp_raw"] = df["p_tp_raw"] * (1.0 - df["p_sl_raw"])   # deployed score
df["comp_cal"] = df["p_tp"]     * (1.0 - df["p_sl"])       # comparison only
print("rows=%d dates=%d folds=%d" % (len(df), df.tradedate.nunique(), df.fold_id.nunique()))
print("tp_hit=%.3f sl_hit=%.3f both_hit_frac=%.4f" % (df.tp_hit.mean(), df.sl_hit.mean(), ((df.tp_hit+df.sl_hit)>1).mean()))
print("comp_raw min/mean/max=%.4f/%.4f/%.4f" % (df.comp_raw.min(), df.comp_raw.mean(), df.comp_raw.max()))

def auc(s, y):
    s=np.asarray(s,float); y=np.asarray(y,int)
    n1=(y==1).sum(); n0=(y==0).sum()
    if n1==0 or n0==0: return np.nan
    r=pd.Series(s).rank().values
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0)

for nm in ("comp_raw","comp_cal"):
    print("%s: AUC vs tp_hit=%.4f | AUC vs sl_hit=%.4f" % (nm, auc(df[nm],df.tp_hit), auc(df[nm],df.sl_hit)))

df["signed"] = df.tp_hit.astype(int) - df.sl_hit.astype(int)
def boot_ci(v, B=1000, bl=20, seed=0):
    v=np.asarray(v,float); v=v[~np.isnan(v)]; n=len(v)
    if n<30: return (np.nan,np.nan,n)
    rng=np.random.default_rng(seed); ms=[]
    for _ in range(B):
        idx=[]
        while len(idx)<n:
            s=rng.integers(0,max(1,n-bl)); idx+=list(range(s,min(n,s+bl)))
        ms.append(v[idx[:n]].mean())
    return (np.percentile(ms,2.5), np.percentile(ms,97.5), n)

for nm in ("comp_raw","comp_cal"):
    ics=[]
    for d,g in df.groupby("tradedate"):
        if g["signed"].nunique()>=2 and len(g)>=20:
            ics.append(g[nm].rank().corr(g["signed"].rank()))
    lo,hi,n=boot_ci(ics)
    print("%s vs signed(TP-SL): rankIC=%+.4f CI[%+.4f,%+.4f] dates=%d" % (nm, np.nanmean(ics), lo, hi, n))

df["dec"] = df.groupby("tradedate")["comp_raw"].transform(
    lambda x: pd.qcut(x.rank(method="first"),10,labels=False) if len(x)>=10 else np.nan)
print("decile mean signed:\n", df.groupby("dec")["signed"].mean().round(4).to_string())
print("decile tp_hit rate:\n", df.groupby("dec")["tp_hit"].mean().round(4).to_string())
print("decile sl_hit rate:\n", df.groupby("dec")["sl_hit"].mean().round(4).to_string())