"""Compile and byte-match unmodified Emerald trade code; no patched ROM output."""
import argparse,hashlib,pathlib,sys
from build_candidate import match_object,ROM_SHA,ROOT
sys.path.insert(0,str(ROOT.parent/'rs-emerald-wireless-port'))
from build_port import run,maps_header
from assets import expand
p=argparse.ArgumentParser()
for n in ['emerald','agbcc','toolchain','preproc','rom','out']:p.add_argument('--'+n,type=pathlib.Path,required=True)
a=p.parse_args()
for n in vars(a):setattr(a,n,getattr(a,n).resolve())
rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
a.out.mkdir(parents=True,exist_ok=True);inc=a.out/'include';inc.mkdir(exist_ok=True);maps_header(a.emerald,inc)
cpp=run([a.toolchain/'arm-none-eabi-gcc.exe','-E','-iquote',a.emerald/'include','-iquote',a.emerald/'src','-I',inc,
 '-DMODERN=0','-I',a.agbcc/'libc/include','-I',a.agbcc/'ginclude','-nostdinc','-undef','-std=gnu89',a.emerald/'src/trade.c'],cwd=a.emerald)
ip=a.out/'trade.i';ip.write_bytes(expand(cpp.decode().replace('\r\n','\n'),a.emerald,[]).encode())
ready=a.out/'trade.pre.i';ready.write_bytes(run([a.preproc,ip,a.emerald/'charmap.txt']))
run([a.agbcc/'agbcc.exe','-g','-mthumb-interwork','-O2','-fhex-asm','-o',a.out/'trade.s',ready])
run([a.toolchain/'arm-none-eabi-as.exe','-mcpu=arm7tdmi','-o',a.out/'trade.o',a.out/'trade.s'])
functions,definitions,base=match_object(a.out/'trade.o',rom)
print('MATCH original trade reference:',len(functions),'functions; ROM base',hex(base+0x8000000))
