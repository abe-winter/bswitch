"timing tests on short and long switch functions"

import bswitch, time

VALS = [1,3,2,10,12,16,42,100,8,7,9,60,61,62,63,66,1000]

def flong(x):
  if x == 1: return x
  elif x == 3: return x
  elif x ==2: return x
  elif x == 10: return x
  elif x == 12: return x
  elif x == 16: return x
  elif x == 42: return x
  elif x == 100: return x
  elif x == 8: return x
  elif x == 7: return x
  elif x == 9: return x
  elif x == 60: return x
  elif x == 61: return x
  elif x == 62: return x
  elif x == 63: return x
  elif x == 66: return x
  else: return x

flong_switched = bswitch.decorate(flong)

def main():
  for status, f in zip(('normal', 'fast'), (flong, flong_switched)):
    for valname, val in zip(('lo','hi','else'),(2,66,1000)):
      t0 = time.clock()
      for i in range(100000): f(val)
      print status, valname, '%.3fs' % (time.clock() - t0)
    t0 = time.clock()
    for i in range(10000):
      for v in VALS: f(v)
    print status, 'average', '%.3fs' % (time.clock() - t0)

if __name__ == '__main__': main()
