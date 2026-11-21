#define PYBIND11_DETAILED_ERROR_MESSAGES
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <pybind11/functional.h>
#include <cmath>
#include <stdexcept>
#include <iostream>
#include <string>

// all the torus headers come from the patched copy in build/torus (see setup.py)
#include "./src/casters.h"

#include "./src/utils/wrap_err.cpp"
#include "./src/utils/wrap_pi.cpp"
#include "./src/utils/wrap_units.cpp"
#include "./src/utils/wrap_constants.cpp"
#include "./src/utils/wrap_WDMath.cpp"
#include "./src/utils/wrap_numerics.cpp"
#include "./src/pot/wrap_pot.cpp"
#include "./src/wrap_torus.cpp"

namespace py = pybind11;

PYBIND11_MODULE(_torus, torus) {
	torus.doc() = "pytorus torus library";
	init_err(torus);
	init_pi(torus);
	init_units(torus);
	init_constants(torus);
	init_wdmath(torus);
	init_numerics(torus);
	init_pot(torus);
	init_torus(torus);
}
