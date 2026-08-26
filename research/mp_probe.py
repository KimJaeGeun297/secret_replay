import dnfile, time
P=r"C:/Users/kjg/Downloads/IL2CppDumper/Dump0/DummyDll/Assembly-CSharp.dll"
pe=dnfile.dnPE(P)
mdt=pe.net.mdtables
ca=mdt.CustomAttribute.rows[100]
print("CA row attrs:",[a for a in dir(ca) if not a.startswith('__')])
t=ca.Type
print("Type type:",type(t).__name__,"attrs:",[a for a in dir(t) if not a.startswith('__')])
for a in ['table','row_index','table_name','value','row']:
    try:print(" Type.",a,"=",getattr(t,a) if a!='row' else type(getattr(t,a)).__name__)
    except Exception as e:print(" Type.",a,"ERR",e)
p=ca.Parent
print("Parent type:",type(p).__name__)
for a in ['table','row_index','table_name']:
    try:print(" Parent.",a,"=",getattr(p,a))
    except Exception as e:print(" Parent.",a,"ERR",e)
