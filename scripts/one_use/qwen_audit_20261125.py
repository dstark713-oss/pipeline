import os, sys, importlib.util, io, contextlib
import pandas as pd, numpy as np
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"..","..")); os.chdir(ROOT)
ASOF=pd.Timestamp("2026-11-25"); TDIR=os.path.join(ROOT,"data","processed","top50"); H=(1,5,20)
spec=importlib.util.spec_from_file_location("_b",os.path.join(ROOT,"scripts","dataset","05_build_top50_panel.py"))
m=importlib.util.module_from_spec(spec); sys.modules["_b"]=m
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(m); src,dates=m.load_source_data(); daily,_=m.aggregate_boards(src)
def col(d,ns):
    low={str(c).lower():c for c in d.columns}; return next((low[k] for k in ns if k in low),None)
dc,sc,cc=col(daily,["tradedate","date"]),col(daily,["secid","ticker"]),col(daily,["adjusted_close","close"])
w=daily.pivot_table(index=dc,columns=sc,values=cc,aggfunc="last"); w.index=pd.to_datetime(w.index); w=w.sort_index().loc[lambda d:d.index<=ASOF]
mem=pd.read_parquet(os.path.join(TDIR,"top50_membership.parquet")); md,ms=col(mem,["tradedate","date"]),col(mem,["secid","ticker"]); mem[md]=pd.to_datetime(mem[md])
mask=mem.assign(m=True).pivot_table(index=md,columns=ms,values="m",aggfunc="any").reindex(index=w.index,columns=w.columns).fillna(False)
sma=w.rolling(20).mean(); above=w.gt(sma); valid=mask&sma.notna()&w.notna()
breadth=(above&mask).sum(axis=1)/valid.sum(axis=1).replace(0,np.nan)
idx=(1+w.pct_change().where(mask).mean(axis=1)).cumprod(); b=float(breadth.iloc[-1])
print(f"asof={w.index[-1].date()} breadth={b:.3f} valid={int(valid.iloc[-1].sum())} above={int((above&mask).iloc[-1].sum())}")
def nw_ols(y,X,lag):
    y=np.asarray(y,float);X=np.asarray(X,float);k=~np.isnan(y)&~np.isnan(X).any(axis=1);y,X=y[k],X[k];n=len(y)
    A=np.linalg.inv(X.T@X);bb=A@X.T@y;e=y-X@bb;Xe=X*e[:,None];S=Xe.T@Xe
    for l in range(1,lag+1):
        ww=1-l/(lag+1);G=Xe[l:].T@Xe[:-l];S+=ww*(G+G.T)
    return bb,A@S@A,n
L={1:0.00037,5:0.00267,20:0.01086}  # 24.11 actual; REPLACE with 25.11
for h in H:
    fwd=idx.pct_change(h).shift(-h); d=pd.concat({"b":breadth,"r":fwd},axis=1).dropna()
    bb,V,n=nw_ols(d["r"].values,np.column_stack([np.ones(len(d)),d["b"].values]),h)
    c=np.array([1.,b]);mu=c@bb;se=np.sqrt(max(c@V@c,1e-18))
    print(f"h={h:2} E={mu*100:+.3f}% CI[{(mu-1.96*se)*100:+.3f},{(mu+1.96*se)*100:+.3f}] LQDT24={L[h]*100:.3f}% n={n}")
oil=["SIBN","TATN","LKOH","RNFT","ROSN","SNGS"]
r=w[oil].pct_change().tail(120)
print("OIL corr 120d:\n", r.corr().round(2).to_string())
if "X5" in w.columns:
    p=float(w["X5"].dropna().iloc[-1]); div=204.0; tax=0.13
    print(f"X5 close={p:.2f} div_yield={div/p*100:.2f}% net_div={div*(1-tax)/p*100:.2f}%")
    for gap in (0.0,0.5,1.0):
        net=(div*(1-tax)-gap*div)/p - L[20]
        print(f"  gap={gap*100:.0f}%div -> H20 net vs LQDT={net*100:+.2f}% (needs appreciation to beat)")