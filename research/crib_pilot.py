import json, struct, collections, os

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
g = json.load(open(BASE+'/game.json', encoding='utf-8'))['userGames']
codes = [u['characterNum'] for u in g]
print("players:", len(g), " characterNums:", sorted(codes))
print("distinct codes:", len(set(codes)), " (dup:", [c for c,n in collections.Counter(codes).items() if n>1], ")")
codeset = set(codes)

# 모든 스냅샷 수집
data = open(BASE+'/replay_work/63953953.er','rb').read()
REC = struct.Struct('<HHIII'); pos=0x410; n=len(data); snaps=[]
while pos+16<=n:
    kind,ver,tick,length,aux = REC.unpack_from(data,pos); payoff=pos+16
    if kind==2 and ver==1: snaps.append((tick, data[payoff:payoff+length]))
    pos=payoff+length
print("snapshots:", len(snaps), " first tick:", snaps[0][0], " sizes:", [len(s) for _,s in snaps[:3]])

sp = snaps[0][1]
print("first snapshot bytes:", len(sp))

# 비트 리더 (MSB-first 및 LSB-first 둘 다 시도)
def bits_msb(buf):
    for byte in buf:
        for i in range(7,-1,-1): yield (byte>>i)&1
def bits_lsb(buf):
    for byte in buf:
        for i in range(8): yield (byte>>i)&1

def read_at(bitlist, off, w):
    v=0
    for i in range(w): v=(v<<1)|bitlist[off+i]
    return v

# known-plaintext 스캔: 각 폭 w, 각 비트오프셋에서 값이 codeset에 드는 위치 수집
def scan(bitlist, label):
    N=len(bitlist)
    print(f"\n[{label}] total bits={N}")
    best=[]
    for w in range(7,15):
        hits=[]  # (offset, value)
        maxv=(1<<w)-1
        # codeset 최대값보다 폭이 너무 크면 상위값 노이즈↑; 그래도 스캔
        for off in range(0, N-w):
            v=read_at(bitlist, off, w)
            if v in codeset:
                hits.append((off,v))
        # 히트가 규칙적 stride로 24개 근처 나오는지
        offs=[o for o,_ in hits]
        # stride 후보: 인접 히트 간격 최빈값
        if len(hits)>=20:
            gaps=collections.Counter(offs[i+1]-offs[i] for i in range(len(offs)-1))
            top=gaps.most_common(3)
            distinct_vals=len(set(v for _,v in hits))
            print(f"  w={w:2d}: {len(hits):5d} hits, {distinct_vals} distinct vals, top gaps={top}")
            best.append((w,len(hits),distinct_vals,top))
    return best

bl_m=list(bits_msb(sp)); bl_l=list(bits_lsb(sp))
scan(bl_m,"MSB-first")
scan(bl_l,"LSB-first")

# 추가: 스냅샷 안 codeset 값이 "정확히 24개, 각 팀 구조"로 뜨는 폭 있나 정밀 체크(MSB, w=8)
print("\n--- byte-aligned quick check (혹시 바이트정렬?) ---")
for w,name,step in [(8,'u8',1),(16,'u16-le',1)]:
    found=collections.Counter()
    for i in range(len(sp)-(w//8)):
        if w==8: v=sp[i]
        else: v=sp[i]|(sp[i+1]<<8)
        if v in codeset: found[v]+=1
    print(f"  {name}: distinct codes present={len(found)}/24, counts sample={dict(list(found.items())[:8])}")
