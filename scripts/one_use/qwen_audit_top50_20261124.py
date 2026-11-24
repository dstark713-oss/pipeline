# scripts/one_use/qwen_audit_top50_v2_20261124.py
"""Point-in-time TOP50 audit: membership + full daily history. No panel-schema guessing."""
import os, sys, importlib.util, io, contextlib, math, time
import pandas as pd, numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASOF = pd.Timestamp("2026-11-24")
TDIR = os.path.join(ROOT, "data", "processed", "top50")
TARGETS = ["T","GCHE","POSI","CNRU","FIXR","SVCB","DOMRF"]
OFFER = 993.05; H = (1,5,20)

spec = importlib.util.spec_from_file_location("_qwen_b", os.path.join(ROOT,"scripts","dataset","05_build_top50_panel.py"))
mod = importlib.util.module_from_spec(spec); sys.modules["_qwen_b"]=mod
os.chdir(ROOT)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)
    source, dates = mod.load_source_data()
    daily, _ = mod.aggregate_boards(source)

def col(df, names):
    low = {str(c).lower(): c for c in df.columns}
    return next((low[k] for k in names if k in low), None)

dc, sc, cc = col(daily,["tradedate","date"]), col(daily,["secid","ticker"]), col(daily,["adjusted_close","close"])
wide = daily.pivot_table(index=dc, columns=sc, values=cc, aggfunc="last")
wide.index = pd.to_datetime(wide.index); wide = wide.sort_index()
wide = wide.loc[wide.index <= ASOF]

mem = pd.read_parquet(os.path.join(TDIR,"top50_membership.parquet"))
md, ms = col(mem,["tradedate","date"]), col(mem,["secid","ticker"])
mem[md] = pd.to_datetime(mem[md])
print("membership cols:", list(mem.columns), "| dates:", mem[md].nunique(), "| daily:", wide.shape)

mask = mem.assign(m=True).pivot_table(index=md, columns=ms, values="m", aggfunc="any")
mask = mask.reindex(index=wide.index, columns=wide.columns).fillna(False)

sma = wide.rolling(20).mean()
above = wide.gt(sma)
valid = mask & sma.notna() & wide.notna()
breadth = (above & mask).sum(axis=1) / valid.sum(axis=1).replace(0,np.nan)

v, a = int(valid.iloc[-1].sum()), int((above & mask).iloc[-1].sum())
print(f"BREADTH asof={str(wide.index[-1].date())} valid={v} above={a} pct={a/max(v,1)*100:.1f}%")
print("above:", ",".join(wide.columns[(above & mask).iloc[-1]]))
if v != 50 or a != 4: print("WARN: not 4/50 -> check adjusted vs raw / SMA window / membership asof")

ret = wide.pct_change()
idx = (1 + ret.where(mask).mean(axis=1)).cumprod()

def nw_slope_t(y,x,lag):
    y=np.asarray(y,float);x=np.asarray(x,float);m=~(np.isnan(y)|np.isnan(x));y,x=y[m],x[m];n=len(y)
    if n<30:return np.nan,np.nan,n
    X=np.column_stack([np.ones(n),x]);b=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@b
    Xe=X*e[:,None];S=Xe.T@Xe
    for l in range(1,lag+1):
        w=1-l/(lag+1);G=Xe[l:].T@Xe[:-l];S+=w*(G+G.T)
    A=np.linalg.inv(X.T@X);V=A@S@A;return b[1],b[1]/np.sqrt(max(V[1,1],1e-18)),n
def nw_mean_t(v,lag):
    v=np.asarray(v,float);v=v[~np.isnan(v)];n=len(v)
    if n<30:return np.nan,n
    mu=v.mean();e=v-mu;S=e@e
    for l in range(1,lag+1):
        w=1-l/(lag+1);S+=2*w*(e[l:]@e[:-l])
    return mu/np.sqrt(max(S,1e-18)/n),n

print("=== H1 breadth->fwd (PIT top50 EW index) ===")
for h in H:
    fwd=idx.pct_change(h).shift(-h)
    d=pd.concat({"b":breadth,"r":fwd},axis=1).dropna()
    ic=d["b"].corr(d["r"],method="spearman")
    beta,t,n=nw_slope_t(d["r"].values,d["b"].values,h)
    print(f"h={h:2} spearman={ic:+.3f} beta={beta:+.4f} NW_t={t:+.2f} n={n}")

dist=(wide-wide.rolling(20).mean())/wide.rolling(20).std()
vol=wide.pct_change().rolling(60).std()
print("=== H2 PIT cross-sectional rank IC ===")
for h in H:
    fwd=wide.pct_change(h).shift(-h)
    for name,feat in (("z_dist",dist),("vol60",vol)):
        a=feat.where(mask).rank(axis=1); b=fwd.where(mask).rank(axis=1)
        ics=a.corrwith(b,axis=1)
        ics=ics[valid.sum(axis=1)>=20].dropna()
        t,n=nw_mean_t(ics.values,h)
        print(f"h={h:2} {name:6} meanIC={ics.mean():+.4f} NW_t={t:+.2f} days={n}")

def metrics(c):
    c=c.dropna()
    if len(c)<70:return None
    s=c.rolling(20).mean();sd=c.rolling(20).std();rv=c.pct_change().rolling(60).std()*math.sqrt(252)
    return dict(close=round(c.iloc[-1],3),dd60=round((c.iloc[-1]/c.rolling(60).max().iloc[-1]-1)*100,2),
                z20=round((c.iloc[-1]-s.iloc[-1])/sd.iloc[-1],2),rv60=round(rv.iloc[-1]*100,2),
                vperc=round(rv.rank(pct=True).iloc[-1]*100,1))
print("=== SLICE ===")
for t in TARGETS: print(f"{t:6}", metrics(wide[t]) if t in wide.columns else "absent")

print("=== LQDT (ISS) ===")
try:
    import requests; got=None
    for board in ("TQTF","TQIF","TQBR"):
        url=f"https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/{board}/securities/LQDT.json"
        start,rows,cols=0,[],None
        while True:
            r=requests.get(url,params={"from":"2026-08-01","till":"2026-11-24","start":start,"iss.meta":"off","history.columns":"TRADEDATE,CLOSE"},timeout=20)
            if r.status_code!=200:break
            blk=r.json().get("history",{});data=blk.get("data",[])
            if not data:break
            cols=blk.get("columns",cols);rows+=data
            if len(data)<100:break
            start+=len(data);time.sleep(0.1)
        if rows:
            df=pd.DataFrame(rows,columns=cols)
            c=pd.Series(pd.to_numeric(df["CLOSE"],errors="coerce").values,index=pd.to_datetime(df["TRADEDATE"])).sort_index()
            got=(board,c);break
    if got:
        board,c=got;print("board:",board,"last:",str(c.index[-1].date()))
        for h in H:
            if len(c)>h:print(f"{h:2}d {(c.iloc[-1]/c.iloc[-1-h]-1)*100:.4f}%")
    else: print("ISS fail; approx 14% (NOT actual): 1d~0.0556% 5d~0.278% 20d~1.11%")
except Exception as e: print("LQDT err:",type(e).__name__,"| approx 14%: 1d~0.0556% 5d~0.278% 20d~1.11%")

if "CNRU" in wide.columns:
    p=wide["CNRU"].dropna().iloc[-1]
    print(f"CNRU close={p:.2f} offer={OFFER} gross_spread={(OFFER/p-1)*100:.2f}% (deal risk unpriced)")
print("rule: |IC|<0.05 or |NW_t|<2 => not validated; no veto/edge from it.")