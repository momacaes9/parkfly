#!/usr/bin/env python3
"""Fit the PARKING encoder on simulated training days; keep real brain wiring fixed.

No test outcomes enter parameter selection. Both encoders are then evaluated on
identical held-out days/masks. Confidence intervals resample whole simulated days.
"""
import itertools
import json
from pathlib import Path
import numpy as np
import model, senses
from common import jload, jdump, ROOT
from evaluate import load
from simulate_drivers import simulate_day, TRAIN_WEEKDAY

PCTS=[0,5,10,15,20,25,30,40,50,75,100]
FIELDS=['walk_scale','uncertainty_gain','loom_gain','near_full_gain']
GRID=list(itertools.product([2.,4.,8.],[.5,1.,2.],[.25,.5,1.],[0.,.5,1.]))


def interpolate(doc, mode, hz):
    """Vectorized form of the existing measured trilinear surface."""
    indices=[]; weights=[]
    for dim,name in enumerate(['sugar','bitter','loom']):
        axis=np.asarray(doc['grid'][name],float)
        v=np.clip(hz[...,dim],axis[0],axis[-1])
        i=np.clip(np.searchsorted(axis,v,side='right')-1,0,len(axis)-2)
        indices.append(i);weights.append((v-axis[i])/(axis[i+1]-axis[i]))
    result=np.zeros(hz.shape)
    for oi,name in enumerate(['mn9','giant_fibre','mdn']):
        table=np.asarray(doc[mode][name])
        for a,b,c in itertools.product([0,1],repeat=3):
            w=np.ones(hz.shape[:-1])
            for bit,f in zip([a,b,c],weights):w*=f if bit else 1-f
            result[...,oi]+=table[indices[0]+a,indices[1]+b,indices[2]+c]*w
    return result


def choose(reads,hz):
    mn,gf,md=reads[...,0],reads[...,1],reads[...,2]
    commit=(gf<senses.GF_DIVERT_HZ)&(md<=mn)&(mn>=senses.MN9_MIN_HZ)
    committing=commit.any(axis=-1)
    rest=gf<senses.GF_DIVERT_HZ
    rest=np.where(rest.any(axis=-1)[...,None],rest,True)
    allowed=np.where(committing[...,None],commit,rest)
    score=np.where(committing[...,None],mn-md,mn-md-gf)
    score=np.where(allowed,score,-np.inf)
    picks=np.lexsort((hz[...,0],score),axis=-1)[...,-1]
    return picks,committing


def encode(features, params=None):
    walk,price,free,unc,rise,pfull,near,availability=np.moveaxis(features,-1,0)
    if params is None:
        sugar=(1-np.exp(-free/senses.FREE_SCALE))*np.exp(-walk/senses.WALK_SCALE_MIN)
        bitter=unc+price/senses.PRICE_FULL
        loom=np.minimum(1,np.maximum(rise,0)/senses.RISE_FULL)+pfull
    else:
        w,u,l,n=params
        sugar=availability*np.exp(-walk/w)
        bitter=u*unc+price/senses.PRICE_FULL
        loom=l*np.maximum(rise,0)/senses.RISE_FULL+n*near
    return np.stack([200*np.clip(sugar,0,1),150*np.clip(bitter,0,1),50*np.clip(loom,0,1)],axis=-1)


def examples(lots,truth,days,geo,pcts,mask_seed):
    fit=truth['fitted'];N=[l['spaces'] for l in lots];T=truth['n_steps']
    S=[ [model.occ_matrix(N[i],fit['tau'][i][p]) for i in range(len(N))] for p in [0,1] ]
    mu=np.array(fit['prior']['weekday']['mu']);sd=np.array(fit['prior']['weekday']['sd'])
    across={'D':np.array(fit['across']['D']),'rho0':fit['across']['rho0'],'ell':fit['across']['ell_m']}
    cand=[i for i,l in enumerate(lots) if not l['pay']]
    feats=[];actual=[];groups=[];coverage=[]
    times=[t for t in range(T) if 450<=truth['start_min']+t*truth['step_min']<=1020 and (truth['start_min']+t*truth['step_min'])%15==0]
    for pct in pcts:
        rng=np.random.default_rng(mask_seed+pct)
        for di,d in enumerate(days):
            for ti in times:
                masks=[model.place('scatter',round(pct*N[i]/100),geo[i]['xy'],geo[i]['ent_d'],N[i],rng) for i in range(len(N))]
                occs=[d['occ'][i][ti] for i in range(len(N))]
                ss=S[int(truth['start_min']+ti*truth['step_min']>=fit['tau_pm_from_min'])]
                post=model.infer(ss,occs,masks,mu[:,ti],sd[:,ti],across)
                row=[]
                for i in cand:
                    rise=mu[i,min(ti+3,T-1)]-mu[i,ti]
                    t=senses.tastes(N[i],post[i]['p_occ'],post[i]['post'],ss[i],masks[i],occs[i],lots[i]['walk_min'],lots[i]['price_hr'],0,rise)
                    row.append([lots[i]['walk_min'],lots[i]['price_hr'],t['e_free'],t['uncertainty'],rise,t['p_full'],t['near_full'],t['availability']])
                feats.append(row);actual.append([bool((~occs[i]).any()) for i in cand]);groups.append(di);coverage.append(pct)
    return np.asarray(feats),np.asarray(actual),np.asarray(groups),np.asarray(coverage),cand


def outcomes(picks,actual,walk):
    rows=np.arange(len(actual));ok=actual[rows,picks]
    oracle=np.argmin(np.where(actual,walk[None,:],np.inf),axis=1)
    # If every candidate is full, match evaluate.py's closest-lot fallback.
    oracle=np.where(actual.any(axis=1),oracle,int(np.argmin(walk)))
    minutes=np.where(ok,walk[picks],5+walk[oracle])
    return ok.astype(float),minutes,oracle


def interval(values, groups, rng):
    per_day=np.array([values[groups==g].mean() for g in np.unique(groups)])
    resampled=per_day[rng.integers(0,len(per_day),(2000,len(per_day)))].mean(axis=1)
    return [float(x) for x in np.quantile(resampled,[.025,.975])]


def main():
    lots,truth,test_days,geo=load();test_days=[d for d in test_days if d['day']=='weekday']
    train=[]
    for seed in TRAIN_WEEKDAY:
        occ,_=simulate_day(lots,jload('lots.json')['dest'],seed,'weekday')
        train.append({'day':'weekday','occ':occ,'seed':seed})
    F,Y,G,P,cand=examples(lots,truth,train,geo,[0,10,25,50],17000)
    surface=jload('fly_surface.json');walk=np.array([lots[i]['walk_min'] for i in cand])
    candidates=[]
    for params in GRID:
        hz=encode(F,params);pick,comm=choose(interpolate(surface,'intact',hz),hz)
        ok,mins,_=outcomes(pick,Y,walk)
        candidates.append((float(ok.mean()),float(mins.mean()),params))
    selected=sorted(candidates,key=lambda r:(-r[0],r[1],r[2]))[0]
    params=selected[2]
    print('TRAIN encoder selected (test outcomes not used):',dict(zip(FIELDS,params)),selected[:2],flush=True)
    # Test data is read into the experiment only after fixing the selected encoder.
    F,Y,G,P,cand=examples(lots,truth,test_days,geo,PCTS,5000)
    raw=encode(F);cal=encode(F,params)
    raw_pick,raw_comm=choose(interpolate(surface,'intact',raw),raw)
    cal_pick,cal_comm=choose(interpolate(surface,'intact',cal),cal)
    les_pick,les_comm=choose(interpolate(surface,'lesion_gf',cal),cal)
    old_les_pick,old_les_comm=choose(interpolate(surface,'lesion_gf',raw),raw)
    _,_,oracle=outcomes(cal_pick,Y,walk)
    greedy=np.argmax(raw[...,0]/200-raw[...,1]/150-raw[...,2]/50,axis=1)
    policies={'calibrated':(cal_pick,cal_comm),'original':(raw_pick,raw_comm),
              'lesioned':(les_pick,les_comm),'original_lesioned':(old_les_pick,old_les_comm),'nearest':(np.full(len(Y),np.argmin(walk)),None),
              'greedy':(greedy,None),'oracle':(oracle,None)}
    output={};rng=np.random.default_rng(20261114)
    for name,(pick,comm) in policies.items():
        success,mins,_=outcomes(pick,Y,walk)
        out={k:[] for k in ['success','minutes','success_lo','success_hi','commit_rate']}
        for pct in PCTS:
            sel=P==pct;ci=interval(success[sel],G[sel],rng)
            out['success'].append(round(float(success[sel].mean()),4))
            out['minutes'].append(round(float(mins[sel].mean()),3))
            out['success_lo'].append(round(ci[0],4));out['success_hi'].append(round(ci[1],4))
            out['commit_rate'].append(round(float(comm[sel].mean()),4) if comm is not None else None)
        output[name]=out
    sel=P==25;new=outcomes(cal_pick,Y,walk)[0];old=outcomes(raw_pick,Y,walk)[0]
    ci=interval(new[sel]-old[sel],G[sel],rng)
    doc={'label':'SIMULATED held-out weekdays; original and calibrated encoder use identical observations. Real v783 connectome is unchanged.',
         'encoder':dict(zip(FIELDS,params)),'pcts':PCTS,'policies':output,
         'provenance':{'train_seeds':TRAIN_WEEKDAY,'test_seeds':[d['seed'] for d in test_days],
                       'training_pcts':[0,10,25,50],'candidates':len(GRID),'training_decisions':len(train)*39*4,
                       'objective':'maximize training free-spot success, then minimize walk + 5-minute failure penalty',
                       'test_decisions_per_pct':int(sel.sum()),'mask_seed':5000,'bootstrap_seed':20261114,
                       'confidence':'95% percentile interval from 2000 resamples of whole test days; only four simulated days',
                       'script':'pipeline/calibrate_fly.py','brain':'existing measured intact and GF-input-lesioned v783 surface; weights not trained',
                       'persona':'C-permit commuter to Hunt Library; no live traffic'},
         'gain_at_25':{'percentage_points':float(100*(new[sel]-old[sel]).mean()),'lo_pp':100*ci[0],'hi_pp':100*ci[1]},
         'limitations':['Occupancy is simulated, not live NCSU observations.','Training prioritizes avoiding full lots; walking time can increase.',
                        'Bootstrap intervals are descriptive over only four simulated test days.','No calibrated visitor or real-traffic accuracy claim.']}
    jdump(doc,'fly_calibration.json')
    for name,vals in output.items():
        i=PCTS.index(25);print(name,'success@25',vals['success'][i],'minutes',vals['minutes'][i],flush=True)

if __name__=='__main__':main()
