import operator as op
import random
from functools import reduce

std_env = {
    '+': op.add, '-': op.sub, '*': op.mul, '/': op.truediv, '//': op.floordiv, '%': op.mod,
    '>': op.gt, '<': op.lt, '>=': op.ge, '<=': op.le, '==': op.eq, '<>': op.xor,
    '!=': lambda *x: op.not_(op.eq(*x)),
    '#': lambda x, y: y[x],
    'abs': abs,
    'append': lambda x, y: x.append(y) if type(x) == list else x + y,
    'apply': lambda proc, args: proc(*args),
    'do': lambda *x: x[-1],
    'is': op.is_,
    'in': op.contains,
    'len': len,
    'list': lambda *x: list(x),
    'l': lambda *x: list(x),
    'tolist': list,
    '2l': list,
    'range': range,
    'list?': lambda x: isinstance(x, list),
    'map': lambda *x: list(map(*x)),
    'imap': map,
    'sum': sum,
    'max': max,
    'min': min,
    'filter': filter,
    'reduce': reduce,
    'sort': sorted,
    'reverse': lambda x: x[::-1],
    'ireverse': reversed,
    'pass': lambda *x: None,
    'not': op.not_,
    'null?': lambda x: x == [],
    'number?': lambda x: isinstance(x, (int, float)),
    'procedure?': callable,
    'round': round,
    'symbol?': lambda x: isinstance(x, str),
    'f': lambda *x: "".join(map(str, x)),

    'chr': chr,
    'ord': ord,

    'int': int,
    'float': float,
    'zip': zip,

    'randint': random.randint,
    'choice': lambda *x: random.choices(*x).pop(),
    'ezchoice': lambda *x: random.choice(x),

}

