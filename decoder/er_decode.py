"""er_decode.py — Eternal Return .er replay decoder (static RE; no bypass).
Format: record payload = Brotli-compressed -> MemoryPack.
Fully decoded & validated: framing, Brotli, MemoryPack container (ReplaySnapshot/GameSnapshot),
string encoding, per-entity position + hp + status block. See docs/er-replay-format.md.
Not yet decoded: deep nested PlayerCharacterSnapshot (characterCode/team/skills), delta-packet fields.
"""
import struct, brotli, json

REC=struct.Struct('<HHIII'); HDR=0x410
KIND={0:'eof',1:'delta',2:'snapshot',3:'definitions',4:'trailer',7:'keyframe_mark'}

def read_records(path):
    d=open(path,'rb').read()
    meta={'magic':d[:16].split(b'\x00')[0].decode(),'version':d[16:32].split(b'\x00')[0].decode(),
          'cdn':d[32:80].split(b'\x00')[0].decode()}
    pos=HDR; recs=[]
    while pos+16<=len(d):
        k,v,t,l,a=REC.unpack_from(d,pos); o=pos+16
        recs.append({'kind':k,'ver':v,'tick':t,'len':l,'aux':a,'payload':d[o:o+l]})
        pos=o+l
    return meta,recs

def decompress(rec):  # snapshot & delta payloads are raw Brotli
    return brotli.decompress(rec['payload'])

# --- MemoryPack string (validated): [int32 a][int32 utf16len][utf8 bytes], utf8len=~a ---
def read_mp_string(buf,o):
    a=struct.unpack_from('<i',buf,o)[0]; o+=4
    if a==0: return "",o
    if a==-1: return None,o
    ln=~a; u16=struct.unpack_from('<i',buf,o)[0]; o+=4
    s=buf[o:o+ln].decode('utf-8','replace'); return s,o+ln

# --- per-entity position/status extractor (validated: pos 1608 samples med err 0.43; hp 24/24) ---
# Entity record signature in decompressed snapshot: 07 02 00 00 00 <objId int32>
# Layout: +9 posXZ.x(f) +13 posXZ.z(f) ... +40 hp +44 sp +48 extraPoint +52 level
#         +56/60/64 shields(all/normal/skill) +68 moveSpeed(f)
def to_grid(fx,fz):   # world -> dakgg isometric grid (24-pt fit, residual<0.6)
    return (-1.645*fx-1.645*fz+290.1, -1.653*fx+1.652*fz+555.0)

def extract_entities(snap_decomp, lo=1, hi=100000):
    raw=snap_decomp; pat=bytes([7,2,0,0,0]); i=0; out={}
    while True:
        j=raw.find(pat,i)
        if j<0: break
        oid=struct.unpack_from('<i',raw,j+5)[0]
        if lo<=oid<=hi and oid not in out and j+72<=len(raw):
            fx=struct.unpack_from('<f',raw,j+9)[0]; fz=struct.unpack_from('<f',raw,j+13)[0]
            gx,gy=to_grid(fx,fz)
            out[oid]={'grid':(round(gx,1),round(gy,1)),'worldXZ':(round(fx,2),round(fz,2)),
                'hp':struct.unpack_from('<i',raw,j+40)[0],'sp':struct.unpack_from('<i',raw,j+44)[0],
                'level':struct.unpack_from('<i',raw,j+52)[0],
                'shield':struct.unpack_from('<i',raw,j+56)[0],
                'moveSpeed':round(struct.unpack_from('<f',raw,j+68)[0],3),'_off':j}
        i=j+1
    return out

if __name__=='__main__':
    BASE=r"C:/Users/kjg/AppData/Local/Temp/claude/C--Users-kjg/1fbeafe4-ec45-4593-88d9-9e6a70e7517b/scratchpad"
    meta,recs=read_records(BASE+'/replay_work/63953953.er')
    print("meta:",meta)
    from collections import Counter
    print("records:",Counter((r['kind'],r['ver']) for r in recs))
    snaps=[r for r in recs if r['kind']==2]
    ents=extract_entities(decompress(snaps[0]),1300,1345)
    print(f"snap0 tick={snaps[0]['tick']}: {len(ents)} player entities")
    for oid in sorted(ents)[:5]:
        print(" ",oid,ents[oid]['grid'],'hp',ents[oid]['hp'],'lv',ents[oid]['level'],'ms',ents[oid]['moveSpeed'])
