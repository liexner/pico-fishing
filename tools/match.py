import numpy as np, soundfile as sf
SR=16000
def load_tpl(p, start=0.0, dur=1.0):
    y,sr=sf.read(p); y=np.interp(np.arange(0,len(y)/sr,1/SR), np.arange(len(y))/sr, y)  # resample to 16k
    return y[int(start*SR):int((start+dur)*SR)]
def ncc(x,h):
    L=len(h); h=(h-h.mean())/np.linalg.norm(h-h.mean())
    n=1<<int(np.ceil(np.log2(len(x)+L)))
    c=np.fft.irfft(np.fft.rfft(x,n)*np.conj(np.fft.rfft(h,n)),n)[:len(x)-L+1]
    cs=np.concatenate(([0],np.cumsum(x))); cs2=np.concatenate(([0],np.cumsum(x*x)))
    s=cs[L:]-cs[:-L]; s2=cs2[L:]-cs2[:-L]
    sd=np.sqrt(np.maximum(s2-s*s/L,1e-9))
    return c/sd
def load_rec(d,pcm,times,keys):
    x=np.fromfile(f"{d}{pcm}",dtype='<i2').astype(float)
    T=np.loadtxt(f"{d}{times}")
    K=[float(l.split()[0]) for l in open(f"{d}{keys}") if 'SPACE' in l]
    return x,T,K

NF,HOP=512,256   # 32 ms frames, 16 ms hop
EDGES=np.geomspace(150,7900,17)  # 16 log-spaced bands
def bands(x):
    fr=np.lib.stride_tricks.sliding_window_view(x,NF)[::HOP]
    f=np.fft.rfftfreq(NF,1/SR)
    P=np.abs(np.fft.rfft((fr-fr.mean(1,keepdims=True))*np.hanning(NF),axis=1))**2
    B=np.stack([P[:,(f>=a)&(f<b)].sum(1) for a,b in zip(EDGES,EDGES[1:])],1)
    return np.log(B+1e-3)
def spec_match(R,Tm):
    # R: rec bands (n,16), Tm: template bands (m,16); normalized correlation of the 2D patch
    m=len(Tm); t=(Tm-Tm.mean()); t/=np.linalg.norm(t)
    W=np.lib.stride_tricks.sliding_window_view(R,(m,R.shape[1]))[:,0]  # (n-m+1,m,16)
    W=W-W.mean(axis=(1,2),keepdims=True)
    return (W*t).sum(axis=(1,2))/np.maximum(np.linalg.norm(W,axis=(1,2)),1e-9)
