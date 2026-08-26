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
gt=[(e,)+dak_pos(e,tick0) for e in users if dak_pos(e,tick0)]

def make_bits(buf,msb=True):
    out=bytearray()
    for byte in buf:
        rng=range(7,-1,-1) if msb else range(8)
        for i in rng: out.append((byte>>i)&1)
    return out
def value_index(bl,w):
    idx=collections.defaultdict(list); v=0; mask=(1<<w)-1
    for i in range(w): v=(v<<1)|bl[i]
    idx[v].append(0)
    for off in range(1,len(bl)-w):
        v=((v<<1)|bl[off+w-1])&mask; idx[v].append(off)
    return idx

# 인접성 테스트: x오프셋과 y오프셋의 델타 히스토그램. tol=좌표 소수 반올림 오차 허용 위해 ±few
for msb in (True,False):
    bl=make_bits(sp,msb)
    for scale in (100,10):
        for w in (15,16,17,18):
            idx=value_index(bl,w)
            delta_votes=collections.Counter()  # (delta) -> set of players
            delta_players=collections.defaultdict(set)
            for e,x,y in gt:
                tx=round(x*scale); ty=round(y*scale)
                if tx>=(1<<w) or ty>=(1<<w): continue
                xoffs=set()
                for dv in range(-2,3):   # 반올림 허용
                    xoffs|=set(idx.get(tx+dv,[]))
                yoffs=set()
                for dv in range(-2,3):
                    yoffs|=set(idx.get(ty+dv,[]))
                for ox in xoffs:
                    for oy in yoffs:
                        d=oy-ox
                        if -64<=d<=64:      # 인접 범위만
                            delta_players[d].add(e)
            # 가장 많은 플레이어가 지지하는 델타
            best=sorted(delta_players.items(), key=lambda kv:-len(kv[1]))[:3]
            top=best[0] if best else (None,set())
            if len(top[1])>=6:
                print(f"{'MSB'if msb else'LSB'} ×{scale} w={w}: top delta={top[0]} supported by {len(top[1])}/24 players | next={[(d,len(s)) for d,s in best[1:3]]}")
print("done")
