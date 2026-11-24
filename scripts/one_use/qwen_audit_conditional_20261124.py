# scripts/one_use/qwen_audit_conditional_20261124.py
import os, sys, importlib.util, io, contextlib, math, time
import pandas as pd, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASOF = pd.Timestamp("2026-11-24"); TDIR = os.path.join(ROOT,"data","processed","top50")
H=(1,5,20); OFFER=993.05
spec=importlib.util.spec_from_file_location("_qwen_b", os.path.join(ROOT,"scripts","dataset","05_build_top50_panel.py"))
mod=importlib.util.module_from_spec(spec); sys.modules["_qwen_b"]=mod; os.chdir(ROOT)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod); source,dates=mod.load_source_data(); daily,_=mod.aggregate_boards(source)
def col(df,names):
    low={str(c).lower():c for c in df.columns}; return next((low[k] for k in names if k in low),None)
dc,sc,cc=col(daily,["tradedate","date"]),col(daily,["secid","ticker"]),col(daily,["adjusted_close","close"])
wide=daily.pivot_table(index=dc,columns=sc,values=cc,aggfunc="last"); wide.index=pd.to_datetime(wide.index)
wide=wide.sort_index().loc[lambda d:d.index<=ASOF]
mem=pd.read_parquet(os.path.join(TDIR,"top50_membership.parquet")); md,ms=col(mem,["tradedate","date"]),col(mem,["secid","ticker"])
mem[md]=pd.to_datetime(mem[md])
mask=mem.assign(m=True).pivot_table(index=md,columns=ms,values="m",aggfunc="any").reindex(index=wide.index,columns=wide.columns).fillna(False)
sma=wide.rolling(20).mean(); above=wide.gt(sma); valid=mask&sma.notna()&wide.notna()
breadth=(above&mask).sum(axis=1)/valid.sum(axis=1).replace(0,np.nan)
idx=(1+wide.pct_change().where(mask).mean(axis=1)).cumprod()
b_cur=float(breadth.iloc[-1])
print("in_top50:", {t:bool(mask[t].iloc[-1]) for t in ["T","GCHE","POSI","CNRU","FIXR","SVCB","DOMRF"] if t in mask.columns})
print(f"breadth_cur={b_cur:.3f}")

def nw_ols(y,X,lag):
    y=np.asarray(y,float);X=np.asarray(X,float)
    m=~np.isnan(y)&~np.isnan(X).any(axis=1);y,X=y[m],X[m];n=len(y)
    A=np.linalg.inv(X.T@X);b=A@X.T@y;e=y-X@b;Xe=X*e[:,None];S=Xe.T@Xe
    for l in range(1,lag+1):
        w=1-l/(lag+1);G=Xe[l:].T@Xe[:-l];S+=w*(G+G.T)
    return b,A@S@A,n

# LQDT benchmark
lqdt={1:0.000556,5:0.00278,20:0.0111}; lqdt_src="approx14%(NOT actual)"
try:
    import requests, urllib3; urllib3.disable_warnings()
    for board in ("TQTF","TQIF","TQBR"):
        url=f"https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/{board}/securities/LQDT.json"
        start,rows,cols=0,[],None
        while True:
            r=requests.get(url,params={"from":"2026-08-01","till":"2026-11-24","start":start,"iss.meta":"off","history.columns":"TRADEDATE,CLOSE"},timeout=20,verify=False)
            if r.status_code!=200:break
            blk=r.json().get("history",{});data=blk.get("data",[])
            if not data:break
            cols=blk.get("columns",cols);rows+=data
            if len(data)<100:break
            start+=len(data);time.sleep(0.1)
        if rows:
            df=pd.DataFrame(rows,columns=cols)
            c=pd.Series(pd.to_numeric(df["CLOSE"],errors="coerce").values,index=pd.to_datetime(df["TRADEDATE"])).sort_index()
            for h in H:
                if len(c)>h:lqdt[h]=float(c.iloc[-1]/c.iloc[-1-h]-1)
            lqdt_src=f"ISS:{board} actual";break
except Exception as e: lqdt_src=f"approx14%(SSL {type(e).__name__})"
print("LQDT:",lqdt_src,{h:f"{lqdt[h]*100:.3f}%" for h in H})

print("=== H1 parametric E[fwd|breadth_cur] (NW 95%CI) ===")
for h in H:
    fwd=idx.pct_change(h).shift(-h)
    d=pd.concat({"b":breadth,"r":fwd},axis=1).dropna()
    b,V,n=nw_ols(d["r"].values,np.column_stack([np.ones(len(d)),d["b"].values]),h)
    c=np.array([1.0,b_cur]);mu=c@b;se=np.sqrt(max(c@V@c,1e-18))
    print(f"h={h:2} E={mu*100:+.3f}% CI[{(mu-1.96*se)*100:+.3f},{(mu+1.96*se)*100:+.3f}] LQDT={lqdt[h]*100:.3f}% n={n}")

print("=== Low-breadth regime mean fwd (NW 95%CI) + P(beat LQDT) ===")
for thr in (0.10,0.15):
    D=(breadth<=thr).astype(float)
    print(f"regime breadth<={thr:.2f}: days={int(D.sum())}")
    for h in H:
        fwd=idx.pct_change(h).shift(-h)
        d=pd.concat({"D":D,"r":fwd},axis=1).dropna()
        b,V,n=nw_ols(d["r"].values,np.column_stack([np.ones(len(d)),d["D"].values]),h)
        c=np.array([1.0,1.0]);mu=c@b;se=np.sqrt(max(c@V@c,1e-18))
        pb=float((d.loc[d["D"]==1,"r"]>lqdt[h]).mean())
        print(f"  h={h:2} mean={mu*100:+.3f}% CI[{(mu-1.96*se)*100:+.3f},{(mu+1.96*se)*100:+.3f}] P(>LQDT)={pb:.2f} n={n}")

print("=== CNRU breakeven close-prob (gross spread 9.39%) ===")
s=OFFER/float(wide["CNRU"].dropna().iloc[-1])-1
for dd in (0.03,0.05,0.08,0.10,0.15):
    print(f"  break_downside={dd*100:.0f}% -> p_be={dd/(s+dd)*100:.1f}%")
print("note: p_be gross; add LQDT carry over expected hold + cost. Deal risk unpriced.")