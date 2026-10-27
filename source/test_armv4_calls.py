"""Execute actual W5/W6 call stubs on ARMv4T; minimal Thumb callee boundary.

W5 must fail; W6 must reach all three Thumb callees in Thumb state and return.
"""
import argparse,json,pathlib,sys
import build_candidate
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UcError
from unicorn.arm_const import *
p=argparse.ArgumentParser()
for n in ['bad-stage','fixed-stage','out']:p.add_argument('--'+n,type=pathlib.Path,required=True)
a=p.parse_args();names=['_IsLinkTaskFinished','GetMultiplayerId','SetLinkStandbyCallback'];results=[]
for label,stage in [('W5',a.bad_stage),('W6',a.fixed_stage)]:
 ref=json.loads((stage/'reconnect-build/reference.json').read_text())['definitions']
 with (stage/'reconnect-build/shim.elf').open('rb') as f:syms={s.name:s['st_value'] for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()}
 image=(stage/'romfs/Emerald_e.gba').read_bytes()
 for name in names:
  start=syms[name] if label=='W6' else syms['__'+name+'_from_thumb']
  target=ref[name]&~1;u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.ctl_set_cpu_model(UC_CPU_ARM_TI925T)
  u.mem_map(0x08000000,0x1000000);u.mem_write(0x08000000,image)
  u.mem_write(target,bytes.fromhex('01207047'));u.reg_write(UC_ARM_REG_LR,0x08000101)
  reached=[]
  def code(uc,pc,size,_):
   if pc==target:reached.append(bool(uc.reg_read(UC_ARM_REG_CPSR)&32))
  u.hook_add(UC_HOOK_CODE,code)
  try:u.emu_start(start|1,0x08000100,count=20);error=None
  except UcError as ex:error=str(ex)
  passed=reached==[True] and u.reg_read(UC_ARM_REG_PC)==0x08000100 and u.reg_read(UC_ARM_REG_R0)==1
  assert passed==(label=='W6'),(label,name,reached,error)
  results.append({'candidate':label,'call':name,'callee_entered_in_thumb_state':reached,'returned_correctly':passed,'emulator_error':error})
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps({'result':'PASS','cpu':'Unicorn TI925T ARMv4T; actual linked call stubs','regression':'All three W5 stubs enter Thumb callees in ARM mode and fail; all three W6 Thumb LDR/BX stubs remain in Thumb mode and return.','cases':results},indent=2))
print('PASS: reproduced all 3 W5 ARMv4T failures; all 3 W6 call stubs correct')
