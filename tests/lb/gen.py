#!/usr/bin/env python3
from itertools import product

shape = """C lb-{l0n}-{s0n}-{l1n}-{s1n}{ub}
{{ [x] = 0; [y] = 0; }}

P0 (int* x, int* y) {{
  int a = {l0};
  {s0};
}}

P1 (int* x, int* y) {{
  int b = {l1};
  if (b != 0) {{
    {s1};
  }}
}}

{cond}"""

l0s = {
    'lna': '*y',
    'lrlx': 'atomic_load_explicit(y, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(y, 0, memory_order_relaxed)',
}
s0s = {
    # Undefined
    'sna': '*x = 1',

    # Unsynchronized
    'srlx': 'atomic_store_explicit(x, 1, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',

    # Release Patterns
    'srel': 'atomic_store_explicit(x, 1, memory_order_release)',
    'faddrel': 'atomic_fetch_add_explicit(x, 1, memory_order_release)',
    'frel-srlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(x, 1, memory_order_relaxed)',
    'frel-faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',
    'frel-2srlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(x, 1, memory_order_relaxed);\n  atomic_store_explicit(x, 2, memory_order_relaxed)',
    'frel-srlx-faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(x, 1, memory_order_relaxed);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',
    'frel-faddrlx-faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',

    # Release sequences
    'srel-srlx': 'atomic_store_explicit(x, 1, memory_order_release);\n  atomic_store_explicit(x, 2, memory_order_relaxed)',
    'srel-faddrlx': 'atomic_store_explicit(x, 1, memory_order_release);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',
    'faddrel-faddrlx': 'atomic_fetch_add_explicit(x, 1, memory_order_release);\n  atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',
    'faddrel-srlx': 'atomic_fetch_add_explicit(x, 1, memory_order_release);\n  atomic_store_explicit(x, 2, memory_order_relaxed)',
}

l1s = {
    # Undefined
    'lna': '*x',

    # Unsynchronized
    'lrlx': 'atomic_load_explicit(x, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(x, 0, memory_order_relaxed)',

    # Acquire Patterns
    'lacq': 'atomic_load_explicit(x, memory_order_acquire)',
    'faddacq': 'atomic_fetch_add_explicit(x, 0, memory_order_acquire)',
    'lrlx-facq': 'atomic_load_explicit(x, memory_order_relaxed);\n  atomic_thread_fence(memory_order_acquire)',
    'faddrlx-facq': 'atomic_fetch_add_explicit(x, 0, memory_order_relaxed);\n  atomic_thread_fence(memory_order_acquire)',    
    'lrlx-lacq': 'atomic_load_explicit(x, memory_order_relaxed);\n  int c = atomic_load_explicit(x, memory_order_acquire)',
}

s1s = {
    'sna': '*y = 1',
    'srlx': 'atomic_store_explicit(y, 1, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',
}

for l0, s0, l1, s1 in product(l0s, s0s, l1s, s1s):
    ub = ''
    cond = '~exists(0:a=1)'
    racy_cond = 'forall(0:a=0 \/ 0:a=1)'
    if l1 in ['lna', 'lrlx', 'faddrlx'] or s0 in ['sna', 'srlx', 'faddrlx', 'faddrel-srlx', 'srel-srlx']:
        ub = '.undef'
    if 'lna' not in [l0, l1] and 'sna' not in [s0, s1] and ub == '.undef':
        ub = '.racy'
        cond = racy_cond
    # Generate a C++11 version with release sequences:
    if ub == '.undef' and s0 in ['srel-srlx']:
        cond2 = cond
        ub2 = ''
        if l1 in ['lna', 'lrlx', 'faddrlx']:
            ub2 = '.undef'
        if 'lna' not in [l0, l1] and 'sna' not in [s0, s1] and ub2 == '':
            ub2 = '.racy'
            cond = racy_cond
        fname = f'lb-{l0}-{s0}-{l1}-{s1}.cpp11{ub2}.litmus'
        out = shape.format(l0n=l0, s0n=s0, l1n=l1, s1n=s1, l0=l0s[l0], s0=s0s[s0], l1=l1s[l1], s1=s1s[s1], cond=cond2, ub='-cpp11'+ub2.replace('.','-'))
        with open(fname, 'w') as f:
            f.write(out)
    fname = f'lb-{l0}-{s0}-{l1}-{s1}{ub}.litmus'
    out = shape.format(l0n=l0, s0n=s0, l1n=l1, s1n=s1, l0=l0s[l0], s0=s0s[s0], l1=l1s[l1], s1=s1s[s1], cond=cond, ub=ub.replace('.','-'))
    with open(fname, 'w') as f:
        f.write(out)
