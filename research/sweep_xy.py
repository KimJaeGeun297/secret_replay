import struct, collections, json, statistics

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
SC   = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/66230dd4-b9cf-4a3d-8a0d-9d5b5080e734/scratchpad"
data=open(BASE+'/replay_work/63953953.er','rb').read()
REC=struct.Struct('<HHIII'); n=len(data); pos=0x410
streams=collections.defaultdict(list)
while pos+16<=n:
    kind,ver,tick,length,aux=REC.unpack_from(data,pos); off=pos+16
    if kind==1:
        b=data[off:off+length]; streams[b[1]].append((tick,b[2],b[4:]))
    pos=off+length

def bitread(buf, off, w):
    v=0
    for i in range(w):
        byte=(off+i)//8; bit=7-((off+i)%8)
        if byte>=len(buf): return None
        v=(v<<1)|((buf[byte]>>bit)&1)
    return v

r=json.load(open(SC+'/rosetta.json',encoding='utf-8'))
mv=r['moves']; users={u['id']:u['nickname'] for u in r['users']}
def dak_pos(eid,tick):
    pts=mv.get(str(eid))
    if not pts: return None
    if tick<=pts[0][0]: return pts[0][1],pts[0][2]
    if tick>=pts[-1][0]: return pts[-1][1],pts[-1][2]
    lo,hi=0,len(pts)-1
    while lo<hi-1:
        m=(lo+hi)//2
        if pts[m][0]<=tick: lo=m
        else: hi=m
    a,bb=pts[lo],pts[hi]; f=(tick-a[0])/(bb[0]-a[0] or 1)
    return a[1]+(bb[1]-a[1])*f, a[2]+(bb[2]-a[2])*f
def pear(x,y):
    m=len(x); mx=sum(x)/m; my=sum(y)/m
    sx=sum((v-mx)**2 for v in x)**.5; sy=sum((v-my)**2 for v in y)**.5
    if sx==0 or sy==0: return 0
    return sum((x[i]-mx)*(y[i]-my) for i in range(m))/(sx*sy)

# 각 objectId: 최다빈도 body길이만, off=0..(L*8-13) 모든 위치에서 값시계열 뽑아
# dakgg 모든 플레이어의 x또는y와 |상관| 최대를 찾음. 전엔티티 통틀어 best 리포트.
GLOBAL=[]
player_ids=[e for e in mv if int(e) in users]
for oid,lst in streams.items():
    t0=[(t,b) for t,tier,b in lst if tier==0]
    if len(t0)<300: continue
    lc=collections.Counter(len(b) for _,b in t0)
    L=lc.most_common(1)[0][0]
    fix=[(t,b) for t,b in t0 if len(b)==L]
    if len(fix)<300: continue
    ticks=[t for t,_ in fix]
    idx=list(range(0,len(fix),max(1,len(fix)//300)))
    tk=[ticks[i] for i in idx]
    # dakgg 후보 미리 계산
    dcache={}
    for e in player_ids:
        ps=[dak_pos(int(e),t) for t in tk]
        if any(p is None for p in ps): continue
        dcache[e]=([p[0] for p in ps],[p[1] for p in ps])
    nbits=L*8
    for w in (13,14):
        for boff in range(0,nbits-w):
            ser=[bitread(fix[i][1],boff,w) for i in idx]
            if any(v is None for v in ser): continue
            if max(ser)-min(ser)< (1<<(w-4)): continue
            for e,(dx,dy) in dcache.items():
                c=max(abs(pear(ser,dx)),abs(pear(ser,dy)))
                if c>0.6:
                    GLOBAL.append((round(c,3),oid,boff,w,users[int(e)],e))
GLOBAL.sort(reverse=True)
print("=== |상관|>0.6 인 (er field) vs (dakgg 좌표) 매치 상위 ===")
for g in GLOBAL[:25]:
    print(f"  corr={g[0]} oid={g[1]} off={g[2]} w={g[3]}  ~ {g[4]}(id{g[5]})")
if not GLOBAL:
    print("  없음 — 고정오프셋으로 좌표 잡히는 필드 0개")
