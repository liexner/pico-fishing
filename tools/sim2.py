# Replays recordings through the Pico bite logic for a given filter (order of differencing) and JUMP.
import numpy as np, sys
def run(pcm,times,keys,order,JUMP,MIN_AMB=2000.0,verbose=False):
    x=np.fromfile(pcm,dtype='<i2').astype(float)
    T=np.loadtxt(times); t0=T[0,0]
    K=[float(l.split()[0]) for l in open(keys) if 'SPACE' in l]
    firsts=[k for i,k in enumerate(K) if i+1<len(K) and K[i+1]-k<1.5 and (i==0 or k-K[i-1]>3)]
    d=np.diff(x,n=order,prepend=[0]*order)
    nb=len(d)//160; E=(d[:nb*160].reshape(nb,160)**2).sum(1)
    bt=np.interp(2*np.arange(nb)*160, T[:,1], T[:,0])
    amb=MIN_AMB; hits=[]; last=-9
    for e,t in zip(E,bt):
        if e>max(amb,MIN_AMB)*JUMP and t-last>3: hits.append(t); last=t
        amb+=(min(e,3*amb)-amb)*0.01
    caught=[k for k in firsts if any(-1.5<=h-k<=0 for h in hits)]
    # false = not followed by a press within 1.5s, not within 5s after a press (cast ignore), and <6s after last press (too early for a bite)
    false=[h for h in hits if not any(0<=k-h<=1.5 for k in K) and not any(0<=h-k<=5 for k in K)]
    if verbose: print(" hits", ' '.join(f"{h-t0:.1f}" for h in hits))
    return len(caught),len(firsts),len(false)
for order in (1,2,3):
    for J in (10,15,25,40):
        q=run('quiet/raw.pcm','quiet/raw_times.txt','quiet/keys.log',order,J)
        n=run('nraw.pcm','nraw_times.txt','nkeys.log',order,J)
        print(f"diff^{order} JUMP {J:3d}: quiet caught {q[0]}/{q[1]} other-hits {q[2]} | noisy caught {n[0]}/{n[1]} other-hits {n[2]}")
