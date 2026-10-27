"""Rebuild the tested Emerald W6 application from exact user-supplied inputs."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, uuid
import lz4.block
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
TITLE='0100E04D454C0000'
sha=lambda b:hashlib.sha256(b).hexdigest()

def require(condition, message):
    if not condition: raise ValueError(message)

def unpack(path):
    b=path.read_bytes();require(b[:4]==b'NSO0',f'{path.name}: expected an NSO executable')
    h=bytearray(b[:256]);image=bytearray();segments=[]
    flags=struct.unpack_from('<I',h,12)[0]
    for i in range(3):
        off,va,n=struct.unpack_from('<III',h,16+16*i)
        cn=struct.unpack_from('<I',h,96+4*i)[0]
        d=lz4.block.decompress(b[off:off+cn],uncompressed_size=n) if flags&(1<<i) else b[off:off+n]
        require(len(d)==n and sha(d)==h[160+32*i:192+32*i].hex(),f'{path.name}: invalid segment hash')
        image.extend(bytes(max(0,va-len(image))));image.extend(d);segments.append((va,n))
    return h,image,segments

def apply(data,writes):
    for off,value in writes:
        value=bytes.fromhex(value)
        require(0<=off and off+len(value)<=len(data),'Patch exceeds input bounds')
        data[off:off+len(value)]=value

def repack(header,image,segments,entry,dest):
    h=bytearray(header);struct.pack_into('<I',h,12,struct.unpack_from('<I',h,12)[0]&~7)
    struct.pack_into('<I',h,60,entry['bss_size'])
    chunks=[(va,bytes(image[va:va+(entry['text_size'] if i==0 else n)])) for i,(va,n) in enumerate(segments)]
    digest=hashlib.sha256(b'Emerald standalone v1'+b''.join(d for _,d in chunks)).digest()
    require(digest.hex()==entry['target_build_id'],'Patched executable differs from the tested build')
    h[64:96]=digest;out=bytearray(h)
    for i,(va,d) in enumerate(chunks):
        struct.pack_into('<III',out,16+16*i,len(out),va,len(d))
        struct.pack_into('<I',out,96+4*i,len(d));out[160+32*i:192+32*i]=hashlib.sha256(d).digest();out.extend(d)
    dest.write_bytes(out);unpack(dest)

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    patch=json.loads((ROOT/'builder/patches.json').read_text())
    release=patch['release']
    require(release['candidate']=='W6' and release['title_version']==11,'Unsupported builder patch release')
    exefs=ROOT/'switch files/exefs';control=ROOT/'switch files/control 0/control.nacp'
    keys=ROOT/'switch files/prod.keys';roms=list((ROOT/'Emerald rom').glob('*.gba'))
    required=[exefs/n for n in ['main','subsdk0','rtld','sdk','main.npdm']]+[control,keys]
    missing=[str(x.relative_to(ROOT)) for x in required if not x.is_file()]
    require(not missing,'Missing files:\n  '+'\n  '.join(missing))
    require(len(roms)==1,'Put exactly one uncompressed English Emerald .gba file in Emerald rom.')
    originals={path:path.read_bytes() for path in required+[roms[0]]}
    for name in ['main','subsdk0']:
        require(sha(originals[exefs/name])==patch[name]['source_sha256'],f'{name}: unsupported dump. Use the original LeafGreen v0 ExeFS listed in README.md.')
    for name,digest in patch['unchanged_exefs'].items():
        require(sha(originals[exefs/name])==digest,f'{name}: unsupported or modified dump')
    require(sha(originals[exefs/'main.npdm'])==patch['npdm_sha256'],'main.npdm: unsupported or modified dump')
    require(sha(originals[control])==patch['control']['source_sha256'],'control.nacp: unsupported control metadata')
    require(sha(originals[roms[0]])==patch['rom']['source_sha256'],'ROM does not match vanilla English Emerald. See the SHA-256 in README.md.')
    available=set()
    for line in originals[keys].decode('utf-8-sig').splitlines():
        if '=' in line: available.add(line.split('=',1)[0].strip())
    require({'header_key','key_area_key_application_00'}<=available,'prod.keys is missing header_key or key_area_key_application_00. Key values are never displayed.')
    icons=[x for x in (ROOT/'Homescreen Icon').iterdir() if x.is_file() and x.suffix.lower() in ['.png','.jpg','.jpeg','.webp','.bmp']]
    require(len(icons)<=1,'Keep only one supported image in Homescreen Icon.')
    if icons:
        with Image.open(icons[0]) as im: im.verify()
    print('Input checks passed. Original files will be left untouched.',flush=True)
    if a.check: return
    stage=ROOT/'.build'/('run-'+uuid.uuid4().hex[:10]);stage.mkdir(parents=True)
    for folder in ['exefs','control','romfs','ncas','result']: (stage/folder).mkdir()
    for name in ['main','subsdk0']:
        h,image,segs=unpack(exefs/name);apply(image,patch[name]['writes'])
        repack(h,image,segs,patch[name],stage/'exefs'/name)
    for name in ['rtld','sdk']: shutil.copyfile(exefs/name,stage/'exefs'/name)
    npdm=bytearray(originals[exefs/'main.npdm']);aci=struct.unpack_from('<I',npdm,0x70)[0];acid=struct.unpack_from('<I',npdm,0x78)[0]
    old=0x010034D02340E000;new=int(TITLE,16)
    npdm[0x20:0x30]=b'EmeraldRTC'.ljust(16,b'\0')
    struct.pack_into('<Q',npdm,aci+0x10,new);struct.pack_into('<QQ',npdm,acid+0x210,new,new)
    off,size=struct.unpack_from('<II',npdm,aci+0x20);start=aci+off
    grants=bytes(npdm[start:start+size]);require(grants.count(struct.pack('<Q',old))==1,'Unexpected save-owner permissions')
    npdm[start:start+size]=grants.replace(struct.pack('<Q',old),struct.pack('<Q',new))
    (stage/'exefs/main.npdm').write_bytes(npdm)
    n=bytearray(originals[control]);apply(n,patch['control']['writes'])
    require(sha(n)==patch['control']['target_sha256'],'Control reconstruction failed')
    (stage/'control/control.nacp').write_bytes(n)
    rom=bytearray(originals[roms[0]]);apply(rom,patch['rom']['writes'])
    require(sha(rom)==patch['rom']['target_sha256'],'ROM reconstruction failed')
    (stage/'romfs/Emerald_e.gba').write_bytes(rom)
    if icons:
        with Image.open(icons[0]) as im:
            im=im.convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
            im.save(stage/'control/icon_AmericanEnglish.dat','JPEG',quality=95)
    else:
        im=Image.new('RGB',(256,256),'#063f30');draw=ImageDraw.Draw(im)
        draw.polygon([(128,24),(199,87),(168,158),(88,158),(57,87)],fill='#27c988',outline='#c5ffe7',width=4)
        draw.line([(128,24),(105,90),(128,158),(151,90),(128,24),(57,87),(199,87)],fill='#c5ffe7',width=3)
        draw.text((128,205),'EMERALD',anchor='mm',font_size=29,fill='white')
        im.save(stage/'control/icon_AmericanEnglish.dat','JPEG',quality=95)
    manifest={'title':'Pokemon Emerald','title_id':TITLE,'title_version':release['title_version'],'display_version':'1.0.0',
              'internal_rom_name':'Emerald_e.gba','internal_save_name':'Emerald_e.sav',
              'main_build_id':patch['main']['target_build_id'],'subsdk0_build_id':patch['subsdk0']['target_build_id'],
              'rom_sha256':sha(rom),'wireless_candidate':release['candidate'],
              'hardware_baseline':release['hardware_status'],'icon':'custom' if icons else 'generated emerald symbol'}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2))
    tool=ROOT/'tools/hacpack.exe';log=stage/'build.log'
    require(tool.is_file(),'Bundled tools/hacpack.exe is missing. Extract the full build pack again.')
    def run(args):
        command=[str(tool),'-k',str(keys),'--titleid',TITLE,'--tempdir',str(stage/'temp'),'--backupdir',str(stage/'backup')]+list(map(str,args))
        with log.open('a',encoding='utf-8') as output:
            result=subprocess.run(command,cwd=stage,stdout=output,stderr=subprocess.STDOUT)
        require(result.returncode==0,f'Packaging failed. The local log is {log}')
    def nca(args):
        before=set((stage/'ncas').glob('*.nca'));run(['--type','nca','-o',stage/'ncas']+args)
        fresh=set((stage/'ncas').glob('*.nca'))-before
        require(len(fresh)==1,'Packager did not produce exactly one NCA');return fresh.pop()
    print('Building the standalone application...',flush=True)
    program=nca(['--ncatype','program','--exefsdir',stage/'exefs','--romfsdir',stage/'romfs'])
    ctl=nca(['--ncatype','control','--romfsdir',stage/'control'])
    nca(['--ncatype','meta','--titletype','application','--programnca',program,'--controlnca',ctl,'--titleversion',f"{release['title_version']:08x}"])
    run(['--type','nsp','--ncadir',stage/'ncas','-o',stage/'result'])
    nsp=stage/'result'/(TITLE.lower()+'.nsp')
    require(nsp.is_file(),'Packager did not produce the NSP')
    print('Checking the finished NSP...',flush=True)
    result=subprocess.run([sys.executable,str(ROOT/'builder/verify_package.py'),'--stage',str(stage),'--nsp',str(nsp),'--keys',str(keys),'--out',str(stage/'verification.json')],capture_output=True,text=True)
    with log.open('a',encoding='utf-8') as output: output.write(result.stdout+result.stderr)
    require(result.returncode==0,f'Finished NSP failed verification. See {log}')
    require(all(path.read_bytes()==data for path,data in originals.items()),'An input changed during the build')
    dest=ROOT/'Release';dest.mkdir(exist_ok=True)
    temporary=dest/'Pokemon_Emerald.nsp.tmp';shutil.copyfile(nsp,temporary);os.replace(temporary,dest/'Pokemon_Emerald.nsp')
    manifest.update(nsp_sha256=sha(nsp.read_bytes()),nsp_bytes=nsp.stat().st_size,verification='PASS')
    (dest/'build-record.json').write_text(json.dumps(manifest,indent=2))
    shutil.copyfile(stage/'verification.json',dest/'verification.json')
    print('\nDone: '+str(dest/'Pokemon_Emerald.nsp'),flush=True)

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,AssertionError) as error:
        print('\nBUILD FAILED: '+str(error),file=sys.stderr);sys.exit(1)
