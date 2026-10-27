"""W3/W5 callback + actual RFU readiness execution, simulated packet delivery.

Executes the original ROM trade callbacks, W5 hook, original cleanup callback,
and original re-entry callback. Rendering/free/flash I/O are mocked explicitly.
RFU state is retained for another party-block exchange and a second trade.
No claim of Switch radio or complete menu rendering is made.
"""
import argparse,json,pathlib,struct,sys
import build_candidate
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'rs-emerald-wireless-port'))
from test_core import Peer as RfuPeer
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
p=argparse.ArgumentParser()
for n in ['stage','rfu-image','out']:p.add_argument('--'+n,type=pathlib.Path,required=True)
a=p.parse_args();ref=json.loads((a.stage/'reconnect-build/reference.json').read_text());defs=ref['definitions'];funcs=ref['functions']
image=(a.stage/'romfs/Emerald_e.gba').read_bytes();STOP=0x0203f000;ANIM=0x02030000
class TradePeer:
 def __init__(self,mpid,version,name):
  self.rfu=RfuPeer(a.rfu_image,mpid);self.id=mpid;self.version=version;self.name=name
  u=self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.ctl_set_cpu_model(UC_CPU_ARM_TI925T)
  u.mem_map(0x08000000,0x1000000);u.mem_write(0x08000000,image)
  for addr,size in [(0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)]:u.mem_map(addr,size)
  excluded=[name,'CB2_FreeTradeAnim','CB2_StartCreateTradeMenu']
  external={v&~1:k for k,v in defs.items() if v&1 and k not in excluded}
  self.done=False;self.sectors=0;self.signatures=0;self.transitions=[];self.calls=[];self.start()
  def code(uc,pc,size,_):
   fn=external.get(pc)
   if not fn:return
   assert uc.reg_read(UC_ARM_REG_CPSR)&32,('Thumb engine function reached in ARM state',fn,hex(pc))
   self.calls.append(fn);ret=0
   if fn in ['SetLinkStandbyCallback','SetTradeLinkStandbyCallback']:self.rfu.call('PortLink_SetStandbyCallback')
   elif fn in ['_IsLinkTaskFinished','IsLinkTaskFinished','IsLinkRfuTaskFinished']:ret=self.rfu.call('IsLinkRfuTaskFinished')
   elif fn=='GetMultiplayerId':ret=self.id
   elif fn=='LinkFullSave_WriteSector':self.sectors+=1;ret=int(self.sectors>=14)
   elif fn=='LinkFullSave_SetLastSectorSignature':
    assert self.sectors==14 and self.rfu.call('IsLinkRfuTaskFinished');self.signatures+=1
   elif fn=='IsBGMStopped':ret=1
   elif fn=='SetMainCallback2':
    target=uc.reg_read(UC_ARM_REG_R0)&~1
    self.transitions.append(target);self.entry=target;uc.mem_write(defs['gMain']+0x438,b'\0')
    if target==funcs['CB2_CreateTradeMenu'][0]:self.done=True
   elif fn=='SetCloseLinkCallback':raise AssertionError('Unexpected disconnect')
   uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
 def start(self):
  self.u.mem_write(defs['sTradeAnim'],struct.pack('<I',ANIM));self.u.mem_write(ANIM,bytes(0x1000))
  self.u.mem_write(defs['gWirelessCommType'],b'\1')
  self.u.mem_write(defs['gLinkPlayers']+28*(self.id^1),struct.pack('<H',self.version))
  self.u.mem_write(defs['gMain']+8,struct.pack('<I',defs['CB2_StartCreateTradeMenu']))
  self.u.mem_write(defs['gMain']+0x438,b'\0');self.entry=funcs[self.name][0]
  self.done=False;self.sectors=0
 def frame(self):
  if self.done:return
  u=self.u;u.reg_write(UC_ARM_REG_SP,0x03007000);u.reg_write(UC_ARM_REG_LR,STOP|1)
  for i in range(4,12):u.reg_write(UC_ARM_REG_R0+i,0x55550000+i)
  u.emu_start(self.entry|1,STOP,count=30000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP and u.reg_read(UC_ARM_REG_SP)==0x03007000
  for i in range(4,12):assert u.reg_read(UC_ARM_REG_R0+i)==0x55550000+i

results=[]
for name in ['CB2_SaveAndEndTrade','CB2_SaveAndEndWirelessTrade']:
 for version in [3,4,5]:
  peers=[TradePeer(i,version,name) for i in [0,1]]
  def tick(frame):
   # Delayed packet delivery exercises actual counter and retransmission state.
   if frame%3:return
   matrix=b''.join(q.rfu.wire() for q in peers)+bytes(48)
   for q in peers:q.rfu.write('gRecvCmds',matrix);q.rfu.call('PortTest_Receive')
   for q in peers:q.rfu.call('PortTest_Produce')
  for trial in range(2):
   if trial:
    for q in peers:q.start()
   for frame in range(1500):
    for q in peers:q.frame()
    tick(frame)
    if all(q.done for q in peers):break
   else:raise AssertionError(('standby/reentry timeout',name,version,trial,[q.calls[-10:] for q in peers]))
   expected=(4 if version==3 else 5)*(trial+1)
   for q in peers:
    assert q.rfu.call('PortTest_StandbyRound')==expected
    assert q.transitions[-3:]==[funcs['CB2_FreeTradeAnim'][0],funcs['CB2_StartCreateTradeMenu'][0],funcs['CB2_CreateTradeMenu'][0]]
    assert q.signatures==trial+1
   # Execute a new original RFU party-pair block exchange after re-entry,
   # without clearing/resetting the session or its standby sequence counter.
   payload=[bytes((j+q.id*63+trial)&255 for j in range(200)) for q in peers]
   for q in peers:q.rfu.call('PortLink_ResetReceivedFlags');q.rfu.write('gBlockSendBuffer',payload[q.id]+bytes(56))
   peers[0].rfu.call('PortLink_RequestBlock',1)
   for bf in range(600):
    tick(bf)
    if all(q.rfu.call('Rfu_GetBlockReceivedStatus')==3 and q.rfu.call('IsLinkRfuTaskFinished') for q in peers):break
   else:raise AssertionError('post-return party exchange timed out')
   for q in peers:
    for pid in [0,1]:assert bytes(q.rfu.u.mem_read(q.rfu.syms['gBlockRecvBuffer']+pid*256,200))==payload[pid]
   results.append({'callback':name,'peer_version':version,'trade':trial+1,'retained_round':expected,'callback_frames':frame+1,'post_return_block_frames':bf+1})
report={'result':'PASS','cases':results,'tested':'Actual W3 ROM callbacks + W5 hook + actual RFU sequence counters, actual ROM cleanup/reentry callbacks, repeated party exchange and second callback cycle without RFU reset.','limits':['Both RFU peers execute Emerald protocol code; FRLG peer callback behavior is not a full independent official-ROM execution.','Packet delivery, flash writes, graphics/free boundaries modeled.','Stops at trade menu reconstruction entry; full rendering/menu reconstruction not executed.','Switch radio/emulator runtime requires hardware testing.']}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2));print('PASS 12 callback/reentry/retained-RFU cycles and subsequent party-block exchanges')
