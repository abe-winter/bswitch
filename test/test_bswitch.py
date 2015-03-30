import pytest, opcode
from bswitch import bswitch

def test_byte_unpack():
  from bswitch.bswitch import ByteCommand
  # don't use standard_f here because it's too long
  def f(x):
    if x==1: return 'a'
    else: return 'b'
  offsets = [0,3,6,9,12,15,16,19,20,23]
  command_names = [
    'LOAD_FAST', 'LOAD_CONST', 'COMPARE_OP', 'POP_JUMP_IF_FALSE', 'LOAD_CONST', 'RETURN_VALUE',
    'LOAD_CONST', 'RETURN_VALUE', 'LOAD_CONST', 'RETURN_VALUE'
  ]
  args = [0,1,2,16,2,None,3,None,0,None]
  assert bswitch.byte_unpack(f.func_code.co_code) == [
    bswitch.ByteCommand(i, opcode.opmap[name], arg) for i,name,arg in zip(offsets,command_names,args)
  ]

def standard_f(x):
  "standard func for analysis"
  if x==2: return 'a'
  elif x==1: return 'b'
  else: return 'c'

def test_group_jumps():
  commands = bswitch.byte_unpack(standard_f.func_code.co_code)
  jumps = bswitch.group_jumps(commands)
  assert sum(len(j.head or ()) + len(j.body) for j in jumps) == len(commands)
  pjif = opcode.opmap['POP_JUMP_IF_FALSE']
  assert all(j.head[-1].code == pjif for j in jumps[:-1])
  assert jumps[-1].head is None

def test_analyze_jumps():
  commands = bswitch.byte_unpack(standard_f.func_code.co_code)
  jumps = bswitch.group_jumps(commands)
  aj = bswitch.analyze_jumps(jumps)
  assert aj.load_left == [bswitch.ByteCommand(0,124,0)]
  assert aj.constant2offset == {1: 0, 3: 16}

def test_regen():
  "can we generate a function from exact same bytecode"
  def f(x): return 'a' if x else 'b'
  f2 = bswitch.bytecode2function(f.func_code.co_code, f)
  assert f(0)=='b' and f(1)=='a'

def test_reorder():
  commands = bswitch.byte_unpack(standard_f.func_code.co_code)
  jumps = bswitch.group_jumps(commands)
  j0, j1, else_stmt = bswitch.reorder(standard_f.func_code.co_consts, jumps)
  print 'j0',j0
  print 'j1',j1
  assert j0.head[0].pos == jumps[1].head[0].pos
  assert j1.head[0].pos == jumps[0].head[0].pos
  return [j0, j1, else_stmt] # because test_reposition uses this

def test_reposition():
  # todo: this tests by running; should go lower-level
  jumps = test_reorder()
  repositioned = bswitch.reposition_commands(bswitch.dejump(jumps))
  f2 = bswitch.bytecode2function(bswitch.tobytecode(repositioned), standard_f)
  assert map(f2, (0,1,2)) == ['c','b','a']

def test_decorate():
  f2 = bswitch.decorate(standard_f)
  assert map(f2, (0,1,2)) == ['c','b','a']
  @bswitch.decorate
  def f(x):
    if x==1: return x
    elif x==2: return x
    elif x==3: return x
    elif x==4: return x
    elif x==5: return x
    elif x==6: return x
    elif x==7: return x
    elif x==8: return x
    else: return 'nomatch'
  assert map(f, range(10)) == ['nomatch',1,2,3,4,5,6,7,8,'nomatch']
