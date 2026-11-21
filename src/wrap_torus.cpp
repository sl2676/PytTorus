#include <sstream>
#include "Torus.h"

namespace py = pybind11;

// a Torus() has no maps until its fitted or read in, mapping before that segfaults
// so we keep track here and throw instead
class PyTorus : public Torus {
public:
	bool fitted = false;
	void check() const {
		if (!fitted) throw py::value_error("torus isnt fitted yet, call AutoFit or read_ebf first");
	}
};

// runs a torus map over one set of angles (3,) or a bunch of them (N, 3)
template<class F>
py::array_t<double> map_angles(F map, py::array_t<double, py::array::c_style | py::array::forcecast> th) {
	if (th.ndim() == 1 && th.shape(0) == 3) {
		Angles A;
		for (int i = 0; i < 3; i++) A[i] = th.at(i);
		return to_numpy(map(A), 6);
	}
	if (th.ndim() != 2 || th.shape(1) != 3) throw py::value_error("angles have to be shape (3,) or (N, 3)");
	py::ssize_t n = th.shape(0);
	py::array_t<double> out({n, (py::ssize_t) 6});
	auto a = th.unchecked<2>();
	auto o = out.mutable_unchecked<2>();
	for (py::ssize_t k = 0; k < n; k++) {
		Angles A;
		for (int i = 0; i < 3; i++) A[i] = a(k, i);
		auto w = map(A);
		for (int i = 0; i < 6; i++) o(k, i) = w(i);
	}
	return out;
}

// pybinding init function
void init_torus(py::module_ &torus) {
	py::class_<PyTorus>(torus, "Torus")
		.def(py::init<>())
		.def("AutoFit", [](PyTorus &self, Actions J, Potential* Phi, double tol, int Max, int Ni, int Nt,
						int Over, int Nr, int Nstep, int Nth, int err) {
			int flag = self.AutoFit(J, Phi, tol, Max, Ni, Nt, Over, Nr, Nstep, Nth, err);
			self.fitted = true;
			return flag;
		}, py::arg("J"), py::arg("Phi"), py::arg("tol") = 0.003, py::arg("Max") = 600, py::arg("Ni") = 150,
		py::arg("Nt") = 12, py::arg("Over") = 3, py::arg("Nr") = 16, py::arg("Nstep") = 200, py::arg("Nth") = 12,
		py::arg("err") = 0, py::keep_alive<1, 3>(),
		"fits the torus with actions J = (JR, Jz, Jphi) in the potential Phi. returns the flag:\n"
		"0 = good, -1 = broke, -2 = missed tol (but < 2 tol), -3 = missed 2 tol, -4 = angle fit failed")

		.def("Map3D", [](const PyTorus &self, py::array_t<double, py::array::c_style | py::array::forcecast> th) {
			self.check();
			return map_angles([&self](const Angles& A) { return self.Map3D(A); }, th);
		}, py::arg("theta"), "(R, z, phi, vR, vz, vphi) at the angles theta = (TR, Tz, Tphi), theta is (3,) or (N, 3)")
		.def("FullMap", [](const PyTorus &self, py::array_t<double, py::array::c_style | py::array::forcecast> th) {
			self.check();
			return map_angles([&self](const Angles& A) { return self.FullMap(A); }, th);
		}, py::arg("theta"), "same as Map3D but as a GCY (R, z, phi, vR, vz, vphi)")

		.def("containsPoint", [](const PyTorus &self, Position x) {
			self.check();
			return self.containsPoint(x);
		}, py::arg("x"), "True if the orbit ever gets to x = (R, z, phi)")
		.def("containsPoint_Vel", [](const PyTorus &self, Position x) {
			self.check();
			Velocity v1, v2;
			bool found = self.containsPoint_Vel(x, v1, v2);
			return py::make_tuple(found, v1, v2);
		}, py::arg("x"), "(found, v1, v2), the two independent velocities (vR, vz, vphi) the orbit has at x")

		.def("actions", [](const PyTorus &self) { return self.actions(); }, "(JR, Jz, Jphi)")
		.def("omega", [](const PyTorus &self) { return self.omega(); }, "frequencies (OmegaR, Omegaz, Omegaphi)")
		.def("errors", [](const PyTorus &self) { return self.errors(); }, "fit errors")
		.def("TP", [](const PyTorus &self) { self.check(); return self.TP(); }, "toy isochrone parameters")
		.def("energy", &PyTorus::energy)
		.def("minR", &PyTorus::minR)
		.def("maxR", &PyTorus::maxR)
		.def("maxz", &PyTorus::maxz)
		.def("NumberofSn", [](const PyTorus &self) { self.check(); return self.NumberofSn(); })
		.def("fitted", [](const PyTorus &self) { return self.fitted; })

		.def("write_ebf", [](PyTorus &self, const std::string &file, const std::string &name, const std::string &mode) {
			self.check();
			return self.write_ebf(file, name, mode);
		}, py::arg("file"), py::arg("name"), py::arg("mode") = "a", "saves the torus to an ebf file")
		.def("read_ebf", [](PyTorus &self, const std::string &file, const std::string &name) {
			bool ok = self.read_ebf(file, name);
			if (ok) self.fitted = true;
			return ok;
		}, py::arg("file"), py::arg("name"), "loads a torus saved with write_ebf")

		.def("show", [](const PyTorus &self) {
			self.check();
			std::ostringstream out;
			self.show(out);
			return out.str();
		}, "all the torus details as a string")
		.def("__repr__", [](const PyTorus &self) {
			if (!self.fitted) return std::string("Torus(not fitted)");
			std::ostringstream out;
			Actions J = self.actions();
			out << "Torus(J=(" << J(0) << ", " << J(1) << ", " << J(2) << "), E=" << self.energy() << ")";
			return out.str();
		});
}
