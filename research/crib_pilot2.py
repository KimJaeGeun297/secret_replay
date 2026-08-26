import json, struct, collections

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
g = json.load(open(BASE+'/game.json', encoding='utf-8'))['userGames']
skins = {u['characterNum']: u['skinCode'] for u in g}
skinset = set(u['skinCode'] for u in g)
print("skinCodes:", sorted(skinset))
print("distinct skins:", len(skinset))

data = open(BASE+'/replay_work/63953953.er','rb').read()
REC = struct.Struct('<HHIII'); pos=0x410; n=len(data); snaps=[]
while pos+16<=n:
    kind,ver,tick,length,aux = REC.unpack_from(data,pos); payoff=pos+16
    if kind==2 and ver==1: snaps.append((tick, data[payoff:payoff+length]))
    pos=payoff+length
sp = snaps[0][1]

def bits(buf, msb=True):
    out=[]
    for byte in buf:
        if msb:
            for i in range(7,-1,-1): out.append((byte>>i)&1)
        else:
            for i in range(8): out.append((byte>>i)&1)
    return out

def search_values(bl, targets, wmin, wmax, label):
    N=len(bl); found=collections.defaultdict(list)
    for w in range(wmin,wmax+1):
        # 미리 각 오프셋 값 계산은 비싸므로 롤링
        v=0; mask=(1<<w)-1
        # 초기 w비트
        for i in range(w): v=(v<<1)|bl[i]
        if v in targets: found[v].append((0,w))
        for off in range(1, N-w):
            v=((v<<1)|bl[off+w-1])&mask
            if v in targets: found[v].append((off,w))
    print(f"\n[{label}] skinCode 히트: {len(found)}/{len(targets)} distinct skins found")
    for sk in sorted(found):
        locs=found[sk]
        print(f"  skin {sk}: {len(locs)} hit(s) -> {locs[:5]}")
    return found

bl_m=bits(sp,True); bl_l=bits(sp,False)
fm=search_values(bl_m, skinset, 18, 24, "MSB-first skinCode")
fl=search_values(bl_l, skinset, 18, 24, "LSB-first skinCode")

# 만약 신호 있으면: 같은 폭 w에서 여러 skin이 규칙적 stride로?
def stride_report(found, label):
    byw=collections.defaultdict(list)
    for sk,locs in found.items():
        for off,w in locs: byw[w].append((off,sk))
    print(f"\n[{label}] per-width offset structure:")
    for w in sorted(byw):
        offs=sorted(byw[w])
        if len(offs)>=3:
            gaps=[offs[i+1][0]-offs[i][0] for i in range(len(offs)-1)]
            print(f"  w={w}: {len(offs)} skins, offsets(sorted)[:10]={[o for o,_ in offs[:10]]}, gaps={gaps[:9]}")
stride_report(fm,"MSB"); stride_report(fl,"LSB")
