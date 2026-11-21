// Err.h is included via the include path rather than a relative path, so that
// the patched copy of Torus/src/utils that setup.py builds is used (see
// patches/torus-exception-handling.patch). Compiled with -D_exception_handling_,
// its TorusError() throws TorusExcept for fatal errors instead of calling exit(1).
#include "Err.h"
#ifndef _exception_handling_
#error "Torus must be compiled with -D_exception_handling_ and the patched Err.h, otherwise TorusError() exits the Python interpreter. Build with setup.py (see Error handling in README.md)."
#endif
namespace py = pybind11;

// The Python class for TorusExcept (from PytTorus/_exceptions.py). Set once in
// init_err() and kept for the life of the process, because the exception
// translator below is a plain function and cannot capture it.
static PyObject* torus_except_type = nullptr;

void init_err(py::module_ &torus) {
	// TorusExcept does not derive from std::exception, so pybind11 would only report
	// "Caught an unknown exception!". Raise it as PytTorus._torus.TorusExcept instead:
	// a RuntimeError subclass carrying the Torus message and index.
	py::object cls = py::module_::import("PytTorus._exceptions").attr("TorusExcept");
	torus.attr("TorusExcept") = cls;
	torus_except_type = cls.release().ptr();
	py::register_exception_translator([](std::exception_ptr p) {
		try {
			if (p) std::rethrow_exception(p);
		} catch (const TorusExcept& e) {
			py::object exc = py::handle(torus_except_type)(e.msgs, e.index);
			PyErr_SetObject(torus_except_type, exc.ptr());
		}
	});
	torus.attr("toruserrno") = py::cast(&toruserrno);
	torus.def("TorusError", &TorusError, py::arg("msgs"), py::arg("index"),
		"Report an error the way Torus does: raise TorusExcept if index < 0, "
		"otherwise print a warning and set toruserrno.");
}
