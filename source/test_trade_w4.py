"""Execute actual original/patched trade callbacks with modeled RFU barriers.

Rendering, flash-sector I/O and radio delivery are explicit mocks. This checks
the save-handshake sequence and ABI, not actual Switch radio interoperability.
"""
import argparse,json,pathlib,struct,sys
import build_candidate
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser();p.add_argument('--stage',type=pathlib.Path,required=True)
p.add_argument('--base-stage',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
p.add_argument('--reference',type=pathlib.Path)
a=p.parse_args();ref=json.loads((a.reference or a.stage/'trade-build/reference.json').read_text());defs=ref['definitions'];functions=ref['functions']
original=(a.base_stage/'romfs/Emerald_e.gba').read_bytes();patched=(a.stage/'romfs/Emerald_e.gba').read_bytes()
STOP=0x0203f000;ANIM=0x02030000
class Peer:
 def __init__(self,image,name,version,mpid):
  self.u=u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.ctl_set_cpu_model(UC_CPU_ARM_TI925T)
  u.mem_map(0x08000000,0x1000000);u.mem_write(0x08000000,image)
  for at,n in [(0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)]:u.mem_map(at,n)
  u.mem_write(defs['sTradeAnim'],struct.pack('<I',ANIM));u.mem_write(defs['gWirelessCommType'],b'\1')
  u.mem_write(defs['gLinkPlayers']+28*(mpid^1),struct.pack('<H',version))
  # Trade Center callback returns here, rather than closing the Union Room link.
  u.mem_write(defs['gMain']+8,struct.pack('<I',defs['CB2_StartCreateTradeMenu']))
  self.name=name;self.mpid=mpid;self.round=0;self.remote_round=0;self.done=False;self.calls=[];self.signatures=0;self.sectors=0
  external={v&~1:k for k,v in defs.items() if v&1 and k not in [name]}
  def code(uc,pc,size,_):
   fn=external.get(pc)
   if not fn:return
   assert uc.reg_read(UC_ARM_REG_CPSR)&32,('Thumb engine function reached in ARM state',fn,hex(pc))
   self.calls.append(fn);ret=0
   if fn in ['SetTradeLinkStandbyCallback','SetLinkStandbyCallback']:self.round+=1
   elif fn in ['_IsLinkTaskFinished','IsLinkTaskFinished']:ret=int(self.remote_round>=self.round)
   elif fn=='GetMultiplayerId':ret=self.mpid
   elif fn=='LinkFullSave_WriteSector':self.sectors+=1;ret=int(self.sectors>=14)
   elif fn=='LinkFullSave_SetLastSectorSignature':self.signatures+=1
   elif fn=='IsBGMStopped':ret=1
   elif fn=='SetMainCallback2':self.done=True
   # Fail closed if a new link/save boundary appears unmodeled.
   elif fn in ['SetCloseLinkCallback']:raise AssertionError('Unexpected close instead of return to Trade Center')
   uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
 def frame(self):
  if self.done:return
  u=self.u;u.reg_write(UC_ARM_REG_SP,0x03007000);u.reg_write(UC_ARM_REG_LR,STOP|1)
  for i in range(4,12):u.reg_write(UC_ARM_REG_R0+i,0x51510000+i)
  u.emu_start(functions[self.name][0]|1,STOP,count=20000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
  assert u.reg_read(UC_ARM_REG_SP)==0x03007000
  for i in range(4,12):assert u.reg_read(UC_ARM_REG_R0+i)==0x51510000+i

results=[]
for name in ['CB2_SaveAndEndTrade','CB2_SaveAndEndWirelessTrade']:
 for version in [3,4,5,0x104,0x105]:
  for mpid in [0,1]:
   q=Peer(patched,name,version,mpid)
   # FRLG Switch has five readiness rounds; original Emerald has four.
   expected=5 if version&255 in [4,5] else 4
   for frame in range(1200):
    q.remote_round=min(q.round,expected) if frame%9==0 else q.remote_round
    q.frame()
    if q.done:break
   assert q.done and q.round==expected and q.signatures==1 and q.sectors==14,(name,version,mpid,q.round,q.calls[-12:])
   assert q.calls.index('LinkFullSave_WriteSector')<q.calls.index('LinkFullSave_SetLastSectorSignature')
   results.append({'callback':name,'peer_version':version,'multiplayer_id':mpid,'barriers':q.round,'frames':frame+1,'signature_commits':q.signatures})
 # Establish the regression: original Emerald has one fewer barrier than Switch FRLG.
 q=Peer(original,name,4,0)
 for frame in range(1200):
  q.remote_round=q.round;q.frame()
  if q.done:break
 assert q.done and q.round==4
 # Execute both patched Emerald players together with delayed readiness.
 peers=[Peer(patched,name,3,i) for i in [0,1]]
 for frame in range(1200):
  if frame%7==0:
   peers[0].remote_round=peers[1].round;peers[1].remote_round=peers[0].round
  for q in peers:q.frame()
  if all(q.done for q in peers):break
 assert all(q.done and q.round==4 and q.signatures==1 for q in peers)
report={'result':'PASS','cases':results,'regression':'Original callbacks perform four readiness barriers; Switch FRLG source requires five. Patched callbacks perform five only for wireless FR/LG peers.','emerald_pair':'Both real patched callbacks complete with four barriers and delayed modeled delivery.','limits':'Radio, rendering and flash I/O mocked. Actual Switch cross-game completion still requires hardware testing.'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2));print('PASS 20 actual callback paths, both Emerald pair paths, original four-barrier regression, ABI and save ordering')
