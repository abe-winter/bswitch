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

Nothing too impressive, but under the hood your function could be up to twice as fast, assuming all the load is happening in the if statement. For longish if statements, that may be close to the truth. (It may not be; I don't have any profiling results suggesting this is a good idea).

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
* every if clause has to be (some expression) == constant. the expression has to be the same every time. the constant can't be a variable, it has to be a constant. (these are limits of the analyzer and may be relaxed eventually)
* 'binary search' is an overstatement. For now, it just sorts the `if` bodies and dispatches to the middle if your expression is greater than the median. also, the binary search logic doesn't know how to short-circuit so high values will be optimized but low values will still have to go through all the tests.
* new, not well-tested. likely to be lots of edge cases that aren't handled well.

## Contributors

Obvious places for improvement:

* real binary search instead of the hacked median system in place
* support for non-constant expressions (global vars, for example)
* code cleanup: factor out the bytecode manipulators
* smarter decompilation and bytecode analysis
* better tests!
