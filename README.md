C++ Memory Model Litmus tests
============================

Collection of C++ Memory Model litmus tests in `.litmus` format and reference memory models in `.cat`.

[herd]: https://github.com/herd/herdtools7
[Dartagnan]: https://github.com/hernanponcedeleon/Dat3M

# Litmus Test Naming Convention

Litmus test naming convention:

* `.racy`: well-defined executions but insufficient synchronization to prevent the shape's outcome (~non-deterministic).
* `.undef`: undefined behavior
* `.cppXX`: precisely requires `./model/cppXX.cat`.
  * Absence of `.cppXX`: runs with default model (see below).

# Instructions

To run all tests:

* With [herd]: `./ci/run`
* With [Dartagnan]: `./ci/run_dat3m`

Currently, only Dartagnan supports running a sub-set of the forward progress tests.
To run the remaining tests:  `./ci/run_rt`.

# Models

Available models in `model/`.
`./ci/run` runs all tests with as follows by default.
**Default Model**:
- [`model/cpp17.cat`](./model/cpp17.cat) for tests that don't specify `.cppXX`.
- [`model/cpp11.cat`](./model/cpp11.cat) for tests that specify `.cpp11`.

To choose a different model: `./ci/run <model_name>` with a `<model_name>` matching `./model/<model_name>.cat`.

## RC11

The `[./model/rc11.cat]` was adapted for [herd] by Simon Colin from: Ori Lahav, Viktor Vafeiadis, Jeehoon Kang, Chung-Kil Hur, and Derek Dreyer, _Repairing sequential consistency in C/C++11_, PLDI '17.

## C++11

The [`./model/cpp11.cat`](./model/cpp11.cat) deviates from RC11 as follows.
In RC11, tests of the form:

```cpp
// Thread 0:
*y = 1;
atomic_store_explicit(x, 1, memory_order_release);
atomic_store_explicit(x, 3, memory_order_relaxed);

// Thread 1
int a = atomic_load_explicit(x, memory_order_acquire);
if (a == 3)
  int b = *y;

// Thread 2
atomic_store_explicit(x, 2, memory_order_relaxed);
```

are well-defined (if `a == 3` then `b = 1`) since Thread 2 store does not break the release sequence headed by Thread 1 release store.

However, C++11 and C++14 state:

> A release sequence headed by a release operation A on an atomic object M is a maximal contiguous sub-sequence of side effects in the modification order of M, where the first operation is A, **and every subsequent operation is performed by the same thread that performed A**, or is an atomic read-modify-write operation.

We incorporate this into the [model/cpp11.cat](./model/cpp11.cat) as follows:

```diff
- let rs = [W]; (sb & loc)?; [W & (RLX | REL | ACQ_REL | ACQ | SC)]; (rf; myrmw)*
+ let rs = ([W]; (sb & loc)?; [W & (RLX | REL | ACQ_REL | ACQ | SC)]) \ (coe; coe); (rf; myrmw)*
```

Notice also that the comma after the high-lighted bold section above is load bearing.
As a consequence, the following test is not allowed by C++11 due to the read-modify-write breaking the release sequence:

```cpp
// Thread 0:
*y = 1;
atomic_store_explicit(x, 1, memory_order_release);
atomic_store_explicit(x, 3, memory_order_relaxed);

// Thread 1
int a = atomic_load_explicit(x, memory_order_acquire);
if (a == 3)
  int b = *y;

// Thread 2
atomic_fetch_add_explicit(x, 1, memory_order_relaxed);
```

Furthermore, C++11 lacks the OOTA fix:

```diff
- acyclic (sb | rf) as no-thin-air
```

## C++17

The [`./model/cpp17.cat`](./model/cpp17.cat) deviates from the C++11 [`./model/cpp11.cat`](./model/cpp11.cat) as follows.
C++17 removed the capability of contiguous same thread writes to extend release sequences:

> A release sequence headed by a release operation A on an atomic object M is a maximal contiguous sub-sequence of side effects in the modification order of M, where the first operation is A, and every subsequent operation is ~performed by the same thread that performed A**, or is~ an atomic read-modify-write operation.

As a consequence, the following test which is well-defined in C++11 (if `a == 3` then `b == 1`) becomes undefined in C++17:

```cpp
// Thread 0:
*y = 1;
atomic_store_explicit(x, 1, memory_order_release);
atomic_store_explicit(x, 3, memory_order_relaxed);

// Thread 1
int a = atomic_load_explicit(x, memory_order_acquire);
if (a == 3)
  int b = *y;
```

We incorporate this into the [model/cpp17.cat](./model/cpp17.cat) as follows:

```diff
- let rs = ([W]; (sb & loc)?; [W & (RLX | REL | ACQ_REL | ACQ | SC)]) \ (coe; coe); (rf; myrmw)*
+ let rs = [W & (RLX | REL | ACQ_REL | ACQ | SC)]; (rf; myrmw)*
```

# References

- [Power and Arm Litmus Tests (test6.pdf)](https://www.cl.cam.ac.uk/~pes20/ppc-supplemental/test6.pdf): Susmit Sarkar, Peter Sewell, Jade Alglave, Luc Maranget, Derek Williams, Understanding POWER Multiprocesors, PLDI '11. Supplemental material: _Quick reference for litmus test families_ (see [project page](https://www.cl.cam.ac.uk/~pes20/ppc-supplemental/index.html)).
- [models/rc11.cat](./models/rc11.cat): sourced from [herd], originally written by Simon Colin.
- [tests/popl15](./tests/popl15): sourced from [herd], originally from: Viktor Vafeiadis, Thibaut Balabonski, Soham Chakraborty, Robin Morisset, and Francesco Zappa Nardelli, _Common Compiler Optimisations are Invalid in the C11 Memory Model and what we can do about it_, POPL '15.
- [tests/herd](./tests/herd): sourced from [hers].
- [tests/pldi17](./tests/pld17): Ori Lahav, Viktor Vafeiadis, Jeehoon Kang, Chung-Kil Hur, and Derek Dreyer, _Repairing sequential consistency in C/C++11_, PLDI '17.
- [tests/dat3m](./tests/dat3m): sourced from Dartagnan's test suite at [Dat3M](https://github.com/hernanponcedeleon/Dat3M).
- [tests/cpp17]: sourced from Hans Boehm, Olivier Giroux, and Viktor Vafeiades, [P0982R1: Weaken Release Sequences](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p0982r1.html), 2018. Also from [mailing list discussion](https://lists.isocpp.org/parallel/2018/03/1643.php) and [P0668](http://wg21.link/p0668).
- [tests/paul_oota]: https://github.com/paulmckrcu/oota/tree/master/litmus

TODO:
- Add more tests:
  - https://github.com/rymrg/rocker/tree/popl21/examples
  - https://github.com/rymrg/rocker/tree/pldi19/examples/submission
  - Bridging the Gap between Programming Languages and Hardware Weak Memory Models
  - mp-release-sequence-store-and-external-store.litmus should not be accepted by rc11? need to talk with Ori
- Include new lb shapes (from LICM, MRD, ...)