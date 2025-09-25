#!/usr/bin/env python
# coding: utf-8

# In[10]:


import numpy as np
import glob
from os import path
import json
from scipy import stats
import matplotlib.pyplot as plt 
import yaml

def load_config(config_path):
    with open(config_path, "r") as cfgfile:
        config = yaml.load(cfgfile, Loader=yaml.FullLoader)
    return config

# In[3]:


dirs=glob.glob('plots/fakes_*/')


# In[5]:

notsimmed = ('ASASSN1',  'ASASSN2', 'SWIFT',  'KAIT1MO', 'KAIT2MO',  'KAIT3MO', 'KAIT4MO', 'NICKEL1MO', 'NICKEL2MO', 'KAIT3', 'KAIT4',  'NICKEL1',  'NICKEL2', 'ZTFD', 'ZTFS', 'ATLAS')

simmap={ 'PS1':'griz', 
    'SNLS':'griz',
    'SDSS':'griz',
    'CFA3K':'BVri',
    'CFA3S': 'BVRI'  ,  
    'CSP':'BVgri',
    'PS1SN':'griz',    
    'DES': 'griz',
    'ZTFS':'gri',
    'ZTFD':'GRI',
    'CFA4P1':'BVri',
    'CFA4P2':'BVri',
    'ZTF':'griGRI',
    'Foundation':'griz',
    'D3YR':'griz',
}

#chainsfile='DOVEKIE.V7.npz'#
chainsfile=load_config('DOVEKIE_DEFS.yml')['chainsfile']

outdir=f'plots/fakes_calspeconly_fitboth_0'
result=np.genfromtxt(path.join(outdir,'preprocess_dovekie.dat'),dtype=None,names=True,encoding='utf-8')
result=result[result['SPECLIB']=='calspec23']
outfile=np.load(path.join(outdir,chainsfile))
    
simmap_indexes={}
label=outfile['labels'][0]
for label in outfile['labels']:
    surv,filt=label.split('-')[0],label.split('-')[1].split('_')[0]
    if 'ZTF' in surv: 
        if filt.isupper():
            surv='ZTFD'
        else:
            surv='ZTFS'
    index=simmap[surv].index('V' if surv=='CSP' and filt in 'omn' else filt  )

    simmap_indexes[label]=(surv,index)


# In[6]:
#outdirfstring='plots/fakes_calspeconly_fitstis_{i}'
outdirfstring='plots/fakes_stisonly_fitboth_{i}'
inputlib=('calspec23' if 'calspeconly' in outdirfstring else 'stis_ngsl_v2')
fitlib=('calspec23' if 'fitcalspec' in outdirfstring else 'stis_ngsl_v2')


results=[]
def splittuple(arr):
    return map( lambda x: np.array(list(map(float,x))),list(zip(*np.char.split(arr,'+-'))))

for i in range(100):
    for outdirfstring in ['plots/fakes_stisonly_fitboth_{i}','plots/fakes_calspeconly_fitboth_{i}']:
        inputlib=('calspec23' if 'calspeconly' in outdirfstring else 'stis_ngsl_v2')
        fitlib=(inputlib if 'fitboth' in outdirfstring else ('calspec23' if 'fitcalspec' in outdirfstring else 'stis_ngsl_v2'))
        outdir=outdirfstring.format(i=i)
        result=np.genfromtxt(path.join(outdir,'preprocess_dovekie.dat'),dtype=None,names=True,encoding='utf-8')
        result=result[result['SPECLIB']==fitlib]
        outfile=np.load(path.join(outdir,chainsfile))
    
        offsetsamples=outfile['samples']
        offsets,offseterrs=np.mean(offsetsamples,axis=0),np.std(offsetsamples,axis=0)
        with open(f'output_simulated_apermags+AV/{inputlib}_{i}/simmedoffsets.json') as file: 
            simmedoffsets=(json.loads(file.read()))
            for k in notsimmed:
                simmedoffsets.pop(k, None)

        trueoffsets=np.array([simmedoffsets[(idx:=simmap_indexes[label])[0]][idx[1]] for label in outfile['labels']])
        pval=np.sum(offsetsamples>trueoffsets[np.newaxis,:],axis=0)/offsetsamples.shape[0]
        chi2= np.sum((np.linalg.solve(np.linalg.cholesky(np.cov(offsetsamples.T) ), np.mean(offsetsamples,axis=0) -trueoffsets))**2)          
        slopes,errs=list((splittuple(result['D_SLOPE'])))
        synth_slopes,_=list((splittuple(result['S_SLOPE'])))
        results+=[(slopes,errs,synth_slopes,offsets,offseterrs,trueoffsets,pval,inputlib,chi2)]
slopes,errs,synth_slopes,offsets,offseterrs,trueoffsets,pval,inputlib,chi2=list(map(np.stack,zip(*results)))

# In[8]:

print(f"Mean chi2: {np.mean(chi2):.1f}")
slopelabels=np.char.add(np.char.add(result['OFFSETSURV'],'-'),result['OFFSETFILT2']) 
offsetlabels=np.char.replace(outfile['labels'],'_offset','')

sloperesids=slopes-synth_slopes
offsetresids=offsets-trueoffsets

matches_mask = slopelabels[:, np.newaxis] == offsetlabels[np.newaxis, :]
slope_idx, offset_idx = np.where(matches_mask)


# In[11]:


plt.hist([stats.kstest(pval[:,i],lambda x: x).pvalue for i in range(pval.shape[1])],bins=np.linspace(0,1,11,True))
plt.xlabel('KS test p-value')
plt.savefig('offsetpvals.pdf')
plt.clf()


# In[12]:




a=(np.abs(np.mean(synth_slopes,axis=0)-np.mean(slopes,axis=0))<.25)
plt.errorbar(np.mean(synth_slopes,axis=0)[a],(np.mean(slopes,axis=0) - np.mean(synth_slopes,axis=0))[a],yerr=np.std(slopes,axis=0)[a],fmt='.')
plt.axhline(0,linestyle='--',color='black')
plt.xlabel('Synthetic slope')
plt.ylabel('Data slope bias (recovered-input)')

plt.savefig('plots/slopebias.pdf')
plt.clf()


# In[13]:


plus,minus=result['COLORFILT1']== result['OFFSETFILT1'],result['COLORFILT2']== result['OFFSETFILT1']
zero=~(plus | minus)

bias=np.mean(slopes,axis=0)-np.mean(synth_slopes,axis=0)
bins=np.linspace(-.05,.05,10,True)
plt.hist([np.clip(bias[x],bins[1]-1e-3,bins[-2]+1e-3) for x in [plus,zero,minus]],label=['Resid matches first index','Resid matches none','Resid matches second index'],bins=bins)
plt.legend()
plt.xlabel('Bias in slope')
plt.xticks( list((bins[1:]+bins[:-1])/2) ,[('Outliers')]+ [f'{x:.3f}' for x in list((bins[1:]+bins[:-1])/2)[1:-1]]+ [('Outliers')],rotation=90)
plt.savefig('plots/slopebiashist.pdf')
plt.clf()


# In[14]:


plt.errorbar(np.arange(offsets.shape[1]),np.mean((offsets-trueoffsets)/offseterrs,axis=0) ,fmt='k.')
plt.xticks(np.arange(offsets.shape[1]),[x.split('_')[0] for x in (outfile['labels'])],rotation=90);
plt.ylabel('')
zvals=np.abs(np.mean(offsets-trueoffsets,axis=0)/(np.std(offsets,axis=0)/np.sqrt(offsets.shape[0])))
plt.ylabel('Mean $z$-score (true-measured/err)')
plt.savefig('meanzscore.pdf')
plt.clf()


# In[15]:


plt.hist( np.clip(((trueoffsets-offsets)/offseterrs).flatten(),-4.9,4.9),bins=np.linspace(-5,5,21),density=True)
plt.plot(plotxs:=np.linspace(-4,4,101), stats.norm.pdf(plotxs))
plt.xlabel('$z$-score')
plt.savefig('offsetzscoreshist.pdf')

plt.clf()

# In[16]:


plt.hist([np.corrcoef((slopes-synth_slopes).T)[~np.eye(slopes.shape[1],dtype=bool)],np.corrcoef((offsets-trueoffsets).T)[~np.eye(offsets.shape[1],dtype=bool)]],
        label=['Slopes','Offsets'])

plt.xlabel('Correlation coefficient (off-diagonal)')

plt.savefig('plots/corrcoefs.pdf')
plt.savefig('plots/corrcoefs.png',dpi=288)
plt.clf()

# In[ ]:


plt.plot(np.sqrt(np.mean(offseterrs**2,axis=0)), np.std((offsets-trueoffsets),axis=0),'k.')
plt.ylim(0,0.02)
plt.xlim(0,0.02)
plt.plot([0,.02],[0,.02],'k--')
plt.xlabel('Estimated offset errors')
plt.ylabel('Observed offset scatter')
plt.savefig('plots/simscatter.pdf')
plt.clf()


# In[25]:


with open('simbiases.txt','w') as file:
    defcolumnwidth=9
    header=['FILTER']+['SPECLIB']+ ['OFFSETBIAS' , 'OFFSETZSCORE','OFFSETERRMEAN','OFFSETSCATTER', 'OFFSETPVAL','SLOPEBIAS','SLOPEERROR','SLOPEZSCORE','SLOPEPVAL','SLOPEOFFSETCORR']
    def formatline(arr):
        return' '.join([('{: >'+(str(max(defcolumnwidth,len(header)+3)))+'.4f}').format(x) if type(x) is np.float64 else ('{: >'+(str(max(defcolumnwidth,len(header)+3)))+'}').format(x) for x,head in zip(arr,header)])
    file.write(formatline(header)+'\n')    
    for filt in np.unique(np.concatenate((offsetlabels,slopelabels))):
        for rowinputlib in list(np.unique(inputlib)) + ['both']:
            if rowinputlib=='both':
                libidx=slice(None,None,None)
            else:
                libidx=inputlib ==rowinputlib
            idx=np.where(filt==offsetlabels)[0]
            if len(idx):
                meanbias=np.mean((offsets[libidx,idx]-trueoffsets[libidx,idx]))
                meanzscore= np.mean((offsets[libidx,idx]-trueoffsets[libidx,idx])/offseterrs[libidx,idx])
                offerrest,offerrobs=np.sqrt(np.mean(offseterrs[libidx,idx]**2)), np.std((offsets[libidx,idx]-trueoffsets[libidx,idx]))
                kspval=stats.kstest(pval[libidx,idx[0]],lambda x: x).pvalue
            else: meanbias , meanzscore,offerrest,offerrobs, kspval = ['NA']*5 #Formerly 3?
            idx=np.where(filt==slopelabels)[0]
            if len(idx):
                idx=idx[0]
                slopebias=np.mean(sloperesids[libidx,idx])
                slopeerr=np.std(sloperesids[libidx,idx])
                slopebiaszscore= slopebias/(slopeerr)
                slopebiaspval= (1-stats.norm.cdf(np.abs(slopebiaszscore)))*2
                slopeoffsetcorr=np.mean( (sloperesids[libidx,idx]-slopebias) * (offsetresids[libidx,offset_idx[idx]]  )) / slopeerr/ np.std(offsetresids[ libidx,offset_idx[idx]])
            else:
                slopebias,slopeerr,slopebiaszscore,slopebiaspval,slopeoffsetcorr= ['NA']*5
            allres=[meanbias , meanzscore,offerrest,offerrobs, kspval,slopebias,slopeerr,slopebiaszscore,slopebiaspval,slopeoffsetcorr]
            file.write(formatline([filt]+[rowinputlib]+allres)+'\n')


# In[20]:





# In[36]:





# In[ ]:





# In[ ]:




