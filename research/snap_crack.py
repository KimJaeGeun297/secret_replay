import struct, collections, json

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
SC   = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/66230dd4-b9cf-4a3d-8a0d-9d5b5080e734/scratchpad"
data=open(BASE+'/replay_work/63953953.er','rb').read()
REC=struct.Struct('<HHIII'); n=len(data); pos=0x410
snaps=[]
while pos+16<=n:
    kind,ver,tick,length,aux=REC.unpack_from(data,pos); off=pos+16
    if kind==2 and ver==1: snaps.append((tick,data[off:off+length]))
    pos=off+length
tick0,sp=snaps[0]
print("snap0 tick",tick0,"len",len(sp))

# dakgg 정답: snap tick에서 24명 위치
r=json.load(open(SC+'/rosetta.json',encoding='utf-8'))
mv=r['moves']; users=[u['id'] for u in r['users']]
def dak_pos(eid,tick):
    pts=mv.get(str(eid))
    if not pts: return None
    if tick<=pts[0][0]: return pts[0][1],pts[0][2]
    if tick>=pts[-1][0]: return None
    lo,hi=0,len(pts)-1
    while lo<hi-1:
        m=(lo+hi)//2
        if pts[m][0]<=tick: lo=m
        else: hi=m
    a,b=pts[lo],pts[hi]; f=(tick-a[0])/(b[0]-a[0] or 1)
    return a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f
gt=[]
for e in users:
    p=dak_pos(e,tick0)
    if p: gt.append((e,p[0],p[1]))
print("ground-truth players at tick:", len(gt))
print("dakgg coord ranges: x",min(g[1] for g in gt),"~",max(g[1] for g in gt),
      " y",min(g[2] for g in gt),"~",max(g[2] for g in gt))

# 비트스트림(양방향) 준비
def make_bits(buf,msb=True):
    out=bytearray()
    for byte in buf:
        if msb:
            for i in range(7,-1,-1): out.append((byte>>i)&1)
        else:
            for i in range(8): out.append((byte>>i)&1)
    return out
def all_values(bl,w):
    # 반환: dict value-> list offsets (희소하게, 특정 타깃만 쓸거라 전체 인덱스 map)
    idx=collections.defaultdict(list); v=0; mask=(1<<w)-1
    for i in range(w): v=(v<<1)|bl[i]
    idx[v].append(0)
    for off in range(1,len(bl)-w):
        v=((v<<1)|bl[off+w-1])&mask; idx[v].append(off)
    return idx

for msb in (True,False):
    bl=make_bits(sp,msb)
    for scale in (1,10,100):
        for w in (14,15,16,17,18):
            idx=all_values(bl,w)
            # 각 플레이어 x,y 타깃이 존재하는지
            fx=0; fy=0; both=0; hitoffs=[]
            for e,x,y in gt:
                tx=round(x*scale); ty=round(y*scale)
                hx = tx in idx and tx< (1<<w)
                hy = ty in idx and ty< (1<<w)
                if hx: fx+=1
                if hy: fy+=1
                if hx and hy: both+=1
            # 노이즈 기대: 각 타깃이 우연히 있을 확률 ~ (검색공간/2^w). 대략 len(bl)/2^w per value
            exp = len(bl)/(1<<w)
            if fx>=8 or fy>=8:
                print(f"  {'MSB' if msb else 'LSB'} scale×{scale} w={w}: x找 {fx}/24, y找 {fy}/24, both {both}  (noise~{exp:.2f}/val)")
print("done")
