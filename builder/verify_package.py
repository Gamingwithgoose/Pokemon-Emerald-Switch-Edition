"""Independent personal NSP validation; never emits keys."""
import sys,pathlib,struct,hashlib,json

from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
import argparse
p=argparse.ArgumentParser()
for name in ['stage','nsp','keys','out']:p.add_argument('--'+name,type=pathlib.Path,required=True)
a=p.parse_args();ST=a.stage;P=a.out.parent
manifest=json.loads((ST/'manifest.json').read_text());TITLE_ID=int(manifest['title_id'],16)
keys={}
for line in a.keys.read_text().splitlines():
 if '=' in line:
  k,v=line.split('=',1)
  if k.strip() in ['header_key','key_area_key_application_00']:keys[k.strip()]=bytes.fromhex(v.strip())
def decrypt(data,key,mode):
 d=Cipher(algorithms.AES(key),mode).decryptor();return d.update(data)+d.finalize()
def pfs(b):
 assert b[:4]==b'PFS0';count,strings=struct.unpack_from('<II',b,4);base=16+24*count+strings;out={}
 for i in range(count):
  off,n,sn,_=struct.unpack_from('<QQII',b,16+24*i);s=16+24*count+sn;name=b[s:b.index(0,s)].decode();assert base+off+n<=len(b);out[name]=b[base+off:base+off+n]
 return out
nsp=a.nsp.read_bytes();files=pfs(nsp);assert len(files)==3
records={};program_files=None;cnmt=None;control=None
for name,b in files.items():
 digest=hashlib.sha256(b).digest();assert name.split('.')[0]==digest[:16].hex()
 h=b''.join(decrypt(b[i:i+512],keys['header_key'],modes.XTS((i//512).to_bytes(16,'big'))) for i in range(0,0xc00,512))
 assert h[0x200:0x204]==b'NCA3';assert struct.unpack_from('<Q',h,0x210)[0]==TITLE_ID
 assert struct.unpack_from('<Q',h,0x208)[0]==len(b);assert h[0x230:0x240]==bytes(16)
 area=decrypt(h[0x300:0x340],keys['key_area_key_application_00'],modes.ECB());ctype=h[0x205]
 records[digest[:16]]=(digest,len(b),ctype)
 for i in range(4):
  start,end=struct.unpack_from('<II',h,0x240+16*i);start*=512;end*=512
  if start==end:continue
  fs=h[0x400+512*i:0x600+512*i];assert hashlib.sha256(fs).digest()==h[0x280+32*i:0x2a0+32*i]
  assert end<=len(b)
  enc=fs[4];assert enc in [1,3]
  d=b[start:end] if enc==1 else decrypt(b[start:end],area[32:48],modes.CTR(fs[0x140:0x148][::-1]+(start//16).to_bytes(8,'big')))
  if fs[3]==2:
   bs=struct.unpack_from('<I',fs,0x28)[0];htoff,htsize,poff,psize=struct.unpack_from('<QQQQ',fs,0x30)
   ht=d[htoff:htoff+htsize];assert hashlib.sha256(ht).digest()==fs[8:40]
   content=d[poff:poff+psize]
   for j in range(0,len(content),bs):assert hashlib.sha256(content[j:j+bs]).digest()==ht[j//bs*32:j//bs*32+32]
   extracted=pfs(content)
   if ctype==0:program_files=extracted
   if ctype==1:cnmt=next(v for k,v in extracted.items() if k.endswith('.cnmt'))
  elif ctype==2:
   nacp=(ST/'control/control.nacp').read_bytes();icon=(ST/'control/icon_AmericanEnglish.dat').read_bytes();assert nacp in d and icon in d;control=nacp
  elif ctype==0:
   assert (ST/'romfs'/manifest['internal_rom_name']).read_bytes() in d
assert program_files and cnmt and control
for name in ['main','subsdk0','rtld','sdk','main.npdm']:assert program_files[name]==(ST/'exefs'/name).read_bytes()
assert struct.unpack_from('<Q',cnmt)[0]==TITLE_ID
assert struct.unpack_from('<I',cnmt,8)[0]==manifest['title_version']
extsize,count=struct.unpack_from('<HH',cnmt,14);assert count==2
for i in range(count):
 r=cnmt[32+extsize+56*i:32+extsize+56*(i+1)];digest,size,ctype=records[r[32:48]];assert r[:32]==digest and int.from_bytes(r[48:54],'little')==size
assert struct.unpack_from('<Q',control,0x3078)[0]==TITLE_ID
assert control[0x3060:0x3070].split(b'\0')[0]==b'1.0.0'
for i in range(16):assert control[i*0x300+0x200:(i+1)*0x300].split(b'\0')[0]==b'Nintendo'
assert control[0x30b0:0x30f0]==struct.pack('<8Q',0x01006FA0233F8000,*([0x010034D02340E000]*7))
npdm=program_files['main.npdm']
aci=struct.unpack_from('<I',npdm,0x70)[0];acid=struct.unpack_from('<I',npdm,0x78)[0]
assert struct.unpack_from('<Q',npdm,aci+0x10)[0]==TITLE_ID
assert struct.unpack_from('<QQ',npdm,acid+0x210)==(TITLE_ID,TITLE_ID)
off,size=struct.unpack_from('<II',npdm,aci+0x20)
assert npdm[aci+off:aci+off+size].count(struct.pack('<Q',TITLE_ID))==1
for old in [0x010034D02340E000]:assert struct.pack('<Q',old) not in npdm
for off,expected in [(0x3038,TITLE_ID),(0x3070,TITLE_ID+0x1000),(0x3078,TITLE_ID),(0x30f8,TITLE_ID)]:assert struct.unpack_from('<Q',control,off)[0]==expected
assert hashlib.sha256((ST/'romfs'/manifest['internal_rom_name']).read_bytes()).hexdigest()==manifest['rom_sha256']
report={'result':'PASS','checks':['NSP entry bounds','NCA content IDs and sizes','decrypted NCA application IDs','NCA filesystem header hashes','ExeFS and CNMT block hashes','embedded executable files match staged RTC/save build','embedded game ROM matches staged input','embedded selected icon and NACP match staged files','CNMT references/hash/size','independent save owner'], 'hardware_status':manifest['hardware_baseline']+'; this local rebuild still requires a console check','nsp_sha256':hashlib.sha256(nsp).hexdigest()}
a.out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

