"""bswitch.py -- binary-tree switch statement
For functions that are composed of long if statements testing a value, this rewrites their bytecode.
"""
# todo: check platform.python_implementation() somewhere
# this PEP talks about if-stmt analysis for switch emulation: https://www.python.org/dev/peps/pep-0275/

import collections, opcode, struct, dis, copy

class BadJumpTable(StandardError): "the input bytecode isn't right for switch conversion"
class HugeRelativeJump(StandardError): "relative jumps outside of Jump.body"

ARG = struct.Struct('<H') # for packing and unpacking arguments

ByteCommand = collections.namedtuple('ByteCommand','pos code arg')
def byte_unpack(code_string):
  "for function f, feed this f.func_code.co_code. returns list of ByteCommand tuples."
  i = 0
  commands = []
  while i < len(code_string):
    command = ord(code_string[i])
    if command >= opcode.HAVE_ARGUMENT:
      if i+3 > len(code_string): raise ValueError('no room for argument at %i/%i' % (i, len(code_string)))
      commands.append(ByteCommand(i, command, ARG.unpack(code_string[i+1:i+3])[0]))
      i += 3
    else:
      commands.append(ByteCommand(i, command, None))
      i += 1
  return commands

Jump = collections.namedtuple('Jump','head body')
def group_jumps(commands):
  """takes list of ByteCommand.
  return list of Jump, where:
   -- Jump.head is a list of commands from the jump target to (including) the next jump
   -- Jump.body is commands from after jump (i.e. the True case) to next jump target
  The first Jump returned will start at the beginning of the function (i.e. it's not a jump target).
  The last Jump will have a head=None because it's the else case.
  Die if there are no jumps.
  """
  def offset2index(offset, index0):
    "return commands index of command with given bytecode offset"
    return next(i for i,command in enumerate(commands[index0:], index0) if command.pos==offset)
  def next_jump(index0):
    "return index of next PJIF command at or after index0. careful: commands array index, not bytecode offset. None if none."
    pjif = opcode.opmap['POP_JUMP_IF_FALSE']
    return next((i for i,command in enumerate(commands[index0:],index0) if command.code==pjif), None)
  jumps = []
  jump_target = 0
  while 1:
    jump_index = next_jump(jump_target)
    if jump_index is None:
      jumps.append(Jump(None, commands[jump_target:]))
      return jumps
    else:
      next_target = offset2index(commands[jump_index].arg, jump_index)
      jumps.append(Jump(commands[jump_target:jump_index+1], commands[jump_index+1:next_target]))
      jump_target = next_target

# JumpCmp.load_left is a list of the standard preamble for all the jumps
# JumpCmp.constant2offset is a dict of {LOAD_CONST.arg:bytecode_offset}
JumpCmp = collections.namedtuple('JumpCmp','load_left constant2offset')
def analyze_jumps(jumps):
  """takes the list of Jump tuples from group_jumps. returns JumpCmp.
  fails if input is weird (tell me more).
  """
  # todo: more of a decompile, AST approach here? look at uncompyle.
  if jumps[-1].head is not None: raise BadJumpTable("last jump not an else")
  if len(jumps) < 3: raise BadJumpTable("too few, what's the point")
  head0 = jumps[0].head
  if head0[-2].code != opcode.opmap['COMPARE_OP'] or head0[-2].arg != 2: raise BadJumpTable('cmp not ==',0)
  if head0[-3].code != opcode.opmap['LOAD_CONST']: raise BadJumpTable('cmp right not LOAD_CONST',0)
  def compare_head(headi, i):
    if len(head0) != len(headi): raise BadJumpTable('length mismatch',i)
    if headi[-2].code != opcode.opmap['COMPARE_OP'] or headi[-2].arg != 2: raise BadJumpTable('cmp not ==',i)
    # todo below: it would be great if this didn't have to be a constant
    if headi[-3].code != opcode.opmap['LOAD_CONST']: raise BadJumpTable('cmp right not LOAD_CONST',i)
    if any(h0[1:]!=hi[1:] for h0,hi in zip(head0[:-3],headi[:-3])): raise BadJumpTable('preamble mismatch',i)
  for i in range(1,len(jumps)-1): compare_head(jumps[i].head,i)
  load_left = head0[:-3] # sans the const, sans the compare, sans the jump
  const2offset = {j.head[-3].arg:j.head[-1].arg for j in jumps[:-1]}
  return JumpCmp(load_left, const2offset)

def reorder(consts, jumps):
  "sort the commands and rewrite them. this assumes that jumps[-1] is an else clause or tail and keeps it at the end."
  # 1. make sure relative jumps don't cross body boundaries
  for i,jump in enumerate(jumps):
    for j,command in enumerate(jump.body):
      if command.code in dis.hasjrel:
        if opcode.opname[command.code] in ('FOR_ITER','JUMP_FORWARD'):
          abs_offset = command.pos + command.arg
          if abs_offset > jump.body[-1].pos: raise HugeRelativeJump('jump past end of body',command,i,j)
        elif opcode.opname[command.code] in ('SETUP_LOOP','SETUP_EXCEPT','SETUP_FINALLY','SETUP_WITH'):
          pass # I'm not writing these yet; assuming the compiler doesn't use them in weird ways
        else: raise NotImplementedError('unk relative jump code', command.code, opcode.opname[command.code])
  sorted_jumps = sorted(jumps[:-1], key=lambda j:consts[j.head[-3].arg]) + [jumps[-1]] # jumps[-1].head is None, remember
  for i,j in enumerate(sorted_jumps[:-1]):
    j = copy.deepcopy(j) # so we don't mutate the input
    j.head[-1] = j.head[-1]._replace(arg=(sorted_jumps[i+1].head or sorted_jumps[i+1].body)[0].pos)
    sorted_jumps[i] = j
  return sorted_jumps

def global_preamble(consts, jumps, jumpcmp):
  "create a global preamble that does binary search. for now, this just splits on the median; get fancier"
  sorted_consts = sorted(map(consts.__getitem__,jumpcmp.constant2offset))
  median = sorted_consts[len(sorted_consts)/2]
  return jumps[0].head[:-3] + [
    jumps[0].head[-3]._replace(arg=consts.index(median)), # todo: support globals too (2 instructions instead of 1)
    ByteCommand(-1, opcode.opmap['COMPARE_OP'], dis.cmp_op.index('>=')),
    ByteCommand(-1, opcode.opmap['POP_JUMP_IF_TRUE'], jumpcmp.constant2offset[consts.index(median)]),
  ]

def reposition_commands(commands):
  """take commands that have been reordered and compute their true offsets.
  return list of ByteCommand (with positions and abs jump args corrected).
  """
  cumulative = 0
  ret = []
  offsets = {}
  for c in commands:
    ret.append(ByteCommand(cumulative, *c[1:]))
    offsets[c.pos] = cumulative
    cumulative += 1 if c.arg is None else 3
  for i,c in enumerate(ret):
    if c.code in dis.hasjabs:
      ret[i] = c._replace(arg=offsets[c.arg])
  return ret

def dejump(jumps):
  "convert list of Jump to list of ByteCommand"
  return sum((((j.head or []) + j.body) for j in jumps),[])

def tobytecode(commands):
  "return bytecode for ByteCommand tups"
  return ''.join(chr(c.code) if c.arg is None else chr(c.code) + ARG.pack(c.arg) for c in commands)

def bytecode2function(bytecode, old_function):
  argnames = [
    'co_argcount',
    'co_nlocals',
    'co_stacksize',
    'co_flags',
    'co_code',
    'co_consts',
    'co_names',
    'co_varnames',
    'co_filename',
    'co_name',
    'co_firstlineno',
    'co_lnotab',
    'co_freevars',
    'co_cellvars',
  ]
  argvals = [getattr(old_function.func_code,name) for name in argnames]
  argvals[argnames.index('co_code')] = bytecode
  code = type(old_function.func_code)(*argvals)
  return type(old_function)(
    code,
    old_function.func_globals,
    old_function.func_name,
    old_function.func_defaults,
    old_function.func_closure
  )

def decorate(f):
  "optimize an if-else function with binary search"
  commands = byte_unpack(f.func_code.co_code)
  jumps = group_jumps(commands)
  ordered = reorder(f.func_code.co_consts, jumps)
  pre = global_preamble(f.func_code.co_consts, ordered, analyze_jumps(jumps))
  reposd = reposition_commands(pre + dejump(ordered))
  f2 = bytecode2function(tobytecode(reposd), f)
  f2.__bswitch__ = True # leave a mark on this
  return f2
