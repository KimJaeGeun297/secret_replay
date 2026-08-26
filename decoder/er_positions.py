import struct, brotli, json

BASE=r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
# .er → snapshots
def load_snaps(path):
    erd=open(path,'rb').read(); REC=struct.Struct('<HHIII'); pos=0x410; out=[]
    while pos+16<=len(erd):
        k,v,t,l,a=REC.unpack_from(erd,pos); o=pos+16
        if k==2 and v==1: out.append((t,erd[o:o+l]))
        pos=o+l
    return out

# 레코드: 07 02 00 00 00 <objId int> <posXZ.x f> <posXZ.z f>
def extract_positions(rawsnap, id_lo=1300, id_hi=1345):
    raw=brotli.decompress(rawsnap); pat=bytes([7,2,0,0,0]); i=0; res={}
    while True:
        j=raw.find(pat,i)
        if j<0: break
        oid=struct.unpack_from('<i',raw,j+5)[0]
        if id_lo<=oid<=id_hi and oid not in res:
            fx=struct.unpack_from('<f',raw,j+9)[0]
            fz=struct.unpack_from('<f',raw,j+13)[0]
            res[oid]=(fx,fz)
        i=j+1
    return res

# world(fx,fz) → dakgg grid (아핀; snap0 24점 피팅값)
def to_grid(fx,fz):
    return (-1.645*fx -1.645*fz +290.1, -1.653*fx +1.652*fz +555.0)

if __name__=='__main__':
    d=json.load(open('rosetta.json',encoding='utf-8'))
    snaps=load_snaps(BASE+'/replay_work/63953953.er')
    # dakgg 궤적
    mv=d['moves']
    def dakpos(oid,tick):
        pts=mv.get(str(oid));
        if not pts:return None
        if tick<=pts[0][0]:return pts[0][1],pts[0][2]
        if tick>=pts[-1][0]:return pts[-1][1],pts[-1][2]
        lo,hi=0,len(pts)-1
        while lo<hi-1:
            m=(lo+hi)//2
            if pts[m][0]<=tick:lo=m
            else:hi=m
        a,b=pts[lo],pts[hi];f=(tick-a[0])/(b[0]-a[0] or 1)
        return a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f

    errs=[]; nsnap=0; total=0
    for tick,sp in snaps:
        pos=extract_positions(sp)
        if not pos: continue
        nsnap+=1
        for oid,(fx,fz) in pos.items():
            gx,gy=to_grid(fx,fz); dk=dakpos(oid,tick)
            if dk:
                e=((gx-dk[0])**2+(gy-dk[1])**2)**.5
                errs.append(e); total+=1
    errs.sort()
    print(f"snapshots with positions: {nsnap}/{len(snaps)}")
    print(f"total (entity,snapshot) position samples validated vs dakgg: {total}")
    print(f"position error (grid units) vs dakgg interpolated: median={errs[len(errs)//2]:.2f} p90={errs[int(len(errs)*.9)]:.2f} max={errs[-1]:.2f}")
    # 첫 스냅샷 표
    print("\n[snap0 tick 2878] oid | .er→grid | dakgg")
    pos=extract_positions(snaps[0][1])
    for oid in sorted(pos):
        fx,fz=pos[oid]; gx,gy=to_grid(fx,fz); dk=dakpos(oid,2878)
        print(f"  {oid} | ({gx:6.1f},{gy:6.1f}) | {dk}")
