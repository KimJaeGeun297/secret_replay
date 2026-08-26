import dnfile, json, struct, sys, time
t0=time.time()
P=r"C:/Users/kjg/Downloads/IL2CppDumper/Dump0/DummyDll/Assembly-CSharp.dll"
print("loading...",flush=True)
pe=dnfile.dnPE(P, clr_lazy_load=True) if 'clr_lazy_load' in dnfile.dnPE.__init__.__code__.co_varnames else dnfile.dnPE(P)
mdt=pe.net.mdtables
print(f"loaded {time.time()-t0:.0f}s TypeDef={len(mdt.TypeDef.rows)} CA={len(mdt.CustomAttribute.rows)}",flush=True)

def tn(r):
    try:
        ns=r.TypeNamespace;nm=r.TypeName;return (ns+'.'+nm) if ns else nm
    except:return None

def serstr(b,o):
    if o>=len(b) or b[o]==0xFF:return None,o+1
    x=b[o]
    if x&0x80==0:ln=x;o+=1
    elif x&0xC0==0x80:ln=((x&0x3f)<<8)|b[o+1];o+=2
    else:ln=((x&0x1f)<<24)|(b[o+1]<<16)|(b[o+2]<<8)|b[o+3];o+=4
    return b[o:o+ln].decode('utf-8','replace'),o+ln

# cache: resolve ctor-> attr type name, keyed by id(row)
cache={}
def ca_attr_name(ca):
    t=ca.Type
    row=getattr(t,'row',None)
    if row is None:return None
    key=id(row)
    if key in cache:return cache[key]
    cls=getattr(row,'Class',None)
    nm=None
    if cls is not None:
        cr=getattr(cls,'row',None)
        if cr is not None:
            nm=tn(cr) if hasattr(cr,'TypeName') else getattr(cr,'Name',None)
    else:
        # MethodDef -> owner typedef: search? skip
        pass
    cache[key]=nm;return nm

unions={};orders={}
TARGET={'SnapshotWrapper','SnapshotWrapperFull','SnapshotWrapperBasic','CharacterSnapshot',
'PlayerCharacterSnapshot','CharacterStatusSnapshot','BaseCharacterStatusSnapshot','MoveAgentSnapshot',
'MoveToDestinationSnapshot','MonsterSnapshot','ProjectileSnapshot'}
n=0;t1=time.time()
for ca in mdt.CustomAttribute.rows:
    n+=1
    if n%50000==0:print(f"  CA {n} {time.time()-t1:.0f}s unions={len(unions)}",flush=True)
    nm=ca_attr_name(ca)
    if not nm:continue
    s=nm.split('.')[-1]
    if s=='MemoryPackUnionAttribute':
        par=getattr(ca.Parent,'row',None)
        base=tn(par) if par is not None and hasattr(par,'TypeName') else None
        b=bytes(ca.Value) if ca.Value else b''
        if base and len(b)>=4 and b[0]==1:
            o=2;tag=struct.unpack_from('<H',b,o)[0];ty,_=serstr(b,o+2)
            if not ty or not any(c.isalpha() for c in ty):
                tag=struct.unpack_from('<i',b,o)[0];ty,_=serstr(b,o+4)
            if ty:unions.setdefault(base,{})[tag]=ty.split(',')[0].split('.')[-1]
    elif s=='MemoryPackOrderAttribute':
        par=getattr(ca.Parent,'row',None)
        if par is not None and hasattr(par,'Name'):  # Field row
            b=bytes(ca.Value) if ca.Value else b''
            if len(b)>=4 and b[0]==1:
                order=struct.unpack_from('<H',b,2)[0]
                orders[id(par)]=(par.Name,order)
print(f"done {time.time()-t0:.0f}s unions={len(unions)}",flush=True)
json.dump({'unions':unions},open('mempack_meta.json','w'),ensure_ascii=False,indent=1)
for base,m in unions.items():
    print("UNION",base,"->",m,flush=True)
