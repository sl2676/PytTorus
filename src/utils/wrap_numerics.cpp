#include <functional>
#include <vector>
#include "Numerics.h"

namespace py = pybind11;

// qbulir and zbrent want a plain c function pointer so a python function cant go straight in.
// so the python funcs go on a stack and torus gets call_top, the stack is so a qbulir
// inside a qbulir still works
static std::vector<std::function<double(double)>*> func_stack;

static double call_top(double x) {
	return (*func_stack.back())(x);
}

struct FuncScope {
	FuncScope(std::function<double(double)>& f) { func_stack.push_back(&f); }
	~FuncScope() { func_stack.pop_back(); }
};

void init_numerics(py::module_ &torus) {
	torus.def("GaussLegendre", [](int n) {
		if (n < 1) throw py::value_error("n has to be at least 1");
		py::array_t<double> x(n), w(n);
		GaussLegendre(x.mutable_data(), w.mutable_data(), n);
		return py::make_tuple(x, w);
	}, py::arg("n"), "Gauss-Legendre points and weights on [-1, 1], returns (x, w)");

	torus.def("LegendrePeven", [](double x, int np) {
		if (np < 1) throw py::value_error("np has to be at least 1");
		py::array_t<double> p(np);
		LegendrePeven(p.mutable_data(), x, np);
		return p;
	}, py::arg("x"), py::arg("np"), "even Legendre polynomials P0, P2, ... P2(np-1) at x");

	torus.def("dLegendrePeven", [](double x, int np) {
		if (np < 1) throw py::value_error("np has to be at least 1");
		py::array_t<double> p(np), d(np);
		dLegendrePeven(p.mutable_data(), d.mutable_data(), x, np);
		return py::make_tuple(p, d);
	}, py::arg("x"), py::arg("np"), "even Legendre polynomials and their derivatives at x, returns (p, d)");

	torus.def("qbulir", [](std::function<double(double)> func, double a, double b, double eps) {
		FuncScope scope(func);
		double err = 0.;
		double res = qbulir(&call_top, a, b, eps, err);
		return py::make_tuple(res, err);
	}, py::arg("func"), py::arg("a"), py::arg("b"), py::arg("eps") = 1e-10,
	"Bulirsch-Stoer integral of func from a to b, returns (integral, error estimate)");

	torus.def("zbrent", [](std::function<double(double)> func, double x1, double x2, double tol) {
		FuncScope scope(func);
		return zbrent(&call_top, x1, x2, tol);
	}, py::arg("func"), py::arg("x1"), py::arg("x2"), py::arg("tol") = 1e-10,
	"Brent root finder, the root has to be bracketed by x1 and x2 (accuracy bottoms out around 1e-8 relative)");
}
