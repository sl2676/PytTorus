#include "WDMath.h"

namespace py = pybind11;

void init_wdmath(py::module_ &torus) {
	torus.attr("EulerGamma") = EulerGamma;
	torus.attr("LogofTwo") = LogofTwo;
	torus.attr("LogofTwoInv") = LogofTwoInv;
	torus.attr("LogofTen") = LogofTen;
	torus.attr("LogofTenInv") = LogofTenInv;
		// misc func
	torus.def("SphVol", &SphVol, py::arg("n"), "volume of the unit sphere in n dimensions");
		// logs and exps func
	torus.def("ln", &ln, py::arg("x"));
	torus.def("ld", &ld, py::arg("x"), "log base 2");
	torus.def("lg", &lg, py::arg("x"), "log base 10");
	torus.def("Tento", &Tento, py::arg("x"));
	torus.def("Twoto", &Twoto, py::arg("x"));
		// gamma functions
	torus.def("LogGamma", py::overload_cast<const double>(&LogGamma), py::arg("x"));
	torus.def("LogGamma", py::overload_cast<const double, const double>(&LogGamma), py::arg("a"), py::arg("x"), "log of the incomplete gamma function");
	torus.def("GammaP", &GammaP, py::arg("a"), py::arg("x"), "regularized incomplete gamma function P(a, x)");
	torus.def("Loggamma", &Loggamma, py::arg("a"), py::arg("x"));
		// exponential integrals
	torus.def("En", &En, py::arg("n"), py::arg("x"));
	torus.def("Ei", &Ei, py::arg("x"));
		// Bessel func
	torus.def("J0", &J0, py::arg("x"));
	torus.def("J1", &J1, py::arg("x"));
	torus.def("Jn", &Jn, py::arg("n"), py::arg("x"));
	torus.def("Y0", &Y0, py::arg("x"));
	torus.def("Y1", &Y1, py::arg("x"));
	torus.def("Yn", &Yn, py::arg("n"), py::arg("x"));
	torus.def("I0", &I0, py::arg("x"));
	torus.def("I1", &I1, py::arg("x"));
	torus.def("In", &In, py::arg("n"), py::arg("x"));
	torus.def("K0", &K0, py::arg("x"));
	torus.def("K1", &K1, py::arg("x"));
	torus.def("Kn", &Kn, py::arg("n"), py::arg("x"));
		// hermite polynomials
	torus.def("HermiteH", py::overload_cast<const int, const double>(&HermiteH), py::arg("n"), py::arg("x"));
}
