# PytTorus ~ Torus Mapper Python Package

[![PyPI version](https://badge.fury.io/py/PytTorus.svg)](https://badge.fury.io/py/PytTorus)

## Overview

**PytTorus** is a Python package for modeling the dynamics of galaxies using the torus mapping method. It wraps the **Torus Mapper**, the **C++** code by Paul McMillan and James Binney, and exposes it to Python using **pybind11**. The heavy lifting stays in C++ and everything goes in and comes out as **numpy** arrays.

Given a gravitational potential and a set of actions (J_R, J_z, J_phi), PytTorus fits the orbital torus with those actions. Once the torus is fitted the whole orbit is known, so you can get a star's position and velocity at any angles without integrating anything.

## Key Features

- Fit orbital tori for given actions in an axisymmetric potential with `Torus.AutoFit`.
- Map angles to positions and velocities (`Map3D`) for one point or thousands at once.
- Orbital frequencies, energy, and the radial and vertical extent of the orbit.
- Check if an orbit passes through a point and get the velocities it has there (`containsPoint`, `containsPoint_Vel`).
- Potentials: isochrone, Kepler, logarithmic, Miyamoto-Nagai, Stackel, sums of them, and the GalPot Milky Way models that come with Torus (McMillan 2011 and 2017, Binney & Tremaine, Dehnen & Binney 1998, Piffl et al 2014).
- Save and load tori in EBF files.
- Errors in the C++ code raise Python exceptions (`PytTorus.TorusError`) instead of killing Python.
- Some of the Torus numerics: Gauss-Legendre quadrature, Bulirsch-Stoer integration, Brent root finding, Legendre polynomials, Bessel and gamma functions.

## Installation

Torus is a git submodule, so clone with `--recursive`:

```bash
git clone --recursive https://github.com/sl2676/PytTorus.git
cd PytTorus
pip install .
```

If you already cloned without `--recursive`, run `git submodule update --init` first. You need a C++17 compiler (GCC or clang, Linux or macOS).

## Getting Started

Torus works in kpc, Myr and solar masses, so velocities are in kpc/Myr and actions are in kpc^2/Myr. `PytTorus.kms` converts from km/s.

Below is an example of how to use the package to fit a torus in a logarithmic potential and get the positions and velocities around the orbit:

```python
import numpy as np
import PytTorus as p

phi = p.LogPotential(220 * p.kms, 0.9, 0.0)    # v0, flattening q, core radius

J = np.array([0.05, 0.02, 1.6])                 # JR, Jz, Jphi in kpc^2/Myr
T = p.Torus()
flag = T.AutoFit(J, phi)                        # 0 means the fit worked
print(T, flag)
print("frequencies:", T.omega())

th = np.random.uniform(0, 2 * np.pi, (1000, 3))     # angles
w = T.Map3D(th)                                      # (R, z, phi, vR, vz, vphi) for each one
```

Below is an example of how to use the package to fit the orbit of a sun-like star in the McMillan (2017) Milky Way potential:

```python
import numpy as np
import PytTorus as p

mw = p.galpot("PJM16_best")                         # p.pot_files() lists all of them
J = np.array([30.0, 10.0, 1900.0]) * p.kms          # kpc km/s -> kpc^2/Myr

T = p.Torus()
T.AutoFit(J, mw)
print("periods (Myr):", 2 * np.pi / T.omega())

x = T.Map3D([0.0, 0.0, 0.0])[:3]                    # a point on the orbit
found, v1, v2 = T.containsPoint_Vel(x)              # the velocities the orbit has there
```

There is a longer example in `examples/torus_example.py`.

## Running the Tests

```bash
pip install pytest
python -m pytest tests
```

The tests check the numerics against numpy, the circular speed of the McMillan (2017) potential, the isochrone torus against the exact energy, and that energy and angular momentum stay constant around a fitted torus.

## Documentation

Every function has a docstring (`help(p.Torus)`). The [PytTorus docs](https://github.com/sl2676/PytTorus-Docs) cover the old 0.0.x API and still need updating for 0.1. The original Torus documentation is in `Torus/` and `torus_mapper_doc.pdf`.

## Applications

### 1. Galactic Dynamics Modeling
- Orbits of stars in axisymmetric potentials, including realistic Milky Way models.
- Comparing orbits between different Milky Way potentials.

### 2. Orbits Without Time-Steppers
- A star's position and velocity at any angles straight from the torus, no orbit integration.
- Orbital frequencies and periods directly from the actions.

### 3. Action-Based Models
- Building samples of stars from distributions in action space.
- Finding the velocities an orbit has at a given position, which is what you need to compare models to observed stars.

## TODO

- resonant tori (resTorus)
- potentials written in Python
- coordinate transforms (PJMCoords) for working with Gaia data
- distribution functions
- surfaces of section

## Citation

If you use this package for academic research, please cite the original paper:

Binney, J., & McMillan, P. J. (2016). Torus Mapper: a code for dynamical models of galaxies. MNRAS, 456, 1982-1998

## License

GPL-2.0, same as Torus (see `LICENSE`). The EBF library in `libebf_c_cpp-0.0.3` has its own license (`libebf_c_cpp-0.0.3/COPYING`).
