#!/usr/bin/env python3
"""Export current posterior tastes for the standalone starter-compatible Colab."""
import json
from pathlib import Path
import numpy as np
from evaluate import load
import model
import senses


def main():
    lots, truth, days, geo = load()
    day = next(d for d in days if d['day'] == 'weekday')
    fit = truth['fitted']; ti = (10 * 60 - truth['start_min']) // truth['step_min']
    period = int(10 * 60 >= fit['tau_pm_from_min'])
    S = [model.occ_matrix(l['spaces'], fit['tau'][i][period]) for i,l in enumerate(lots)]
    rng = np.random.default_rng(25)
    masks = [model.place('scatter', round(.25*l['spaces']), geo[i]['xy'], geo[i]['ent_d'], l['spaces'],rng) for i,l in enumerate(lots)]
    occ = [day['occ'][i][ti] for i in range(len(lots))]
    P = fit['prior']['weekday']
    post = model.infer(S,occ,masks,np.array(P['mu'])[:,ti],np.array(P['sd'])[:,ti],
                       {'D':np.array(fit['across']['D']),'rho0':fit['across']['rho0'],'ell':fit['across']['ell_m']})
    calibration_path=Path(__file__).resolve().parents[1]/'web/data/fly_calibration.json'
    calibration=json.loads(calibration_path.read_text())['encoder'] if calibration_path.exists() else None
    out=[]
    for i,l in enumerate(lots):
        if l['pay']: continue
        rise = P['mu'][i][min(ti+3,truth['n_steps']-1)]-P['mu'][i][ti]
        t = senses.tastes(l['spaces'],post[i]['p_occ'],post[i]['post'],S[i],masks[i],occ[i],l['walk_min'],l['price_hr'],0,rise)
        sugar,bitter,loom=senses.calibrated_hz(t,l['walk_min'],l['price_hr'],0,rise,calibration) if calibration else senses.to_hz(t)
        out.append({'lot':l['name'],'walk_min':l['walk_min'],'sugar_hz':sugar,'bitter_hz':bitter,'looming_hz':loom})
    doc={'scenario':f"SIMULATED {day['id']}, 10:00, 25% scattered sensors, RNG 25",'persona':'commuter with a C permit, Hunt Library',
         'encoder':calibration or 'original','source':'Computed posterior from official NCSU capacity and simulated occupancy; no live sensor feed','lots':out}
    path=Path(__file__).resolve().parents[1]/'senses.json'
    path.write_text(json.dumps(doc,indent=2));print('wrote senses.json')

if __name__ == '__main__':main()
