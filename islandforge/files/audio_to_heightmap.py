"""
audio_to_heightmap.py  —  Island Forge v2.0
============================================
v2.0 improvements:
  - Audio-driven geographic archetypes (each band = distinct landform type)
  - Landmark peak injection — 1-4 peaks driven by BPM
  - River erosion simulation — valleys + navigation channels
  - Multi-pass organic coastline — bays, peninsulas, headlands
  - Road network — flat channels connecting town to zone centers
  - Hillshaded preview with contour lines
"""

import argparse, json, math, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# ─────────────────────────────────────────────────────────────
# PERLIN NOISE
# ─────────────────────────────────────────────────────────────

def make_permutation(seed):
    rng = np.random.default_rng(seed)
    p = np.arange(256, dtype=np.int32)
    rng.shuffle(p)
    return np.tile(p, 2)

def fade(t): return t*t*t*(t*(t*6-15)+10)
def lerp(a,b,t): return a+t*(b-a)

def grad(h,x,y):
    h=h&3
    u=np.where(h<2,x,y); v=np.where(h<2,y,x)
    return np.where(h&1,-u,u)+np.where(h&2,-v,v)

def perlin2d(x,y,perm):
    xi=x.astype(int)&255; yi=y.astype(int)&255
    xf=x-np.floor(x); yf=y-np.floor(y)
    u=fade(xf); v=fade(yf)
    aa=perm[perm[xi]+yi]; ab=perm[perm[xi]+yi+1]
    ba=perm[perm[xi+1]+yi]; bb=perm[perm[xi+1]+yi+1]
    x1=lerp(grad(aa,xf,yf),grad(ba,xf-1,yf),u)
    x2=lerp(grad(ab,xf,yf-1),grad(bb,xf-1,yf-1),u)
    return lerp(x1,x2,v)

def octave_noise(size,octaves,persistence,lacunarity,scale,seed):
    perm=make_permutation(seed)
    result=np.zeros((size,size),dtype=np.float64)
    amp=1.0; freq=1.0; maxv=0.0
    lin=np.linspace(0,scale,size,endpoint=False)
    xs,ys=np.meshgrid(lin,lin)
    for _ in range(octaves):
        result+=amp*perlin2d(xs*freq,ys*freq,perm)
        maxv+=amp; amp*=persistence; freq*=lacunarity
    return result/maxv

def noise_norm(size,oct,per,lac,scale,seed):
    n=octave_noise(size,oct,per,lac,scale,seed)
    lo,hi=n.min(),n.max()
    return (n-lo)/(hi-lo+1e-9)

# ─────────────────────────────────────────────────────────────
# AUDIO ANALYSIS
# ─────────────────────────────────────────────────────────────

def analyse_audio(path):
    default={"sub_bass":0.5,"bass":0.5,"midrange":0.5,"presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":60.0}
    SUPPORTED=(".wav",".mp3",".flac",".ogg",".aac",".m4a",".aiff",".opus")
    try:
        import subprocess,tempfile
        from scipy.io import wavfile
        ext=os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED: return default
        work_path=path; tmp_wav=None
        if ext!=".wav":
            ffmpeg=subprocess.run(["which","ffmpeg"],capture_output=True).stdout.strip()
            if not ffmpeg: return default
            tmp_wav=tempfile.NamedTemporaryFile(suffix=".wav",delete=False); tmp_wav.close()
            r=subprocess.run(["ffmpeg","-y","-i",path,"-ac","1","-ar","44100","-sample_fmt","s16",tmp_wav.name],capture_output=True)
            if r.returncode!=0: return default
            work_path=tmp_wav.name
        framerate,raw=wavfile.read(work_path)
        if tmp_wav: os.unlink(tmp_wav.name)
        if raw.dtype==np.int16: samples=raw.astype(np.float64)/32768.0
        elif raw.dtype==np.int32: samples=raw.astype(np.float64)/2147483648.0
        else: samples=raw.astype(np.float64)
        if samples.ndim>1: samples=samples.mean(axis=1)
        duration_s=len(samples)/framerate
        chunk=samples[:int(min(duration_s,60)*framerate)]
        fft_mag=np.abs(np.fft.rfft(chunk))
        freqs=np.fft.rfftfreq(len(chunk),d=1.0/framerate)
        def be(lo,hi):
            mask=(freqs>=lo)&(freqs<hi)
            return float(np.mean(fft_mag[mask])) if mask.any() else 0.0
        bands={"sub_bass":be(20,60),"bass":be(60,250),"midrange":be(250,2000),"presence":be(2000,8000),"brilliance":be(8000,20000)}
        maxe=max(bands.values()) or 1.0
        for k in bands: bands[k]/=maxe
        hop=512
        env=np.array([np.sqrt(np.mean(chunk[i:i+hop]**2)) for i in range(0,len(chunk)-hop,hop)])
        corr=np.correlate(env,env,mode="full")[len(env)-1:]
        blo=max(1,int(framerate/hop*60/180)); bhi=min(len(corr)-1,int(framerate/hop*60/60))
        peak=np.argmax(corr[blo:bhi])+blo
        bpm=(framerate/hop)*60.0/peak if peak>0 else 120.0
        bands["tempo_bpm"]=round(bpm,1); bands["duration_s"]=round(duration_s,1)
        print(f"[audio] {duration_s:.1f}s BPM≈{bpm:.0f} sub={bands['sub_bass']:.2f} bass={bands['bass']:.2f} mid={bands['midrange']:.2f}")
        return bands
    except Exception as e:
        print(f"[audio] failed ({e}) — defaults"); return default

# ─────────────────────────────────────────────────────────────
# ISLAND MASK — organic multi-pass coastline
# ─────────────────────────────────────────────────────────────

def build_island_mask(size,seed,presence):
    cx=cy=size/2.0
    ys,xs=np.mgrid[:size,:size]
    rng=np.random.default_rng(seed+900)
    sx=rng.uniform(0.85,1.15); sy=rng.uniform(0.85,1.15)
    tilt=rng.uniform(0,math.pi)
    ct,st=math.cos(tilt),math.sin(tilt)
    dx=xs-cx; dy=ys-cy
    rx=dx*ct+dy*st; ry=-dx*st+dy*ct
    ellip=np.sqrt((rx/sx)**2+(ry/sy)**2)
    # Large warp — peninsulas and bays
    w1x=octave_noise(size,5,0.55,2.0,2.8,seed+200); w1y=octave_noise(size,5,0.55,2.0,2.8,seed+201)
    ws1=size*(0.10+presence*0.12)
    xw=xs+w1x*ws1; yw=ys+w1y*ws1
    # Fine coastal detail
    w2x=octave_noise(size,4,0.65,2.3,6.0,seed+202); w2y=octave_noise(size,4,0.65,2.3,6.0,seed+203)
    ws2=size*(0.03+presence*0.05)
    xw=xw+w2x*ws2; yw=yw+w2y*ws2
    wd=np.sqrt((xw-cx)**2+(yw-cy)**2)
    combined=ellip*0.3+wd*0.7
    rn=combined/(size*0.50)
    mask=np.clip(1.0-rn/0.76,0.0,1.0)**1.8
    return mask.astype(np.float64)

# ─────────────────────────────────────────────────────────────
# AUDIO-DRIVEN BASE TERRAIN
# ─────────────────────────────────────────────────────────────

def build_base_terrain(size,seed,w):
    sub=w["sub_bass"]; bass=w["bass"]; mid=w["midrange"]
    pres=w["presence"]; bril=w["brilliance"]

    # Layer 1: Mountain spine — sub_bass pulls elevation to centre
    spine=octave_noise(size,8,0.52,2.0,2.5+sub*1.5,seed)
    cx=cy=size/2.0; ys,xs=np.mgrid[:size,:size]
    pull=np.exp(-((xs-cx)**2+(ys-cy)**2)/(2*(size*0.25)**2))
    spine=spine*(0.6+sub*0.4*pull)

    # Layer 2: Hill chains — bass drives radiating ridges
    hills=octave_noise(size,6,0.58,2.1,4.5+bass*3.0,seed+1)
    hw=octave_noise(size,3,0.5,2.0,3.0,seed+10)
    scale_h=4.5+bass*3.0
    lin=np.linspace(0,scale_h,size,endpoint=False)
    xg,yg=np.meshgrid(lin,lin)
    perm_h=make_permutation(seed+1)
    hw_str=size*0.04*bass
    hills_w=perlin2d(xg+hw*hw_str/size*scale_h, yg+hw*hw_str/size*scale_h, perm_h)
    hills=hills*0.5+hills_w*0.5

    # Layer 3: Interior detail — midrange
    detail=octave_noise(size,5,0.48,2.0,9.0+mid*5.0,seed+2)

    # Layer 4: Coastal erosion — presence
    erosion=octave_noise(size,4,0.62,2.3,14.0+pres*6.0,seed+3)

    # Layer 5: Micro-detail — brilliance
    micro=octave_noise(size,3,0.45,2.0,22.0+bril*10.0,seed+4)

    terrain=(
        spine  *(0.45+sub *0.20)+
        hills  *(0.25+bass*0.15)+
        detail *(0.15+mid *0.10)+
        erosion*(0.10+pres*0.08)+
        micro  *(0.05+bril*0.05)
    )
    return terrain

# ─────────────────────────────────────────────────────────────
# LANDMARK PEAK INJECTION
# ─────────────────────────────────────────────────────────────

def inject_peaks(terrain,size,seed,w):
    bpm=w.get("tempo_bpm",120.0); sub=w["sub_bass"]
    n_peaks=max(1,min(4,int((bpm-60)/40)+1))
    p_height=0.35+sub*0.30; p_radius=size*(0.06+sub*0.04)
    rng=np.random.default_rng(seed+700)
    cx=cy=size//2; placed=[]
    ys,xs=np.mgrid[:size,:size]
    attempts=0
    while len(placed)<n_peaks and attempts<200:
        attempts+=1
        angle=rng.uniform(0,2*math.pi); dist=rng.uniform(size*0.12,size*0.32)
        px=int(cx+math.cos(angle)*dist); py=int(cy+math.sin(angle)*dist)
        margin=int(size*0.08)
        if not(margin<px<size-margin and margin<py<size-margin): continue
        if any(math.sqrt((px-ox)**2+(py-oy)**2)<size*0.18 for ox,oy in placed): continue
        placed.append((px,py))
        bump=np.exp(-((xs-px)**2+(ys-py)**2)/(2*p_radius**2))
        pn=noise_norm(size,3,0.5,2.0,8.0,seed+710+len(placed))
        terrain=terrain+bump*(0.7+pn*0.3)*p_height
    print(f"[peaks] {len(placed)} landmark peaks (BPM={bpm:.0f})")
    return terrain

# ─────────────────────────────────────────────────────────────
# RIVER EROSION
# ─────────────────────────────────────────────────────────────

def simulate_rivers(terrain,size,seed,n_rivers=4):
    rng=np.random.default_rng(seed+800)
    result=terrain.copy(); wl=0.22
    for r in range(n_rivers):
        flat=terrain.ravel()
        cands=np.where(flat>np.percentile(flat,85))[0]
        if not len(cands): continue
        idx=rng.choice(cands); row,col=divmod(int(idx),size)
        path=[(row,col)]; visited=set()
        for _ in range(size*3):
            visited.add((row,col))
            best_h=terrain[row,col]; best_n=None
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    if dr==0 and dc==0: continue
                    nr,nc=row+dr,col+dc
                    if not(0<=nr<size and 0<=nc<size): continue
                    if(nr,nc) in visited: continue
                    nh=terrain[nr,nc]
                    if nh<best_h: best_h=nh; best_n=(nr,nc)
            if best_n is None or best_h<wl: break
            row,col=best_n; path.append((row,col))
        if len(path)<10: continue
        cw=max(2,int(size*0.008)); cd=0.04+rng.uniform(0,0.03)
        for pr,pc in path:
            r0=max(0,pr-cw); r1=min(size,pr+cw)
            c0=max(0,pc-cw); c1=min(size,pc+cw)
            result[r0:r1,c0:c1]=np.minimum(result[r0:r1,c0:c1],result[r0:r1,c0:c1]-cd*0.5)
        print(f"[river] River {r+1}: {len(path)} steps")
    return gaussian_filter(result,sigma=1.5)

# ─────────────────────────────────────────────────────────────
# ROAD NETWORK
# ─────────────────────────────────────────────────────────────

def build_roads(terrain,size,seed,zone_centers):
    result=terrain.copy()
    road_mask=np.zeros((size,size),dtype=bool)
    cy=cx=size//2; rw=max(2,size//120)
    for(zr,zc) in zone_centers:
        dr=zr-cy; dc=zc-cx; steps=max(abs(dr),abs(dc))
        if steps==0: continue
        for i in range(steps+1):
            t=i/steps; r=int(cy+dr*t); c=int(cx+dc*t)
            r0=max(0,r-rw); r1=min(size,r+rw)
            c0=max(0,c-rw); c1=min(size,c+rw)
            lh=float(np.mean(result[r0:r1,c0:c1]))
            result[r0:r1,c0:c1]=result[r0:r1,c0:c1]*0.7+lh*0.3
            road_mask[r0:r1,c0:c1]=True
    return result,road_mask

# ─────────────────────────────────────────────────────────────
# FULL TERRAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def generate_terrain(size,seed,weights,water_level=0.20):
    w=weights; pres=w["presence"]
    print("[gen] Island mask..."); mask=build_island_mask(size,seed,pres)
    print("[gen] Base terrain..."); terrain=build_base_terrain(size,seed,w)
    print("[gen] Landmark peaks..."); terrain=inject_peaks(terrain,size,seed,w)

    ocean_hard=(mask<0.08)
    terrain=terrain*mask
    terrain=gaussian_filter(terrain,sigma=1.8)
    lo,hi=terrain.min(),terrain.max(); terrain=(terrain-lo)/(hi-lo+1e-9)

    land_px=mask>=0.08
    if land_px.any():
        lv=terrain[land_px]; ranks=np.argsort(np.argsort(lv))
        norm=ranks/(len(lv)-1.0); terrain[land_px]=0.22+norm*0.78
    terrain[ocean_hard]=0.04

    # Town plateau
    rng=np.random.default_rng(seed+500)
    cx_f=cy_f=size/2.0
    off_x=int(rng.integers(-size//14,size//14)); off_y=int(rng.integers(-size//14,size//14))
    tcx=int(cx_f)+off_x; tcy=int(cy_f)+off_y; tr=int(size*0.032)
    tn=noise_norm(size,3,0.5,2.0,9.0,seed+300)
    ys2,xs2=np.mgrid[:size,:size]
    td=np.sqrt((xs2-tcx)**2+(ys2-tcy)**2)
    tdw=td-(tn-0.5)*tr*0.40; tb=np.clip(tdw/tr,0.0,1.0)
    inf=tr*2; r0=max(0,tcy-inf); r1=min(size,tcy+inf); c0=max(0,tcx-inf); c1=min(size,tcx+inf)
    terrain[r0:r1,c0:c1]=terrain[r0:r1,c0:c1]*tb[r0:r1,c0:c1]+0.35*(1.0-tb[r0:r1,c0:c1])

    # Rivers
    n_rivers=2+int(w["midrange"]*3)
    print(f"[gen] {n_rivers} rivers..."); terrain=simulate_rivers(terrain,size,seed,n_rivers)

    # Roads
    zd=size*0.28
    zcs=[(int(size//2-zd),size//2),(int(size//2+zd),size//2),(size//2,int(size//2+zd)),(size//2,int(size//2-zd))]
    zcs=[(max(4,min(size-4,r)),max(4,min(size-4,c))) for r,c in zcs]
    print("[gen] Roads..."); terrain,road_mask=build_roads(terrain,size,seed,zcs)

    if water_level>0.0:
        terrain[terrain<water_level]=water_level*0.5
    terrain[ocean_hard]=0.04
    terrain=gaussian_filter(terrain,sigma=0.8)
    return np.clip(terrain,0.0,1.0),road_mask

# ─────────────────────────────────────────────────────────────
# MOISTURE + BIOMES
# ─────────────────────────────────────────────────────────────

def generate_moisture(size,seed):
    m=octave_noise(size,6,0.5,2.0,3.0,seed+99)
    lo,hi=m.min(),m.max(); return (m-lo)/(hi-lo+1e-9)

BIOME_OCEAN=0; BIOME_PLAINS=1; BIOME_FOREST=2; BIOME_HIGHLAND=3
BIOME_MOUNTAIN=4; BIOME_PEAK=5; BIOME_FARM=6

BIOME_NAMES={0:"Ocean",1:"Plains",2:"Forest",3:"Highland",4:"Mountain",5:"Peak",6:"Farm Town"}
BIOME_COLOURS={0:(20,60,140),1:(155,205,90),2:(50,130,55),3:(130,160,95),4:(115,90,70),5:(235,240,245),6:(205,155,55)}
BIOME_ZONE_TIER={0:0,1:1,2:1,3:2,4:3,5:4,6:0}

def classify_biomes(height,moisture,water_level=0.20):
    biome=np.zeros(height.shape,dtype=np.int32); wl=water_level
    biome[height<wl]=BIOME_OCEAN; biome[height<=0.05]=BIOME_OCEAN
    lo_hi=wl+0.18; mid_hi=wl+0.34; hig_hi=wl+0.50; mtn_hi=wl+0.64
    low=(height>=wl)&(height<lo_hi)
    biome[low]=np.where(moisture[low]>0.52,BIOME_FOREST,BIOME_PLAINS)
    mid=(height>=lo_hi)&(height<mid_hi)
    biome[mid]=np.where(moisture[mid]>0.40,BIOME_FOREST,BIOME_HIGHLAND)
    biome[(height>=mid_hi)&(height<hig_hi)]=BIOME_HIGHLAND
    biome[(height>=hig_hi)&(height<mtn_hi)]=BIOME_MOUNTAIN
    biome[height>=mtn_hi]=BIOME_PEAK
    return biome

# ─────────────────────────────────────────────────────────────
# FARM CLUSTER
# ─────────────────────────────────────────────────────────────

def find_plot_positions(height,biome,n_plots,size,min_spacing=28,cluster_angle_deg=135.0,cluster_spread=1.0,seed=42):
    cx=cy=size//2
    ar=math.radians(cluster_angle_deg)
    dc=math.sin(ar); dr=-math.cos(ar)
    cd=size*0.20
    ccx=int(cx+dc*cd); ccy=int(cy+dr*cd)
    ccx=max(min_spacing,min(size-min_spacing,ccx)); ccy=max(min_spacing,min(size-min_spacing,ccy))
    cols=max(1,int(math.ceil(math.sqrt(n_plots)))); rows=max(1,int(math.ceil(n_plots/cols)))
    step=int(min_spacing*cluster_spread)
    rng=np.random.default_rng(seed+601)
    gr=math.radians(int(rng.integers(-25,25))); cr,sr=math.cos(gr),math.sin(gr)
    jrng=np.random.default_rng(seed+602)
    positions=[]
    for gi in range(n_plots):
        grow=gi//cols; gcol=gi%cols
        bx=(gcol-cols/2.0)*step; by=(grow-rows/2.0)*step
        rx=bx*cr-by*sr; ry=bx*sr+by*cr
        dfc=math.sqrt(bx**2+by**2)
        js=step*(0.12+0.22*(dfc/(step*cols/2.0+1e-6)))
        jx=jrng.uniform(-js,js); jy=jrng.uniform(-js,js)
        fc=int(ccx+rx+jx); fr=int(ccy+ry+jy)
        positions.append((max(2,min(size-2,fr)),max(2,min(size-2,fc))))
    return positions

def get_farm_cluster_info(positions,size):
    if not positions: return {"cx":size//2,"cy":size//2,"radius_px":0}
    rows=[p[0] for p in positions]; cols=[p[1] for p in positions]
    cy=int(np.mean(rows)); cx=int(np.mean(cols))
    dists=[math.sqrt((r-cy)**2+(c-cx)**2) for r,c in positions]
    return{"cx":cx,"cy":cy,"radius_px":int(max(dists)+20) if dists else 20}

def paint_farm_biome(biome,positions,size,padding=20,seed=42):
    info=get_farm_cluster_info(positions,size); cx,cy=info["cx"],info["cy"]
    br=info["radius_px"]+padding
    fw=octave_noise(size,4,0.55,2.0,7.0,seed+400)
    ys,xs=np.ogrid[:size,:size]
    fd=np.sqrt((xs-cx)**2+(ys-cy)**2); wfd=fd-fw*br*0.42
    biome=biome.copy(); biome[wfd<=br]=BIOME_FARM; return biome

def pixel_to_world(row,col,size,world_size_cm=201700):
    half=world_size_cm/2.0; cell=world_size_cm/size
    return(round(col*cell-half),round(row*cell-half),0)

# ─────────────────────────────────────────────────────────────
# LAYOUT JSON
# ─────────────────────────────────────────────────────────────

def build_layout(height,biome,plot_positions,size,seed,weights,water_level=0.20,world_wrap=True):
    cx=cy=size//2; tw=pixel_to_world(cy,cx,size)
    fi=get_farm_cluster_info(plot_positions,size)
    fw=pixel_to_world(fi["cy"],fi["cx"],size)
    fr=int(fi["radius_px"]/size*201700)
    zone_radii_pct=[0.0,0.18,0.30,0.42,0.54]
    zone_tiers=[{"zone_index":i,"tier":i+1,"center_x":tw[0],"center_y":tw[1],
                 "radius_cm":int(zone_radii_pct[i+1]*201700/2),"biome_hint":BIOME_NAMES.get(i+1,"Plains")}
                for i in range(len(zone_radii_pct)-1)]
    plots=[{"plot_index":i,"pixel_row":int(r),"pixel_col":int(c),
            "world_x_cm":pixel_to_world(r,c,size)[0],"world_y_cm":pixel_to_world(r,c,size)[1],
            "world_z_cm":int(float(height[r,c])*50000),
            "biome":BIOME_NAMES.get(int(biome[r,c]),"Plains"),
            "zone_tier":BIOME_ZONE_TIER.get(int(biome[r,c]),1)}
           for i,(r,c) in enumerate(plot_positions)]
    total=float(size*size)
    bpct={BIOME_NAMES[b]:round(float(np.sum(biome==b))/total*100,1) for b in BIOME_NAMES}
    return{"meta":{"seed":seed,"size_px":size,"world_size_cm":201700,"audio_weights":weights,
                   "n_plots":len(plots),"water_level":water_level,"world_wrap":world_wrap,"generator_version":"2.0"},
           "town_center":{"world_x_cm":tw[0],"world_y_cm":tw[1],"world_z_cm":int(float(height[cy,cx])*50000)},
           "zone_tiers":zone_tiers,
           "farm_cluster":{"world_x_cm":fw[0],"world_y_cm":fw[1],"radius_cm":fr,"n_plots":len(plots)},
           "plots":plots,"biome_distribution_pct":bpct,
           "verse_constants":{"comment":"Paste into plot_registry.verse","PLOT_COUNT":len(plots),
                               "WORLD_SIZE_CM":201700,"TOWN_X":tw[0],"TOWN_Y":tw[1],
                               "WORLD_WRAP":world_wrap,"WATER_LEVEL_NORMALIZED":round(water_level,3),
                               "FARM_CENTER_X":fw[0],"FARM_CENTER_Y":fw[1],"FARM_RADIUS_CM":fr,
                               "PLOT_POSITIONS":[[p["world_x_cm"],p["world_y_cm"],p["world_z_cm"]] for p in plots],
                               "ZONE_TIER_RADII_CM":[z["radius_cm"] for z in zone_tiers]}}

# ─────────────────────────────────────────────────────────────
# PREVIEW — hillshading + contours + roads
# ─────────────────────────────────────────────────────────────

def build_preview(height,biome,plot_positions,size,road_mask=None):
    rgb=np.zeros((size,size,3),dtype=np.float32)
    for bid,col in BIOME_COLOURS.items():
        rgb[biome==bid]=np.array(col,dtype=np.float32)
    # Ocean depth
    om=biome==BIOME_OCEAN
    if om.any():
        depth=np.clip(1.0-height/0.22,0.0,1.0)
        deep=np.array([8,30,100],dtype=np.float32); shore=np.array([40,100,190],dtype=np.float32)
        d=depth[om][:,np.newaxis]; rgb[om]=shore*(1-d)+deep*d
    # Hillshade — NW light
    dz_dy,dz_dx=np.gradient(height*80.0)
    lx,ly,lz=-0.6,-0.6,0.8; ln=math.sqrt(lx**2+ly**2+lz**2)
    lx,ly,lz=lx/ln,ly/ln,lz/ln
    mag=np.sqrt(dz_dx**2+dz_dy**2+1.0)
    nx=-dz_dx/mag; ny=-dz_dy/mag; nz=1.0/mag
    shade=np.clip(nx*lx+ny*ly+nz*lz,0.0,1.0); shade=0.55+shade*0.45
    rgb=np.clip(rgb*shade[:,:,np.newaxis],0,255)
    # Contours
    ci=0.08; contours=(height/ci).astype(int)
    ce=((contours!=np.roll(contours,1,axis=0))|(contours!=np.roll(contours,1,axis=1)))
    land=biome!=BIOME_OCEAN; rgb[ce&land]*=0.72
    # Roads
    if road_mask is not None:
        rgb[road_mask&land]=np.array([210,195,160],dtype=np.float32)
    rgb=np.clip(rgb,0,255).astype(np.uint8)
    # Plot markers
    for row,col in plot_positions:
        r0=max(0,row-2);r1=min(size,row+3);c0=max(0,col-2);c1=min(size,col+3)
        rgb[r0:r1,c0:c1]=(220,40,40)
    # Town marker
    cx=cy=size//2; ts=max(3,size//80)
    rgb[cy-ts:cy+ts,cx-ts:cx+ts]=(240,220,40)
    return rgb

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    p=argparse.ArgumentParser(description="Island Forge v2.0")
    p.add_argument("--audio",type=str,default=None)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--size",type=int,default=1009,choices=[513,1009,2017])
    p.add_argument("--plots",type=int,default=32)
    p.add_argument("--output",type=str,default="island")
    p.add_argument("--preview",action="store_true")
    p.add_argument("--spacing",type=int,default=40)
    p.add_argument("--water",type=float,default=0.20)
    p.add_argument("--cluster-angle",type=float,default=135.0)
    p.add_argument("--cluster-spread",type=float,default=1.0)
    args=p.parse_args()
    print(f"[gen] Island Forge v2.0  Seed={args.seed}  Size={args.size}  Plots={args.plots}")
    if args.audio:
        weights=analyse_audio(args.audio)
    else:
        weights={"sub_bass":0.5,"bass":0.5,"midrange":0.5,"presence":0.5,"brilliance":0.5,"tempo_bpm":120.0,"duration_s":0.0}
    height,road_mask=generate_terrain(args.size,args.seed,weights,water_level=args.water)
    print("[gen] Biomes..."); moisture=generate_moisture(args.size,args.seed)
    biome=classify_biomes(height,moisture,args.water)
    print(f"[gen] {args.plots} farm plots...")
    plots=find_plot_positions(height,biome,args.plots,args.size,args.spacing,args.cluster_angle,args.cluster_spread,args.seed)
    biome=paint_farm_biome(biome,plots,args.size,seed=args.seed)
    layout=build_layout(height,biome,plots,args.size,args.seed,weights,args.water)
    hm_16=(height*65535).astype(np.uint16)
    Image.fromarray(hm_16).save(f"{args.output}_heightmap.png")
    print(f"[out] {args.output}_heightmap.png")
    with open(f"{args.output}_layout.json","w") as f: json.dump(layout,f,indent=2)
    print(f"[out] {args.output}_layout.json")
    if args.preview:
        prev=build_preview(height,biome,plots,args.size,road_mask)
        Image.fromarray(prev,mode="RGB").save(f"{args.output}_preview.png")
        print(f"[out] {args.output}_preview.png")
    vc=layout["verse_constants"]
    print(f"\n── v2.0 done ─── peaks+rivers+roads+hillshade ──")
    print(f"  PLOTS={vc['PLOT_COUNT']}  TOWN={vc['TOWN_X']},{vc['TOWN_Y']}")
    print(f"  BIOMES={layout['biome_distribution_pct']}")

if __name__=="__main__": main()
