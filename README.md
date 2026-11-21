# PytTorus ~ Torus Mapper Python Package

[![PyPI version](https://badge.fury.io/py/torus-mapper.svg)](https://badge.fury.io/py/torus-mapper)

## Overview

**PytTorus** is a Python package designed to model the dynamics of galaxies using the torus mapping method. The core functionality is implemented in **C++** for high performance, and exposed to Python using **pybind11**. This combination ensures both computational efficiency and user-friendly interaction for scientific computing tasks.

The package allows users to compute orbital tori based on action integrals and provides robust tools for analyzing orbits in dynamical systems. By utilizing C++ for the heavy numerical operations and Python for high-level scripting, allows for ease of use without the trade off of performance. 

## Key Features

- Efficient computation of orbital tori using **C++** back-end for performance-critical tasks.
- Python bindings implemented via **pybind11**, providing an intuitive interface for Python users.
- Custom **C++** matrix and vector operations, optimized for handling various data types and large-scale computations.
- Time-averaged density and velocity calculations, ideal for N-body simulations and resonance trapping studies.
- Flexibility in setting up initial conditions for dynamical models, with a focus on astronomical applications.

## Installation

Install the package using pip:

```bash
pip install PytTorus
```
## Getting Started

Below is an example of how to use the package to perform Cholesky Decomposition:

```python
import PytTorus
from PytTorus import _torus as torus

A = torus.Matrix(3, 3)
a_data = [[4.0, 12.0, -16.0], [12.0, 37.0, -43.0], [-16.0, -43.0, 98.0]]
N = 3

for i in range(len(a_data)):
  A.set_row(i, torus.Vector(a_data[i]))
print(A)

result = torus.CholeskyDecomposition(A, N)
print("Result of Cholesky Decomposition: ", result)
print("Decomposed Matrix L (lower triangular):\n", A)
```
Below is an example of how to use the package to simulate the motion of a projectile in a 3D space by numerically integrating the Vector:

```python
import PytTorus
from PytTorus import _torus as torus

g = 9.8        # Gravitational constant

# Initial velocities in 3D (x, y, z components)
v0x = 10.0
v0y = 20.0
v0z = 15.0

# Set the integration bounds and accuracy
a = 0.0
b = 2.0
eps = 1e-6

def x_position(t):
	return v0x * t

def y_position(t):
	return v0y * t - 0.5 * g * t * t

def z_position(t):
	return v0z * t

def integrate_vector(funcs, a, b, eps):
	n = len(funcs)
	vector = torus.Vector(0.0, 0.0, 0.0)
	err = 0.0    # Error placeholder
	
	for i in range(n):
		vector.__setitem__(i, torus.qbulir(funcs[i], a, b, eps, err))
		print(f"Component {i} integrated result: {vector[i]}, error: {err}")
	return vector


position_funcs = [x_position, y_position, z_position]
result_vector = integrate_vector(position_funcs, a, b, eps)

print(f"\nProjectile's position at t = {b} seconds:")
for i in range(3):
    print(f"Component {i}: {result_vector[i]} meters")

```

## Error handling

Errors in the C++ code are raised as Python exceptions, so bad input does not end the Python process (or kill a Jupyter kernel):

| Problem | Exception |
| --- | --- |
| Invalid input, e.g. `ln(-1.0)`, a root that is not bracketed (`rtsafe`, `zbrent`), a point outside a table, a singular or non-positive-definite matrix | `ValueError` |
| An iterative routine that does not converge (`rtsafe`, `qbulir`, `zbrent`, `tqli`, `hqr`) | `RuntimeError` |
| A fatal Torus error: `TorusError(msgs, index)` with `index < 0` | `TorusExcept`, a `RuntimeError` subclass with `.msgs` and `.index` |

```python
from PytTorus import _torus as torus

try:
    torus.ln(-1.0)
except ValueError as e:
    print(e)                # error in Mathematics: ln() of argument <= 0

try:
    torus.TorusError("boom", -1)
except torus.TorusExcept as e:
    print(e.msgs, e.index)  # boom -1
```

`CholeskyDecomposition`, `LUDecomposition`, `GaussJordan` and `GaussBack` raise `ValueError` instead of returning `-1`; they return `0` on success. As in Torus, `TorusError` with `index >= 0` is only a warning: it is printed, it sets `toruserrno`, and nothing is raised.

### How Torus is patched

Torus (the `Torus/` checkout of [PaulMcMillan-Astro/Torus](https://github.com/PaulMcMillan-Astro/Torus)) handles fatal errors by printing a message and calling `exit()`. This happens in `MathError()` (`WDMath.cc`), in `TorusError()` (`Err.h`) and in the `Cheby` constructor (`CHB.cc`). `Err.h` has an `_exception_handling_` switch that makes `TorusError()` throw instead, but the header `#undef`s it, so passing `-D_exception_handling_` has no effect on its own.

Rather than maintain a fork or wait for an upstream release, PytTorus applies a small patch at build time, [`patches/torus-exception-handling.patch`](patches/torus-exception-handling.patch), which changes about 20 lines in 3 files:

- `setup.py` copies `Torus/src/utils` into the build directory, applies the patch to the copy and compiles the copy with `-D_exception_handling_`. The `Torus/` checkout is not modified.
- With `_exception_handling_` defined, `MathError()` throws `std::domain_error`, fatal `TorusError()` calls throw `TorusExcept` and `Cheby` throws `std::invalid_argument`. The extension raises these as the exceptions above. Without the define, the patched files behave exactly like upstream.
- `TorusError()` still only warns for `index >= 0` and still sets `toruserrno`, because Torus' fitting code (`Fit.cc`) depends on that. Upstream's disabled exception branch would also throw on warnings, and it does not declare `toruserrno`, so `Fit.cc` does not compile with it.
- The patch must apply exactly. If `Torus/` changes and the patch no longer matches, the build stops with an error. `src/utils/wrap_err.cpp` also refuses to compile against an unpatched `Err.h`.

The patch could also be submitted upstream. Once Torus includes the change, delete the patch file and `BuildExtWithPatchedTorus` in `setup.py`.

### Running the tests

```bash
python setup.py build_ext --inplace
python -m pytest
```

Tests that exercise an error path each run in a separate interpreter, so a regression shows up as a failing test instead of ending the test run.

## Documentation

For detailed documentation and usage examples, please visit our [documentation](https://pypi.org/project/PytTorus/0.0.2/).

## Applications

PytTorus is a versatile tool with numerous applications in astrophysics and computational dynamics. Below are some common use cases:

### 1. Galactic Dynamics Modeling
PytTorus can be used to model the orbital structure of galaxies based on their gravitational potentials. This is useful for:
- Simulating star orbits within axisymmetric and triaxial potentials.
- Investigating the long-term evolution of galactic structures.
- Mapping the motion of stars in both external galaxies and our own Milky Way.
- Comparing simulation results with observational data, such as from Gaia and other space missions.

### 2. N-body Simulations
The package provides tools for generating initial conditions for N-body simulations, often used in galactic dynamics and cosmological simulations. Applications include:
- Setting up dynamically consistent initial conditions for N-body simulations of disk, bulge, and halo components of galaxies.
- Avoiding discreteness noise, which can affect results in traditional N-body setups.
- Constructing equilibrium models that can be refined with observational data.

### 3. Resonance Trapping Studies
PytTorus excels at studying the phenomenon of resonance trapping:
- Investigating how stars get caught in resonances within rotating galactic potentials.
- Analyzing the influence of resonances on the long-term behavior of stellar orbits.
- Using the angle-action framework to explore resonant and near-resonant structures.

### 4. Numerical Solutions in Astrophysics
The package provides high-precision methods for calculating orbits without needing to use time-steppers:
- Directly computing a star’s position and velocity at any point in time, allowing for efficient orbit integrations.
- Calculating time-averaged densities, which are useful in theoretical studies of galactic dynamics.
- Supporting the development of distribution functions based on actions, used for creating accurate galaxy models.

### 5. Stellar Stream Analysis
The package is also capable of helping with stellar stream studies:
- Modeling the phase-space distribution of disrupted star clusters or dwarf galaxies as stellar streams.
- Analyzing the impact of galactic potentials on the dynamics of stellar streams over time.
- Facilitating comparison between simulation results and observed streams like the Sagittarius Stream.

### 6. Academic Research
PytTorus provides a rich platform for academic research in various fields:
- Cosmological simulations for galaxy formation and structure evolution.
- Studies of dark matter distributions by comparing simulated and observed galactic kinematics.
- Generating precise, scalable models that can be used to validate theoretical predictions in galactic dynamics.


## Citation

If you use this package for academic research, please cite the original paper:

Binney, J., & McMillan, P. J. (2015). Torus Mapper: A Code for Dynamical Models of Galaxies. MNRAS, 000(000), 000-000
