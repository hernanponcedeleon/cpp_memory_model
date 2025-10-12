#!/usr/bin/env python3
from itertools import product

# Normal MP shape.
shape = """C mp-{s0n}-{s1n}-{l0n}-{l1n}{ub}
{{ [x] = 0; [y] = 0; }}

P0 (int* x, int* y) {{
  {s0};
  {s1};
}}

P1 (int* x, int* y) {{
  int a = {l0};
  if (a != 0) {{
    int b = {l1};
  }}
}}
{P2}
{cond}"""

ok_cond='~exists(~1:a=0 /\ 1:b=0)'
racy_cond='forall(1:b=0 \/ 1:b=1)'

s0s = {
    'sna': '*x = 1',
    'srlx': 'atomic_store_explicit(x, 1, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(x, 1, memory_order_relaxed)',
}

s1s = {
    # Undefined
    'sna' : '*y = 1',

    # Racy or Undefined
    'srlx': 'atomic_store_explicit(y, 1, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',

    # Release patterns with fences
    'frel-srlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(y, 1, memory_order_relaxed)',
    'frel-faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',
    'frel-2srlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(y, 1, memory_order_relaxed);\n  atomic_store_explicit(y, 2, memory_order_relaxed)',
    'frel-2faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',
    'frel-srlx-faddrlx': 'atomic_thread_fence(memory_order_release);\n  atomic_store_explicit(y, 1, memory_order_relaxed);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',
    'frel-faddrlx-srlx': 'atomic_thread_fence(memory_order_release);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed);\n  atomic_store_explicit(y, 2, memory_order_relaxed)',

    # Release pattern with operations
    'srel': 'atomic_store_explicit(y, 1, memory_order_release)',
    'srel-srel': 'atomic_store_explicit(y, 1, memory_order_release);\n  atomic_store_explicit(y, 2, memory_order_release)',
    'srel-faddrlx': 'atomic_store_explicit(y, 1, memory_order_release);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',
    'faddrel-faddrlx': 'atomic_fetch_add_explicit(y, 1, memory_order_release);\n  atomic_fetch_add_explicit(y, 1, memory_order_relaxed)',

    # Release sequences: pre-C++17
    'srel-srlx': 'atomic_store_explicit(y, 1, memory_order_release);\n  atomic_store_explicit(y, 2, memory_order_relaxed)',

    # Not a release sequence pre-C++17
    'faddrel-srlx': 'atomic_fetch_add_explicit(y, 1, memory_order_release);\n  atomic_store_explicit(y, 2, memory_order_relaxed)',
}

l0s = {
    # Undefined
    'lna': '*y',

    # Racy or Undefined
    'lrlx': 'atomic_load_explicit(y, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(y, 0, memory_order_relaxed)',

    # Acquire patterns with fences
    'lrlx-facq': 'atomic_load_explicit(y, memory_order_relaxed);\n  atomic_thread_fence(memory_order_acquire)',
    'faddrlx-facq': 'atomic_fetch_add_explicit(y, 0, memory_order_relaxed);\n  atomic_thread_fence(memory_order_acquire)',

    # Acquire patterns with operations
    'lacq': 'atomic_load_explicit(y, memory_order_acquire)',
    'faddacq': 'atomic_fetch_add_explicit(y, 0, memory_order_acquire)',

    # Acquire sequences: not supported in C++
    'lrlx-lacq': 'atomic_load_explicit(y, memory_order_relaxed);\n  int c = atomic_load_explicit(y, memory_order_acquire)',
}

l1s = {
    'lna': '*x',
    'lrlx': 'atomic_load_explicit(x, memory_order_relaxed)',
    'faddrlx': 'atomic_fetch_add_explicit(x, 0, memory_order_relaxed)',
}

P2 = """
P2 (int* y) {
  atomic_store_explicit(y, 0, memory_order_relaxed);
}
"""

# Release and Acquire patterns:
release_patterns = ['frel-srlx', 'frel-faddrlx', 'frel-2srlx', 'frel-2faddrlx', 'frel-srlx-faddrlx', 'frel-faddrlx-srlx', 'srel', 'srel-srel', 'srel-faddrlx', 'faddrel-faddrlx']
acquire_patterns_no_sequences = ['lrlx-facq', 'faddrlx-facq', 'lacq', 'faddacq']
acquire_patterns = acquire_patterns_no_sequences + ['lrlx-lacq'] # BUG: lrlx-lacq should not create an acquire pattern

# Pre C++17 release pattenrs include release sequences:
release_patterns_cpp11 = release_patterns + ['srel-srlx']

# Test check:
def check(s0, s1, l0, l1, rel, acq):
    cond = ok_cond
    ub = ''
    # If s1 and l0 do not synchronize with release -> acquire pattern: racy
    if s1 not in rel or l0 not in acq:
        ub = '.racy'
        cond = racy_cond
        # If racy and data-race: undefined behavior:
        if 'sna' in [s0, s1] or 'lna' in [l0, l1]:
            ub = '.undef'
    return cond, ub


for s0, s1, l0, l1 in product(s0s, s1s, l0s, l1s):
    cond, ub = check(s0, s1, l0, l1, release_patterns, acquire_patterns)
    cond11, ub11 = check(s0, s1, l0, l1, release_patterns_cpp11, acquire_patterns)

    # If C++ < 17 and C++ >=17 condition differs generate two versions of the test, one for C++11 and one for C++17:
    if cond != cond11 or ub != ub11:
        fname = f'mp-{s0}-{s1}-{l0}-{l1}.cpp11{ub11}.litmus'
        out = shape.format(s0n=s0, s1n=s1, l0n=l0, l1n=l1, s0=s0s[s0], s1=s1s[s1], l0=l0s[l0], l1=l1s[l1], cond=cond11, ub='-cpp11' + ub11.replace('.','-'), P2='\n')
        with open(fname, 'w') as f:
            f.write(out)
        # If acquire sequence: generate a second version of this test with external thread
        if l0 in ['lrlx-lacq']:
            condAS, ubAS = check(s0, s1, l0, l1, release_patterns_cpp11, acquire_patterns_no_sequences)
            fname = f'mp-{s0}-{s1}-{l0}-{l1}-srlx.cpp11{ubAS}.litmus'
            out = shape.format(s0n=s0, s1n=s1, l0n=l0, l1n=l1, s0=s0s[s0], s1=s1s[s1], l0=l0s[l0], l1=l1s[l1], cond=condAS, ub=ubAS.replace('.','-'), P2=P2)
            with open(fname, 'w') as f:
                f.write(out)

    # If acquire sequence: generate a second version of this test with external thread
    if l0 in ['lrlx-lacq']:
        condAS, ubAS = check(s0, s1, l0, l1, release_patterns, acquire_patterns_no_sequences)
        fname = f'mp-{s0}-{s1}-{l0}-{l1}-srlx{ubAS}.litmus'
        out = shape.format(s0n=s0, s1n=s1, l0n=l0, l1n=l1, s0=s0s[s0], s1=s1s[s1], l0=l0s[l0], l1=l1s[l1], cond=condAS, ub=ubAS.replace('.','-'), P2=P2)
        with open(fname, 'w') as f:
            f.write(out)

    fname = f'mp-{s0}-{s1}-{l0}-{l1}{ub}.litmus'
    out = shape.format(s0n=s0, s1n=s1, l0n=l0, l1n=l1, s0=s0s[s0], s1=s1s[s1], l0=l0s[l0], l1=l1s[l1], cond=cond, ub=ub.replace('.','-'), P2='\n')
    with open(fname, 'w') as f:
        f.write(out)
