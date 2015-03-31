# bswitch

bswitch analyzes and rewrites the bytecode of long `if` statements so that the function will use binary search to skip unnecessary comparisons.

Binary search for long if statements has been proposed and voted down for inclusion to the core python language (https://www.python.org/dev/peps/pep-0275/). This package sort of does that but with limitations (see below) and, probably, bugs.

## Installation

`pip install git+https://github.com/abe-winter/bswitch.git`

## Example

```python
import bswitch
@bswitch.decorate
def f(x):
  if x==1: return 'a'
  elif x==2: return 'b'
  elif x==3: return 'c'
  else: return 'd'
>>> map(f,[0,1,2])
['d', 'a', 'b']
```

Nothing too impressive, but your function is now twice as fast, assuming all the load is happening in the if statement. For longish if statements, that may be close to the truth. (see test/profile.py).

Under the hood, your function now looks more like this:

```python
def f(x):
  if x < 2:
    if x==1: return 'a'
  else:
    if x==2: return 'b'
    elif x==3: return 'c'
  return 'd'
```

## Limitations

* this can introduce undefined behavior in your program
* the function has to consist entirely of a single if / elif / else composite statement
* every if clause has to be `some_expression == constant`. the expression has to be the same every time. the constant can't be a variable, it has to be a constant. (these are limits of the analyzer and may be relaxed eventually)
* 'binary search' is an overstatement. For now, it just sorts the `if` bodies and dispatches to the middle if your expression is greater than the median.
* new, not well-tested. likely to be lots of edge cases that aren't handled well.

## Profiling results

This is from running `python -m test.profile` on my laptop 3 times. The milliseconds numbers are `average_of_3_runs ms (std dev)`.
```
value_type | normal     | rewritten | speedup
-----------|------------|-----------|--------
low        | 24 ms (3)  | 22 ms (4) | 10%
high       | 58 ms (6)  | 39 ms (7) | 33%
else       | 59 ms (8)  | 37 ms (3) | 37%
average    | 65 ms (5)  | 47 ms (2) | 27%
```
The 'low' case seems faster for the rewritten function, but it should be slightly slower. I think the cause is the ordering of the tests; there seems to be a warmup penalty for the first test case (low+normal). Changing the test order seems to erase the rewritten+low advantage. The other tests (in particular average, the one to watch) keep their advantage.

## Contributors

Ideas for improvement:

* real binary search instead of the hacked median system in place. perfect hashing where appropriate.
* support for non-constant expressions (global vars, for example)
* code cleanup: factor out the bytecode manipulators
* smarter decompilation and bytecode analysis. better intermediate representations.
* better tests! in particular, test that functions which don't meet our requirements are being rejected
* decorator flag to require an else statement or ensure that the if statement hits every value of an enum
* profiling suite showing this is (more likely, isn't) worth using
