import json, struct, collections

BASE = r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
data = open(BASE+'/replay_work/63953953.er','rb').read()
REC = struct.Struct('<HHIII'); n=len(data)

records=[]
pos=0x410
while pos+16<=n:
    kind,ver,tick,length,aux = REC.unpack_from(data,pos); payoff=pos+16
    records.append((kind,ver,tick,length,aux,payoff))
    pos=payoff+length

# 1) 패킷 objectId 인벤토리
pkt_obj=collections.Counter()
tier0_obj=collections.Counter()
for kind,ver,tick,length,aux,off in records:
    if kind==1:
        oid=data[off+1]; pkt_obj[oid]+=1
        if data[off+2]==0: tier0_obj[oid]+=1
print("packet objectIds:", len(pkt_obj), "distinct")
print("  top by count:", pkt_obj.most_common(30))
print("  objectId set (sorted):", sorted(pkt_obj))

# 2) 스냅샷들 추출
snaps=[(tick,off,length) for kind,ver,tick,length,aux,off in records if kind==2 and ver==1]
print("\nsnapshots:", len(snaps))

def snap_bytes(i):
    tick,off,length=snaps[i]; return tick, data[off:off+length]

# 3) 스냅샷 안 0x1B 다음 바이트 = objectId 후보?
for si in [0,1,2]:
    tick,sp=snap_bytes(si)
    tag_pos=[i for i in range(len(sp)-1) if sp[i]==0x1B]
    follow=collections.Counter(sp[i+1] for i in tag_pos)
    inpkt=sum(c for b,c in follow.items() if b in pkt_obj)
    tot=sum(follow.values())
    print(f"\nsnap[{si}] tick={tick} len={len(sp)} : {len(tag_pos)} x 0x1B; follow-byte in packet-objIds: {inpkt}/{tot} ({inpkt/tot:.0%})")
    print("  follow-byte set (sorted):", sorted(follow))
    # 0x1B 간격
    gaps=[tag_pos[i+1]-tag_pos[i] for i in range(len(tag_pos)-1)]
    print("  0x1B gap histogram (top):", collections.Counter(gaps).most_common(8))
