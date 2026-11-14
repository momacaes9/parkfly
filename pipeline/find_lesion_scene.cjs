const fs=require('fs'),path=require('path'),root=path.resolve(__dirname,'..'),PF=require(path.join(root,'web/model.js'));
const J=f=>JSON.parse(fs.readFileSync(path.join(root,'web/data',f+'.json')));
const {lots}=J('lots'),truth=J('truth'),surf=J('fly_surface'),fit=truth.fitted;
const intact=new PF.Surface(surf,'intact'),lesion=new PF.Surface(surf,'lesion_gf');
const days=truth.days.map(d=>({...d,occ:d.occ.map((s,i)=>PF.unpack(s,truth.n_steps,lots[i].spaces))}));
let found=[];
for(let di=0;di<days.length;di++){
 const day=days[di];if(day.day!=='weekday')continue;
 for(let ti=24;ti<96;ti++){
 const P=fit.prior[day.day], S=lots.map((l,i)=>PF.occMatrix(l.spaces,fit.tau[i][truth.start_min+ti*truth.step_min<fit.tau_pm_from_min?0:1]));
 for(const pct of [0,10,25,40,75,100]){
 const masks=lots.map((l,i)=>PF.place('scatter',Math.round(pct/100*l.spaces),[],[],l.spaces,PF.rng32(7919+i*104729+17)));
 const occ=lots.map((l,i)=>day.occ[i][ti]),post=PF.infer(S,occ,masks,P.mu.map(a=>a[ti]),P.sd.map(a=>a[ti]),{D:fit.across.D,rho0:fit.across.rho0,ell:fit.across.ell_m});
 for(let i=0;i<lots.length;i++){
 if(lots[i].pay)continue;
 const t=PF.tastes(lots[i].spaces,post[i].post,S[i],masks[i],occ[i],lots[i].walk_min,lots[i].price_hr,0,P.mu[i][Math.min(ti+3,truth.n_steps-1)]-P.mu[i][ti]);
 const hz=PF.toHz(t),a=intact.read(...hz),b=lesion.read(...hz);
 const free=Array.from(occ[i]).filter(x=>!x).length, future=Array.from(day.occ[i][Math.min(ti+3,truth.n_steps-1)]).filter(x=>!x).length;
 if(PF.verdict(a)==='DIVERT'&&PF.verdict(b)==='COMMIT')found.push({day:di,ti,pct,lot:i,free,future,hz,intact:a,lesion:b});
 }
 }
 }
}
found.sort((a,b)=>a.future-b.future||a.free-b.free||Math.abs(a.pct-25)-Math.abs(b.pct-25));
if(!found.length)throw new Error('No DIVERT-to-COMMIT scene was measured');
const doc={label:'Selected from held-out SIMULATED weekdays. Near-full lot, not a collision forecast.',shuffle:1,search_cases:found.length,script:'pipeline/find_lesion_scene.cjs',...found[0]};
fs.writeFileSync(path.join(root,'web/data/lesion_scene.json'),JSON.stringify(doc,null,2));
console.log('scenes',found.length,doc);
