#!/usr/bin/env python3
"""Aggregate measured v783 signed synapse weights into sensory/readout groups."""
import json
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from flybrain import Brain

if __name__ == '__main__':
    b=Brain()
    names=['other neurons','sugar','bitter','looming','mn9','giant_fibre','mdn']
    groups=np.zeros(b.N,dtype=np.int32)
    for i,name in enumerate(names[1:],1):groups[b.groups[name]]=i
    A=sp.csr_matrix((np.ones(b.N),(np.arange(b.N),groups)),shape=(b.N,len(names)))
    signed=(A.T @ b.W @ A).toarray()
    absolute=b.W.copy();absolute.data=np.abs(absolute.data)
    magnitude=(A.T @ absolute @ A).toarray()
    nodes=[{'id':i,'name':name,'neurons':int(np.count_nonzero(groups==i))} for i,name in enumerate(names)]
    edges=[]
    for i in range(len(names)):
        for j in range(len(names)):
            if i==j or not magnitude[i,j]:continue
            edges.append({'from':i,'to':j,'signed_synapses':float(signed[i,j]),
                          'excitatory_synapses':float((magnitude[i,j]+signed[i,j])/2),
                          'inhibitory_synapses':float((magnitude[i,j]-signed[i,j])/2)})
    doc={'provenance':{'source':'Shiu Connectivity_783.parquet, real FlyWire v783 signed synapse counts',
                       'n_neurons':b.N,'n_connections':b.n_connections,'script':'pipeline/export_fly_network.py'},
         'note':'Groups collapse internal wiring; diagram shows selected between-group connections, not individual neurons.',
         'nodes':nodes,'edges':edges}
    path=Path(__file__).resolve().parents[1]/'web/data/fly_network.json'
    path.write_text(json.dumps(doc));print('wrote',path,len(edges),'group edges')
