"""ER .er 리플레이 → per-entity {objectId, position(grid), hp, sp, level, shields, moveSpeed}
포맷: 레코드 payload = Brotli → MemoryPack. 엔티티 레코드 시그니처 07 02 00 00 00 <objId>.
검증: dakgg 동일게임 대조."""
import struct, brotli, json

def load_snaps(path):
    erd=open(path,'rb').read(); REC=struct.Struct('<HHIII'); pos=0x410; out=[]
    while pos+16<=len(erd):
        k,v,t,l,a=REC.unpack_from(erd,pos); o=pos+16
        if k==2 and v==1: out.append((t,erd[o:o+l]))
        pos=o+l
    return out

def to_grid(fx,fz):  # world→dakgg 미니맵 그리드 (아핀; 24점 피팅, 잔차<0.6)
    return (-1.645*fx-1.645*fz+290.1, -1.653*fx+1.652*fz+555.0)

def extract(rawsnap, lo=1300, hi=1345):
    raw=brotli.decompress(rawsnap); pat=bytes([7,2,0,0,0]); i=0; res={}
    while True:
        j=raw.find(pat,i)
        if j<0: break
        oid=struct.unpack_from('<i',raw,j+5)[0]
        if lo<=oid<=hi and oid not in res:
            fx=struct.unpack_from('<f',raw,j+9)[0]; fz=struct.unpack_from('<f',raw,j+13)[0]
            gx,gy=to_grid(fx,fz)
            res[oid]={'pos':(round(gx,1),round(gy,1)),'worldXZ':(round(fx,2),round(fz,2)),
                'hp':struct.unpack_from('<i',raw,j+40)[0],
                'sp':struct.unpack_from('<i',raw,j+44)[0],
                'extraPoint':struct.unpack_from('<i',raw,j+48)[0],
                'level':struct.unpack_from('<i',raw,j+52)[0],
                'shieldAll':struct.unpack_from('<i',raw,j+56)[0],
                'shieldNormal':struct.unpack_from('<i',raw,j+60)[0],
                'shieldSkill':struct.unpack_from('<i',raw,j+64)[0],
                'moveSpeed':round(struct.unpack_from('<f',raw,j+68)[0],3)}
        i=j+1
    return res

if __name__=='__main__':
    BASE=r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
    d=json.load(open('rosetta.json',encoding='utf-8'))
    id2nick={u['id']:u['nickname'] for u in d['users']}
    snaps=load_snaps(BASE+'/replay_work/63953953.er')
    r=extract(snaps[0][1])
    print(f"tick {snaps[0][0]}: {len(r)} players extracted\n")
    print(f"{'oid':4} {'nick':14} {'pos(grid)':16} {'hp':5} {'SP':4} {'lv':3} {'moveSpd':7}")
    for oid in sorted(r):
        e=r[oid]; nk=id2nick.get(oid,'?')[:13]
        print(f"{oid:4} {nk:14} {str(e['pos']):16} {e['hp']:5} {e['sp']:4} {e['level']:3} {e['moveSpeed']:7}")
