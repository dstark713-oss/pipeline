from __future__ import annotations
import argparse, json, logging, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, precision_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[3]
PANEL = ROOT / "data/processed/top50/top50_panel.parquet"
DB = ROOT / "data/processed/moex_daily_adjusted.sqlite"
OUT = ROOT / "data/interim/model1_replication"
TABLE = "adjusted_daily_bars"
BOARDS = ("TQBR", "EQBR")
EXCLUDED = {"GAZC", "GAZS", "GAZT"}
SUSPENSION = ("2022-02-28", "2022-03-23")
PRIORITY = {"TQBR": 0, "EQBR": 1}

# Frozen values copied from model1/configs/*.yaml.
FCFG = {
 "trend":{"ema_periods":[10,20,50,100,200],"momentum_periods":[5,10,20,60],"adx_period":14},
 "volatility":{"atr_period":14,"rv_windows":[10,20,60],"vol_exp_window":20},
 "volume":{"rel_vol_window":20,"vol_shock_window":20,"vol_shock_z":2.0},
 "oscillators":{"rsi_period":14,"stoch_k":14,"stoch_d":3,"macd_fast":12,"macd_slow":26,"macd_signal":9},
 "price_action":{"breakout_window":20},
}
TARGET = {"h":5,"k_tp":1.5,"k_sl":1.0,"vol_window":20}
CAT = {"iterations":500,"depth":6,"learning_rate":0.05,"l2_leaf_reg":3.0,
       "min_data_in_leaf":20,"loss_function":"Logloss","eval_metric":"Logloss",
       "random_seed":42,"verbose":False,"allow_writing_files":False}
WF = {"pretrain_years":3,"retrain_months":6,"purge_days":10,"window":"expanding","test_months":6}
PORT = {"n_grid":[4,5,6,7,8],"threshold":0.0,"corr_window":20,"corr_threshold":0.8,"breadth_ema":20}
COSTS = {"entry_bps":3,"exit_bps":3}
DROP = {"date","tradedate","secid","open","high","low","close","volume","value",
        "entry_date","entry","tp","sl","sigma","tp_hit","sl_hit","timeout","ambiguous"}

def log(s): print(f"[{datetime.now():%H:%M:%S}] {s}", flush=True)

def ro(path):
    c=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True); c.execute("PRAGMA query_only=ON"); return c

def load_panel():
    if not PANEL.is_file(): raise FileNotFoundError(PANEL)
    p=pd.read_parquet(PANEL)
    req={"tradedate","secid","bar_available","ranking_asof_date"}
    if req-set(p): raise RuntimeError(f"TOP50 panel missing {sorted(req-set(p))}")
    p["tradedate"]=pd.to_datetime(p.tradedate,errors="coerce")
    p["ranking_asof_date"]=pd.to_datetime(p.ranking_asof_date,errors="coerce")
    p["secid"]=p.secid.astype(str).str.strip().str.upper()
    p["bar_available"]=pd.to_numeric(p.bar_available,errors="coerce").fillna(0).astype(int)
    p=p.dropna(subset=["tradedate","ranking_asof_date","secid"])
    p=p[~p.secid.isin(EXCLUDED)].copy()
    if p.duplicated(["tradedate","secid"]).any(): raise RuntimeError("Duplicate PIT date/SECID rows")
    if not (p.ranking_asof_date<p.tradedate).all(): raise RuntimeError("PIT ranking date is not strictly before signal date")
    if (p.groupby("tradedate").secid.nunique()>50).any(): raise RuntimeError("More than 50 PIT members on a date")
    p=p[p.bar_available.eq(1)][["tradedate","secid","ranking_asof_date"]].drop_duplicates()
    if p.empty: raise RuntimeError("No PIT rows with bar_available=1")
    log(f"PIT rows={len(p):,}; dates={p.tradedate.nunique():,}; SECIDs={p.secid.nunique():,}")
    return p

def load_history(secids):
    chunks=[]
    with ro(DB) as c:
        cols={r[1].lower() for r in c.execute(f'PRAGMA table_info("{TABLE}")')}
        req={"secid","tradedate","boardid","adjusted_open","adjusted_high","adjusted_low","adjusted_close","adjusted_volume","value"}
        if req-cols: raise RuntimeError(f"Adjusted table missing {sorted(req-cols)}")
        for k in range(0,len(secids),400):
            batch=secids[k:k+400]; q=",".join("?" for _ in batch); b=",".join("?" for _ in BOARDS)
            sql=f"""SELECT UPPER(TRIM(secid)) secid,tradedate,UPPER(TRIM(boardid)) boardid,
            adjusted_open,adjusted_high,adjusted_low,adjusted_close,adjusted_volume,value
            FROM "{TABLE}" WHERE UPPER(TRIM(secid)) IN ({q}) AND UPPER(TRIM(boardid)) IN ({b})
            AND tradedate IS NOT NULL ORDER BY secid,tradedate,boardid"""
            x=pd.read_sql_query(sql,c,params=[*batch,*BOARDS])
            if not x.empty: chunks.append(x)
            log(f"History loaded {min(k+400,len(secids))}/{len(secids)} SECIDs")
    if not chunks: raise RuntimeError("No adjusted history")
    x=pd.concat(chunks,ignore_index=True); x["tradedate"]=pd.to_datetime(x.tradedate,errors="coerce")
    for col in ["adjusted_open","adjusted_high","adjusted_low","adjusted_close","adjusted_volume","value"]:
        x[col]=pd.to_numeric(x[col],errors="coerce")
    x=x.dropna(subset=["secid","tradedate","boardid"])
    x=x[~x.secid.isin(EXCLUDED)]
    x=x[(x.tradedate<pd.Timestamp(SUSPENSION[0]))|(x.tradedate>pd.Timestamp(SUSPENSION[1]))]
    if x.duplicated(["secid","tradedate","boardid"]).any(): raise RuntimeError("Duplicate SECID/date/board rows")
    # Activity sums across boards; OHLC uses one complete TQBR-first, EQBR-fallback row.
    a=x.groupby(["secid","tradedate"],as_index=False).agg(
        volume=("adjusted_volume",lambda s:s.sum(min_count=1)),
        value=("value",lambda s:s.sum(min_count=1)))
    px=["adjusted_open","adjusted_high","adjusted_low","adjusted_close"]
    x["_valid"]=x[px].notna().all(axis=1).astype(int); x["_priority"]=x.boardid.map(PRIORITY).fillna(999)
    x=x.sort_values(["secid","tradedate","_valid","_priority","boardid"],
                    ascending=[True,True,False,True,True],kind="mergesort")
    x=x.drop_duplicates(["secid","tradedate"])[["secid","tradedate",*px]]
    d=a.merge(x,on=["secid","tradedate"],validate="one_to_one")
    d=d.dropna(subset=px)
    d=d.rename(columns=dict(zip(px,["open","high","low","close"])))
    d=d[(d[["open","high","low","close"]]>0).all(axis=1)]
    if d.duplicated(["secid","tradedate"]).any(): raise RuntimeError("Duplicate daily bars after board aggregation")
    return d.sort_values(["secid","tradedate"]).reset_index(drop=True)

def ema(s,p): return s.ewm(span=p,adjust=False,min_periods=p).mean()
def truerange(d):
    pc=d.close.shift(1)
    return pd.concat([d.high-d.low,(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
def rolling_slope(s,w):
    a=s.to_numpy(float); out=np.full(len(a),np.nan)
    if len(a)>=w:
        x=np.arange(w,dtype=float); xc=x-x.mean(); den=(xc**2).sum()
        win=np.lib.stride_tricks.sliding_window_view(a,w)
        out[w-1:]=((win-win.mean(axis=1,keepdims=True))*xc).sum(axis=1)/den
    return pd.Series(out,index=s.index)

def features(frame):
    o=frame.copy().set_index("tradedate").sort_index(); c=o.close; v=o.volume
    for p in FCFG["trend"]["ema_periods"]:
        e=ema(c,p); o[f"ema_{p}"]=e; o[f"dist_ema_{p}"]=(c-e)/e
        o[f"close_above_ema_{p}"]=(c>e).astype("Int8"); o[f"ema_{p}_slope"]=e.diff()
    for p in FCFG["trend"]["momentum_periods"]: o[f"mom_{p}"]=c.pct_change(p)
    p=FCFG["trend"]["adx_period"]; up=o.high.diff(); down=-o.low.diff()
    plus=np.where((up>down)&(up>0),up,0.); minus=np.where((down>up)&(down>0),down,0.)
    tr=truerange(o); atr=tr.ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    pdi=100*pd.Series(plus,index=o.index).ewm(alpha=1/p,adjust=False,min_periods=p).mean()/atr
    mdi=100*pd.Series(minus,index=o.index).ewm(alpha=1/p,adjust=False,min_periods=p).mean()/atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    o["plus_di"]=pdi; o["minus_di"]=mdi; o["adx"]=dx.ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    p=FCFG["volatility"]["atr_period"]; o[f"atr_{p}"]=truerange(o).ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    o[f"atr_pct_{p}"]=o[f"atr_{p}"]/c
    r=c.pct_change()
    for w in FCFG["volatility"]["rv_windows"]: o[f"rv_{w}"]=r.rolling(w,min_periods=w).std()*np.sqrt(252)
    w=FCFG["volatility"]["vol_exp_window"]
    o["vol_expansion"]=r.rolling(w,min_periods=w).std()/r.rolling(w*3,min_periods=w*3).std().replace(0,np.nan)
    w=FCFG["volume"]["rel_vol_window"]; avg=v.rolling(w,min_periods=w).mean()
    o["rel_volume"]=v/avg.replace(0,np.nan); o["volume_trend"]=rolling_slope(v,w)
    w=FCFG["volume"]["vol_shock_window"]; vm=v.rolling(w,min_periods=w).mean(); vs=v.rolling(w,min_periods=w).std()
    o["volume_zscore"]=(v-vm)/vs.replace(0,np.nan)
    o["volume_shock"]=(o.volume_zscore>=FCFG["volume"]["vol_shock_z"]).astype("Int8")
    p=FCFG["oscillators"]["rsi_period"]; delta=c.diff()
    ag=delta.clip(lower=0).ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    al=(-delta.clip(upper=0)).ewm(alpha=1/p,adjust=False,min_periods=p).mean()
    o["rsi"]=100-100/(1+ag/al.replace(0,np.nan))
    k,d=FCFG["oscillators"]["stoch_k"],FCFG["oscillators"]["stoch_d"]
    lo=o.low.rolling(k,min_periods=k).min(); hi=o.high.rolling(k,min_periods=k).max()
    o["stoch_k"]=100*(c-lo)/(hi-lo).replace(0,np.nan); o["stoch_d"]=o.stoch_k.rolling(d,min_periods=d).mean()
    f=ema(c,FCFG["oscillators"]["macd_fast"]); s=ema(c,FCFG["oscillators"]["macd_slow"]); m=f-s
    sig=m.ewm(span=FCFG["oscillators"]["macd_signal"],adjust=False,min_periods=FCFG["oscillators"]["macd_signal"]).mean()
    o["macd"]=m; o["macd_signal"]=sig; o["macd_hist"]=m-sig
    w=FCFG["price_action"]["breakout_window"]
    o["rolling_high"]=o.high.rolling(w,min_periods=w).max(); o["rolling_low"]=o.low.rolling(w,min_periods=w).min()
    o["dist_to_high"]=(o.rolling_high-c)/c; o["dist_to_low"]=(c-o.rolling_low)/c
    o["breakout_up"]=(c>=o.rolling_high).astype("Int8"); o["breakout_down"]=(c<=o.rolling_low).astype("Int8")
    rng=(o.high-o.low).replace(0,np.nan); o["body"]=(c-o.open)/rng
    o["upper_wick"]=(o.high-o[["open","close"]].max(axis=1))/rng
    o["lower_wick"]=(o[["open","close"]].min(axis=1)-o.low)/rng
    return o

def triple_barrier(frame):
    d=frame.set_index("tradedate").sort_index(); h=TARGET["h"]
    sigma=d.close.pct_change().rolling(TARGET["vol_window"],min_periods=TARGET["vol_window"]).std()*np.sqrt(h)
    entry=d.open.shift(-1); entry_date=pd.Series(d.index,index=d.index).shift(-1)
    tp=entry*(1+TARGET["k_tp"]*sigma); sl=entry*(1-TARGET["k_sl"]*sigma)
    n=len(d); high=d.high.to_numpy(); low=d.low.to_numpy(); op=d.open.to_numpy()
    ev,tpv,slv=entry.to_numpy(),tp.to_numpy(),sl.to_numpy()
    th=np.zeros(n); sh=np.zeros(n); timeout=np.zeros(n,dtype=bool); ambs=np.zeros(n,dtype=bool)
    for i in range(n):
        if np.isnan(ev[i]) or np.isnan(tpv[i]) or np.isnan(slv[i]): th[i]=sh[i]=np.nan; continue
        start,end=i+1,min(i+1+h,n)
        if start>=n: th[i]=sh[i]=np.nan; continue
        t_hit=s_hit=amb=False
        for j in range(start,end):
            a=high[j]>=tpv[i] or (j==start and op[j]>=tpv[i])
            b=low[j]<=slv[i] or (j==start and op[j]<=slv[i])
            if a and b: amb=True; break
            if a: t_hit=True; break
            if b: s_hit=True; break
        if amb: ambs[i]=True; th[i]=sh[i]=np.nan
        elif t_hit: th[i],sh[i]=1.,0.
        elif s_hit: th[i],sh[i]=0.,1.
        else: timeout[i]=True; th[i]=sh[i]=0.
    return pd.DataFrame({"entry_date":entry_date,"entry":entry,"tp":tp,"sl":sl,
        "sigma":sigma,"tp_hit":th,"sl_hit":sh,"timeout":timeout,"ambiguous":ambs},index=d.index)

def build_dataset(panel,history):
    groups={k:g.sort_values("tradedate") for k,g in history.groupby("secid",sort=False)}
    chunks=[]; histories={}
    for i,secid in enumerate(sorted(panel.secid.unique()),1):
        px=groups.get(secid)
        if px is None or len(px)<300: log(f"SKIP {secid}: history < 300 bars"); continue
        histories[secid]=px
        f=features(px); t=triple_barrier(px); z=f.join(t)
        z["secid"]=secid; z["tradedate"]=z.index; chunks.append(z.reset_index(drop=True))
        if i%25==0: log(f"Features/labels {i}/{panel.secid.nunique()}")
    if not chunks: raise RuntimeError("No eligible histories")
    full=pd.concat(chunks,ignore_index=True)
    full=full.merge(panel[["tradedate","secid"]],on=["tradedate","secid"],how="inner",validate="one_to_one")
    full=full[~full.ambiguous].copy()
    cols=[c for c in full if c not in DROP and pd.api.types.is_numeric_dtype(full[c])]
    before=len(full); full=full.dropna(subset=cols+["tp_hit","sl_hit"])
    full=full.loc[np.isfinite(full[cols].to_numpy(float)).all(axis=1)].copy()
    log(f"Model rows={len(full):,}/{before:,}; features={len(cols)}")
    if full.empty: raise RuntimeError("No rows after warmup/label validation")
    return full.sort_values(["tradedate","secid"]).reset_index(drop=True),cols,histories

def folds(dates):
    dates=pd.DatetimeIndex(sorted(pd.to_datetime(dates).unique()))
    if dates.empty:return []
    first=dates.min()+pd.DateOffset(years=WF["pretrain_years"]); last=dates.max()
    out=[]; start=first; i=0
    while start<=last:
        boundary=min(start+pd.DateOffset(months=WF["test_months"]),last+pd.Timedelta(days=1))
        train_start=dates.min() if WF["window"]=="expanding" else start-pd.DateOffset(years=3)
        cutoff=start-pd.Timedelta(days=WF["purge_days"])
        tr=dates[(dates>=train_start)&(dates<=cutoff)]; te=dates[(dates>=start)&(dates<boundary)]
        if not len(tr) or not len(te):break
        out.append({"fold_id":i,"train_start":tr.min(),"train_end":tr.max(),"test_start":te.min(),"test_end":te.max()})
        i+=1; start+=pd.DateOffset(months=WF["retrain_months"])
    return out

def metrics(y,p):
    y=np.asarray(y,dtype=int); p=np.asarray(p,dtype=float)
    if len(np.unique(y))<2:return {"n":len(y),"pos_rate":float(y.mean()) if len(y) else None}
    pred=(p>=.5).astype(int)
    return {"n":len(y),"pos_rate":float(y.mean()),"logloss":float(log_loss(y,p,labels=[0,1])),
        "roc_auc":float(roc_auc_score(y,p)),"pr_auc":float(average_precision_score(y,p)),
        "precision":float(precision_score(y,pred,zero_division=0)),
        "recall":float(recall_score(y,pred,zero_division=0)),"brier":float(brier_score_loss(y,p))}

def fit(X,y):
    m=CatBoostClassifier(**CAT); m.fit(X,y.astype(int)); return m

def probs(model,Xtr,ytr,Xte):
    raw=model.predict_proba(Xte)[:,1]
    cut=int(len(Xtr)*.8); pcal=model.predict_proba(Xtr.iloc[cut:])[:,1]
    # Faithful source behavior: calibration is fit on in-sample predictions from a model trained on all train rows.
    iso=IsotonicRegression(out_of_bounds="clip"); iso.fit(pcal,ytr.iloc[cut:].astype(int))
    return raw,iso.predict(raw)

def choose_n(train,cols):
    z=train.sort_values("tradedate"); cut=int(len(z)*.8); a,b=z.iloc[:cut],z.iloc[cut:]
    if b.empty:return 4
    tp=fit(a[cols],a.tp_hit); sl=fit(a[cols],a.sl_hit)
    v=b[["tradedate","secid"]].copy(); v["score"]=tp.predict_proba(b[cols])[:,1]*(1-sl.predict_proba(b[cols])[:,1])
    means={}
    for n in PORT["n_grid"]:
        ds=[float(g.sort_values("score",ascending=False).head(n).score.mean()) for _,g in v.groupby("tradedate") if len(g)]
        means[n]=float(np.mean(ds)) if ds else -np.inf
    return max(means,key=means.get) if any(np.isfinite(x) for x in means.values()) else 4

def run_fold(f,full,cols):
    tr=full[full.tradedate.between(f["train_start"],f["train_end"])].copy()
    te=full[full.tradedate.between(f["test_start"],f["test_end"])].copy()
    if tr.empty or te.empty:return {"fold_id":f["fold_id"],"skipped":True},pd.DataFrame()
    preds=[]; result={}
    for name,target in [("tp","tp_hit"),("sl","sl_hit")]:
        m=fit(tr[cols],tr[target]); raw,cal=probs(m,tr[cols],tr[target],te[cols])
        result[name]={"raw":metrics(te[target],raw),"calibrated":metrics(te[target],cal)}
        preds.append(pd.DataFrame({"tradedate":te.tradedate.to_numpy(),"secid":te.secid.to_numpy(),
            f"p_{name}":cal,f"p_{name}_raw":raw,target:te[target].to_numpy()}))
    p=preds[0].merge(preds[1],on=["tradedate","secid"],validate="one_to_one")
    n=choose_n(tr,cols)
    return {"fold_id":f["fold_id"],"train_rows":len(tr),"test_rows":len(te),
        "train_start":str(f["train_start"].date()),"train_end":str(f["train_end"].date()),
        "test_start":str(f["test_start"].date()),"test_end":str(f["test_end"].date()),
        "n_star":n,"tp":result["tp"],"sl":result["sl"]},p

def backtest(preds,panel,histories,fold_results):
    closes={k:g.set_index("tradedate").close.sort_index() for k,g in histories.items()}
    opens={k:g.set_index("tradedate").open.sort_index() for k,g in histories.items()}
    returns=pd.DataFrame({k:s.pct_change() for k,s in closes.items()}).sort_index()
    emas={k:ema(s,PORT["breadth_ema"]) for k,s in closes.items()}
    breadth={}
    for date,members in panel.groupby("tradedate"):
        flags=[]
        for ticker in members.secid:
            s=closes.get(ticker); e=emas.get(ticker)
            if s is not None and date in s.index and pd.notna(e.get(date)): flags.append(s.get(date)>e.get(date))
        breadth[pd.Timestamp(date)]=float(np.mean(flags)) if flags else 0.
    periods=[(pd.Timestamp(f["test_start"]),pd.Timestamp(f["test_end"]),f["n_star"])
             for f in fold_results if not f.get("skipped")]
    current=pd.Series(dtype=float); rows=[]
    for date in sorted(pd.to_datetime(preds.tradedate.unique())):
        day=preds[pd.to_datetime(preds.tradedate).eq(date)].copy()
        n=next((n for a,b,n in periods if a<=date<=b),4)
        day["score"]=day.p_tp*(1-day.p_sl)
        cand=day.sort_values("score",ascending=False).set_index("secid")
        cand=cand[cand.score>PORT["threshold"]]; selected=[]
        if len(cand):
            corr=returns.loc[:date].tail(PORT["corr_window"]).corr()
            for ticker in cand.index:
                if len(selected)>=n:break
                if ticker not in corr.columns:continue
                if all(pd.isna(corr.loc[ticker,s]) or abs(corr.loc[ticker,s])<=PORT["corr_threshold"]
                       for s in selected if s in corr.columns):selected.append(ticker)
        exposure=breadth.get(pd.Timestamp(date),0.)
        target=pd.Series(exposure/len(selected),index=selected,dtype=float) if selected else pd.Series(dtype=float)
        idx=current.index.union(target.index); delta=target.reindex(idx,fill_value=0)-current.reindex(idx,fill_value=0)
        buys=float(delta.clip(lower=0).sum()); sells=float((-delta).clip(lower=0).sum())
        cost=(buys*COSTS["entry_bps"]+sells*COSTS["exit_bps"])/10000
        rows.append({"tradedate":pd.Timestamp(date),"target_weights":target.to_dict(),
            "turnover":buys+sells,"costs":cost,"exposure":float(target.sum()),"cash":1-float(target.sum())})
        current=target
    bt=pd.DataFrame(rows).set_index("tradedate").sort_index()
    calendar=pd.DatetimeIndex(sorted(set().union(*(set(s.index) for s in opens.values()))))
    gross=[]
    for date,row in bt.iterrows():
        i=calendar.searchsorted(date,side="right")
        if i+1>=len(calendar):gross.append(0.);continue
        t1,t2=calendar[i],calendar[i+1]; r=0.
        for ticker,w in row.target_weights.items():
            s=opens.get(ticker)
            if s is None:continue
            a,b=s.get(t1),s.get(t2)
            if pd.notna(a) and pd.notna(b) and a>0:r+=w*(b/a-1)
        gross.append(r)
    bt["ret_gross"]=gross; bt["ret_net"]=bt.ret_gross-bt.costs
    r=bt.ret_net.fillna(0.); eq=(1+r).cumprod(); dd=eq/eq.cummax()-1; sd=r.std()
    summary={"n_days":len(bt),"sharpe":float(r.mean()/sd*np.sqrt(252)) if len(r)>1 and sd>0 else None,
        "cagr":float((eq.iloc[-1]/eq.iloc[0])**(252/len(eq))-1) if len(eq) and eq.iloc[0]>0 else None,
        "mdd":float(dd.min()) if len(dd) else None,"total_return":float(eq.iloc[-1]/eq.iloc[0]-1) if len(eq) else None,
        "avg_turnover":float(bt.turnover.mean()),"total_costs":float(bt.costs.sum()),
        "avg_exposure":float(bt.exposure.mean()),"avg_cash":float(bt.cash.mean()),
        "holding_period_warning":"Inherited model1 backtest holds Open(t+1)->Open(t+2), one session, while Triple Barrier labels use H=5. Sharpe/CAGR/MDD are diagnostic only."}
    return bt,summary

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--skip-backtest",action="store_true"); args=ap.parse_args()
    panel=load_panel(); history=load_history(sorted(panel.secid.unique()))
    full,cols,histories=build_dataset(panel,history)
    wf=folds(pd.DatetimeIndex(full.tradedate.unique())); log(f"WF folds={len(wf)}")
    if not wf:raise RuntimeError("No WF folds: insufficient history for 3-year pretrain plus OOS.")
    results=[]; ps=[]
    for f in wf:
        r,p=run_fold(f,full,cols)
        if r.get("skipped"):continue
        results.append(r); p["fold_id"]=f["fold_id"]; ps.append(p)
        log(f"Fold {f['fold_id']} {r['test_start']}..{r['test_end']} TP AUC={r['tp']['calibrated'].get('roc_auc')} SL AUC={r['sl']['calibrated'].get('roc_auc')} N*={r['n_star']}")
    if not ps:raise RuntimeError("No OOS predictions")
    pred=pd.concat(ps,ignore_index=True); OUT.mkdir(parents=True,exist_ok=True)
    pred.to_parquet(OUT/"oos_predictions.parquet",index=False,compression="zstd")
    aggregate={"tp_raw":metrics(pred.tp_hit,pred.p_tp_raw),"tp_calibrated":metrics(pred.tp_hit,pred.p_tp),
        "sl_raw":metrics(pred.sl_hit,pred.p_sl_raw),"sl_calibrated":metrics(pred.sl_hit,pred.p_sl)}
    metadata={"created_utc":datetime.now(timezone.utc).isoformat(),"source":"dstark713-oss/model1",
        "universe":"PIT TOP50 membership on signal date, bar_available=1",
        "feature_count":len(cols),"feature_columns":cols,"target":TARGET,"catboost":CAT,"wf":WF,
        "calibration":"isotonic; faithfully reproduced in-sample calibration procedure",
        "calibration_warning":"Model fit on all train rows; calibrator fit on predictions for the last 20% of those same rows. Not an independent calibration sample.",
        "market_features":"model1/features/market.py is not wired into model1/features/pipeline.py, so not included.",
        "adaptations":["Adjusted SQLite adapter; TQBR-preferred complete OHLC, EQBR fallback; adjusted volume/value summed across boards.",
        "Full observed history used for warmup; only PIT TOP50 and bar_available=1 rows enter model sample; no forward fill.",
        "Breadth computed over PIT TOP50 membership on each signal date."],
        "known_source_quirks":["Breakout rolling high/low includes current bar; preserved.","N selection maximizes predicted score, not realized return; preserved.",
        "WF purge is 10 calendar days; preserved.","Adjacent OOS test blocks are made disjoint; model1 source used inclusive six-month endpoints, duplicating a boundary session when it was a trading day."],
        "backtest_warning":"Legacy backtest is one-session Open(t+1)->Open(t+2), inconsistent with H=5 Triple Barrier labels.",
        "signal_rows":len(full),"signal_dates":int(full.tradedate.nunique()),"secids":int(full.secid.nunique()),
        "folds":len(results),"oos_rows":len(pred)}
    (OUT/"wf_results.json").write_text(json.dumps({"folds":results,"aggregate_oos":aggregate},indent=2,ensure_ascii=False),encoding="utf-8")
    (OUT/"run_metadata.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    if not args.skip_backtest:
        bt,summary=backtest(pred,panel,histories,results)
        bt.reset_index().to_parquet(OUT/"backtest_daily.parquet",index=False,compression="zstd")
        (OUT/"backtest_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
        log(f"Legacy Sharpe={summary['sharpe']} CAGR={summary['cagr']} MDD={summary['mdd']}")
    log(f"COMPLETE: {OUT}")

if __name__=="__main__":main()
