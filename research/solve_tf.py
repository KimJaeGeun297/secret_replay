import json, struct, collections

D  = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
SC = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/66230dd4-b9cf-4a3d-8a0d-9d5b5080e734/scratchpad"

area_pos = json.load(open(D+'/replay_work/area_positions.json',encoding='utf-8'))
area_api = json.load(open(D+'/replay_work/area_api.json',encoding='utf-8'))['data']
code2name = {a['code']:a['name'] for a in area_api}

game = json.load(open(D+'/game.json',encoding='utf-8'))['userGames']
r = json.load(open(SC+'/rosetta.json',encoding='utf-8'))
mv=r['meta'] if 'meta' in r else None
moves=r['moves']; users={u['id']:u['nickname'] for u in r['users']}
nick2id={v:k for k,v in users.items()}
startSeq=r['startSeq']; endSeq=r['endSeq']

def pos_at(eid,tick):
    pts=moves.get(str(eid))
    if not pts: return None
    if tick<=pts[0][0]: return pts[0][1],pts[0][2]
    if tick>=pts[-1][0]: return pts[-1][1],pts[-1][2]
    lo,hi=0,len(pts)-1
    while lo<hi-1:
        m=(lo+hi)//2
        if pts[m][0]<=tick: lo=m
        else: hi=m
    a,b=pts[lo],pts[hi]; f=(tick-a[0])/(b[0]-a[0] or 1)
    return a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f

# 앵커: (dakgg좌표, 맵좌표)
# start: placeOfStart 구역 <-> 게임 초반 dakgg 위치
# death: placeOfDeath 구역 <-> 사망시각 dakgg 위치
maxdur=max(u['duration'] for u in game); off=maxdur-(endSeq-startSeq)/60
anchors=[]
for u in game:
    nk=u['nickname']; eid=nick2id.get(nk)
    if eid is None: continue
    # start
    for code_key,when in [('placeOfStart','start'),('placeOfDeath','death')]:
        code=int(u.get(code_key)) if str(u.get(code_key)).lstrip('-').isdigit() else None
        nm=code2name.get(code)
        if nm and nm in area_pos and area_pos[nm]!=[0.0,0.0]:
            if when=='start':
                p=pos_at(eid, startSeq+120)   # +2s
            else:
                dt=u['duration']-off
                p=pos_at(eid, startSeq+dt*60-60)
            if p: anchors.append((p[0],p[1], area_pos[nm][0], area_pos[nm][1], nk, when, nm))
print("anchors:", len(anchors))

# 아핀 최소제곱 (numpy 없이 정규방정식): [X Y 1]·M = [U V]
# dakgg (X,Y) -> map (U,V)
import math
def solve_affine(pts):
    # pts: list of (X,Y,U,V)
    # 6 params: U=aX+bY+c ; V=dX+eY+f  -> 각각 3변수 최소제곱
    def lstsq3(rows, target):
        # normal equations A^T A x = A^T b, A rows=[X,Y,1]
        ATA=[[0]*3 for _ in range(3)]; ATb=[0]*3
        for (X,Y,_,_),t in zip(pts,target):
            a=[X,Y,1.0]
            for i in range(3):
                ATb[i]+=a[i]*t
                for j in range(3): ATA[i][j]+=a[i]*a[j]
        # solve 3x3
        import copy
        M=[row[:]+[ATb[i]] for i,row in enumerate(ATA)]
        for i in range(3):
            piv=M[i][i]
            if abs(piv)<1e-12: return None
            for j in range(i,4): M[i][j]/=piv
            for k in range(3):
                if k!=i:
                    f=M[k][i]
                    for j in range(i,4): M[k][j]-=f*M[i][j]
        return [M[0][3],M[1][3],M[2][3]]
    U=[p[2] for p in pts]; V=[p[3] for p in pts]
    su=lstsq3(pts,U); sv=lstsq3(pts,V)
    return su,sv
pts=[(a[0],a[1],a[2],a[3]) for a in anchors]
su,sv=solve_affine(pts)
print("U = %.4f*X + %.4f*Y + %.2f"%tuple(su))
print("V = %.4f*X + %.4f*Y + %.2f"%tuple(sv))
# 잔차
res=[]
for (X,Y,U,V) in pts:
    pu=su[0]*X+su[1]*Y+su[2]; pv=sv[0]*X+sv[1]*Y+sv[2]
    res.append(((pu-U)**2+(pv-V)**2)**.5)
res.sort()
print("residual (map units): median %.1f  90pct %.1f  max %.1f"%(res[len(res)//2],res[int(len(res)*.9)],res[-1]))
print("map coord span for reference: x", min(a[2] for a in anchors),"~",max(a[2] for a in anchors))
