import struct, collections, json, statistics

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
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

def smoothness(series):
    rng=max(series)-min(series)
    if rng==0: return 1e9,0
    d=[abs(series[i+1]-series[i]) for i in range(len(series)-1)]
    return statistics.median(d)/(rng+1), rng

OID=58
s=[(t,b) for t,tier,b in streams[OID] if tier==0 and len(b)>=6]
s.sort()
# 축 A = off0 w13. 축 B 자동탐색: off 13..40, w13, 가장 부드럽고 A와 상관 낮은 것
A=[bitread(b,0,13) for _,b in s]
tA=[t for t,_ in s]
cand=[]
for off in range(13,60):
    B=[bitread(b,off,13) for _,b in s]
    if any(v is None for v in B): continue
    sm,rng=smoothness(B)
    if rng<200: continue
    # A와 상관(겹치면 같은 필드) 낮아야
    cand.append((sm,off,rng))
cand.sort()
print("축B 후보 (smooth,off,range):", [(round(c[0],4),c[1],c[2]) for c in cand[:8]])
offB=cand[0][1]
B=[bitread(b,offB,13) for _,b in s]
print(f"\n선택: A=off0w13, B=off{offB}w13")
print("A head:",A[:8]); print("B head:",B[:8])

# dakgg 궤적 로드, 틱정렬 상관
r=json.load(open(r'C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/66230dd4-b9cf-4a3d-8a0d-9d5b5080e734/scratchpad/rosetta.json',encoding='utf-8'))
mv=r['moves']; users={u['id']:u['nickname'] for u in r['users']}
def dak_pos(eid,tick):
    pts=mv.get(str(eid));
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

def pearson(x,y):
    nx=len(x); mx=sum(x)/nx; my=sum(y)/nx
    sx=sum((v-mx)**2 for v in x)**.5; sy=sum((v-my)**2 for v in y)**.5
    if sx==0 or sy==0: return 0
    return sum((x[i]-mx)*(y[i]-my) for i in range(nx))/(sx*sy)

# 각 dakgg 엔티티에 대해 (A,B) vs (x,y) 최적 상관(축 교환·부호 포함)
print("\n=== oid58 (A,B) 를 dakgg 궤적과 상관 ===")
scores=[]
sample=list(range(0,len(s),max(1,len(s)//400)))
for eid in mv:
    if int(eid) not in users: continue
    dxy=[dak_pos(int(eid),tA[i]) for i in sample]
    if any(p is None for p in dxy): continue
    dx=[p[0] for p in dxy]; dy=[p[1] for p in dxy]
    aa=[A[i] for i in sample]; bb=[B[i] for i in sample]
    # 최적: A~x,B~y 또는 A~y,B~x
    c1=abs(pearson(aa,dx))+abs(pearson(bb,dy))
    c2=abs(pearson(aa,dy))+abs(pearson(bb,dx))
    best=max(c1,c2)
    scores.append((best,users[int(eid)],eid,round(pearson(aa,dx),2),round(pearson(bb,dy),2),round(pearson(aa,dy),2),round(pearson(bb,dx),2)))
scores.sort(reverse=True)
for sc in scores[:6]:
    print(f"  {sc[0]:.2f}  {sc[1]}(id{sc[2]})  A~x={sc[3]} B~y={sc[4]} | A~y={sc[5]} B~x={sc[6]}")
