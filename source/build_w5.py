"""Narrow W3-based post-save readiness candidate. W4 is never a build input."""
import argparse,hashlib,json,pathlib,shutil,struct,sys
from build_candidate import match_object,thumb_target,ROM_SHA,ROOT
sys.path.insert(0,str(ROOT.parent/'rs-emerald-wireless-port'))
from build_port import run
from elftools.elf.elffile import ELFFile

def main():
 p=argparse.ArgumentParser()
 for n in ['base-stage','previous-stage','reference','toolchain','out']:p.add_argument('--'+n,type=pathlib.Path,required=True)
 p.add_argument('--candidate',choices=['W5','W6'],default='W6',help='W5 only reproduces the withdrawn interworking bug; W6 is ARMv4T safe')
 a=p.parse_args()
 for n in vars(a):
  if isinstance(getattr(a,n),pathlib.Path):setattr(a,n,getattr(a,n).resolve())
 assert not a.out.exists()
 vanilla=(a.base_stage/'romfs/Emerald_e.gba').read_bytes();assert hashlib.sha256(vanilla).hexdigest()==ROM_SHA
 prior=json.loads((a.previous_stage/'manifest.json').read_text())
 assert prior['wireless_bridge']['candidate']=='W3' and 'trade_save_fix' not in prior,'W3 only; refuse W4 baseline'
 functions,defs,base=match_object(a.reference,vanilla)
 with a.reference.open('rb') as f:
  e=ELFFile(f);table=e.get_section_by_name('.symtab');raw=e.get_section_by_name('.text').data()
  s=table.get_symbol_by_name('sTradeAnim')[0];values=[]
  for r in e.get_section_by_name('.rel.text').iter_relocations():
   symbol=table.get_symbol(r['r_info_sym']);off=r['r_offset']
   if r['r_info_type']==2 and symbol['st_shndx']==s['st_shndx']:
    values.append(struct.unpack_from('<I',vanilla,base+off)[0]-struct.unpack_from('<I',raw,off)[0]+s['st_value']-symbol['st_value'])
  assert values and len(set(values))==1;defs['sTradeAnim']=values[0]
 # Derive timer displacement from original instructions adjacent to its reset
 # after LinkFullSave_Init, independently in both callbacks. No guessed offsets.
 from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
 cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);routes=[];offsets=[]
 for name in ['CB2_SaveAndEndTrade','CB2_SaveAndEndWirelessTrade']:
  pc,size=functions[name];start=pc-0x8000000
  ins=list(cs.disasm(vanilla[start:start+size],pc))
  # Data in jump tables can interrupt linear decoding; scan every halfword for BL.
  calls=[]
  for off in range(start,start+size-3,2):
   try:target=thumb_target(vanilla,off,off+0x8000000)
   except AssertionError:continue
   calls.append((off+0x8000000,target))
  commits=[at for at,t in calls if t==defs['LinkFullSave_SetLastSectorSignature']&~1];assert len(commits)==1
  waits=[at for at,t in calls if t==defs['_IsLinkTaskFinished']&~1 and at<commits[0]]
  assert waits and commits[0]-waits[-1]<160
  init=[at for at,t in calls if t==defs['LinkFullSave_Init']&~1];assert len(init)==1
  instructions=[next(cs.disasm(vanilla[at-0x8000000:at-0x8000000+2],at),None) for at in range(pc,pc+size,2)]
  stores=[i for i in instructions if i and i.mnemonic=='str' and '#0x64]' in i.op_str]
  loads=[i for i in instructions if i and i.mnemonic=='ldr' and '#0x64]' in i.op_str]
  assert stores and loads,('timer load/store displacement not verified',name)
  offsets.append(100)
  routes.append({'function':name,'site':waits[-1],'original_target':defs['_IsLinkTaskFinished'],'commit_site':commits[0]})
 assert len(set(offsets))==1
 a.out.mkdir();b=a.out/'reconnect-build';b.mkdir()
 script='SECTIONS { . = 0x08f01000; .text : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.ARM.attributes) *(.ARM.exidx*) *(.comment) } }\n'
 calls=['_IsLinkTaskFinished','GetMultiplayerId','SetLinkStandbyCallback']
 script+='\n'.join(f'{k} = 0x{v:x};' for k,v in defs.items() if a.candidate=='W5' or k not in calls)
 (b/'link.ld').write_text(script)
 assembly='.section .rodata\n.global W5_TimerOffset\nW5_TimerOffset: .word '+str(offsets[0])+'\n'
 if a.candidate=='W6':
  # Absolute script symbols lose their Thumb function type. GNU ld otherwise
  # emits BX-PC / ARM LDR-PC veneers that only interwork on ARMv5, not GBA ARMv4T.
  # Local, typed Thumb tail stubs use BX explicitly and preserve the caller LR.
  assembly+='\n.syntax unified\n.cpu arm7tdmi\n.thumb\n.text\n'
  for name in calls:
   assembly+=f'.align 2\n.global {name}\n.type {name},%function\n.thumb_func\n{name}:\n ldr r3,1f\n bx r3\n.align 2\n1: .word 0x{defs[name]|1:x}\n'
 (b/'offset.s').write_text(assembly)
 run([a.toolchain/'arm-none-eabi-gcc.exe','-S','-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-mabi=apcs-gnu','-Os','-ffreestanding','-fno-builtin','-o',b/'shim.s',ROOT/'reconnect_w5.c'])
 for name in ['shim','offset']:run([a.toolchain/'arm-none-eabi-as.exe','-mcpu=arm7tdmi','-o',b/(name+'.o'),b/(name+'.s')])
 run([a.toolchain/'arm-none-eabi-ld.exe','-T',b/'link.ld','-o',b/'shim.elf',b/'shim.o',b/'offset.o'])
 run([a.toolchain/'arm-none-eabi-objcopy.exe','-O','binary',b/'shim.elf',b/'shim.bin'])
 with (b/'shim.elf').open('rb') as f:
  table=ELFFile(f).get_section_by_name('.symtab');syms={s.name:s['st_value'] for s in table.iter_symbols()}
  if a.candidate=='W6':assert not any(s.name=='$a' or s.name.startswith('$a.') for s in table.iter_symbols()),'Unexpected ARM code in Thumb-only shim'
 for folder in ['exefs','romfs','control']:shutil.copytree(a.previous_stage/folder,a.out/folder)
 rom=bytearray((a.out/'romfs/Emerald_e.gba').read_bytes());payload=(b/'shim.bin').read_bytes()
 assert rom[0xf01000:0xf01000+len(payload)]==b'\xff'*len(payload)
 rom[0xf01000:0xf01000+len(payload)]=payload
 assert rom[0xd4:0xdc]==bytes(8)
 rom[0xd4:0xdc]=struct.pack('<HHI',0x4b00,0x4718,syms['W5_PostWriteReady']|1)
 for r in routes:
  off=r['site']-0x8000000;assert rom[off:off+4]==vanilla[off:off+4]
  delta=0x080000d4-(r['site']+4);assert -(1<<22)<=delta<(1<<22) and not delta&1
  code=struct.pack('<HH',0xf000|((delta>>12)&2047),0xf800|((delta>>1)&2047))
  r['original']=rom[off:off+4].hex();r['replacement']=code.hex();rom[off:off+4]=code
  assert thumb_target(rom,off,r['site'])==0x080000d4
 (a.out/'romfs/Emerald_e.gba').write_bytes(rom)
 prior['title_version']=10 if a.candidate=='W5' else 11;prior['rom_sha256']=hashlib.sha256(rom).hexdigest()
 prior['reconnect_candidate']={'candidate':a.candidate,'baseline':'W3','routes':routes,'payload_bytes':len(payload),'timer_offset':offsets[0],'status':'development; tests pending','native_save_and_exefs':'unchanged','host_direction_fix':False,'call_stubs':'explicit Thumb LDR/BX; ARMv4T safe' if a.candidate=='W6' else 'WITHDRAWN: ARMv5-only linker veneers'}
 prior.pop('nsp_bytes',None);prior.pop('nsp_sha256',None)
 (a.out/'manifest.json').write_text(json.dumps(prior,indent=2))
 (b/'reference.json').write_text(json.dumps({'functions':functions,'definitions':defs},indent=2))
 print(a.candidate,'from W3:',len(payload),'payload bytes; two four-byte readiness-call hooks; save callbacks stay in place')
if __name__=='__main__':main()
