# bswitch

bswitch analyzes and rewrites the bytecode of long `if` statements so that the function will use binary search to 

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
['c', 'a', 'b']
```

Nothing too impressive, but under the hood your function could be up to twice as fast, assuming all the load is happening in the if statement. For longish if statements, that may be close to the truth.

Under the hood, your function now looks more like this:

```python
def f(x):
  if x < 2:
    if x==1: return 'a'
    elif x==2: return 'b'
  else:
    if x==3: return 'c'
  return 'd'
```

## Limitations

* this can introduce undefined behavior in your program
* the function has to consist entirely of a single if / elif / else composite statement
* every if clause has to be (some expression) == constant. the expression has to be the same every time. the constant can't be a variable, it has to be a constant. (these are limits of the analyzer and may be relaxed eventually)
* 'binary search' is an overstatement. For now, it just sorts the `if` bodies and dispatches to the middle if your expression is greater than the median.
* new, not well-tested. likely to be lots of edge cases that aren't handled well.
