import struct, collections, statistics

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
data=open(BASE+'/replay_work/63953953.er','rb').read()
REC=struct.Struct('<HHIII'); n=len(data); pos=0x410
# objectId -> list of (tick, tier, body bytes)
streams=collections.defaultdict(list)
while pos+16<=n:
    kind,ver,tick,length,aux=REC.unpack_from(data,pos); off=pos+16
    if kind==1:
        body=data[off:off+length]
        streams[body[1]].append((tick, body[2], body[4:]))  # after [1B][oid][tier][00]
    pos=off+length

OID=58
s=[x for x in streams[OID] if x[1]==0]  # tier0
print(f"oid {OID}: {len(s)} tier0 packets")
lens=collections.Counter(len(b) for _,_,b in s)
print("body length histogram:", lens.most_common(10))

# 가장 흔한 길이만
L=lens.most_common(1)[0][0]
fix=[(t,b) for t,_,b in s if len(b)==L]
print(f"using body len {L}: {len(fix)} packets")

def bitread(buf, off, w):
    v=0
    for i in range(w):
        byte=(off+i)//8; bit=7-((off+i)%8)
        if byte>=len(buf): return None
        v=(v<<1)|((buf[byte]>>bit)&1)
    return v

# 각 (오프셋,폭) 후보에서 값 시계열의 "부드러움" 측정: 1차차분의 표준편차/범위
nbits=L*8
ticks=[t for t,_ in fix]
best=[]
for w in (12,13,14,15,16):
    for off in range(0, nbits-w):
        series=[]
        ok=True
        for _,b in fix[:200]:  # 앞 200패킷으로 스캔
            v=bitread(b,off,w)
            if v is None: ok=False;break
            series.append(v)
        if not ok or len(series)<50: continue
        rng=max(series)-min(series)
        if rng < (1<<(w-3)): continue  # 거의 안 변하면 좌표 아님(상수/플래그)
        diffs=[abs(series[i+1]-series[i]) for i in range(len(series)-1)]
        med=statistics.median(diffs) if diffs else 1e9
        # 부드러움 지표: 중앙값 스텝이 범위 대비 작을수록 연속 이동
        smooth = med/(rng+1)
        best.append((smooth, off, w, rng, med, series[:6]))
best.sort()
print("\n=== 가장 '부드러운' 비트필드 후보 (좌표 의심) ===")
for smooth,off,w,rng,med,head in best[:15]:
    print(f"  off={off:4d} w={w} range={rng:6d} medstep={med:5.0f} smooth={smooth:.4f} head={head}")
