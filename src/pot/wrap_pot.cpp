#include <fstream>
#include <vector>
#include "Potential.h"
#include "IsochronePot.h"
#include "KeplerPot.h"
#include "LogPot.h"
#include "MiyamotoNagaiPot.h"
#include "StackelPot.h"
#include "MultiPot.h"
#include "falPot.h"

namespace py = pybind11;

// MultiPotential just keeps the pointer list you give it, so this one owns the list
class PyMultiPotential : public MultiPotential {
public:
	Potential** list;
	PyMultiPotential(Potential** l, int n) : MultiPotential(l, n), list(l) {}
	~PyMultiPotential() { delete[] list; }
};

// pybinding init function
// units are torus units: kpc, Myr, Msun (so velocities in kpc/Myr, use PytTorus.kms)
void init_pot(py::module_ &torus) {
	py::class_<Potential>(torus, "Potential", "base class, use one of the potentials below")
		.def("__call__", [](const Potential &self, py::array_t<double> R, py::array_t<double> z) {
			// works on numbers or whole arrays. uses the version with forces cause thats what the
			// fitting uses (LogPotential's two versions are off by a constant)
			return py::vectorize([&self](double R, double z) { double dR, dz; return self(R, z, dR, dz); })(R, z);
		}, py::arg("R"), py::arg("z"), "Phi(R, z)")
		.def("forces", [](const Potential &self, double R, double z) {
			double dPdR, dPdz;
			double P = self(R, z, dPdR, dPdz);
			return py::make_tuple(P, dPdR, dPdz);
		}, py::arg("R"), py::arg("z"), "returns (Phi, dPhi/dR, dPhi/dz)")
		.def("KapNuOm", &Potential::KapNuOm, py::arg("R"), "epicycle frequencies (kappa, nu, Omega) at R")
		.def("RfromLc", [](const Potential &self, double L) { return self.RfromLc(L); }, py::arg("Lc"),
		"radius of the circular orbit with angular momentum Lc")
		.def("LfromRc", [](const Potential &self, double R) { return self.LfromRc(R); }, py::arg("R"),
		"angular momentum of the circular orbit at R");

	py::class_<IsochronePotential, Potential>(torus, "IsochronePotential")
		.def(py::init<double, double>(), py::arg("M") = 1., py::arg("b") = 1.);
	py::class_<KeplerPotential, Potential>(torus, "KeplerPotential")
		.def(py::init<double>(), py::arg("M") = 1.);
	py::class_<LogPotential, Potential>(torus, "LogPotential")
		.def(py::init<double, double, double>(), py::arg("v0") = 1., py::arg("q") = 1., py::arg("Rc") = 0.);
	py::class_<MiyamotoNagaiPotential, Potential>(torus, "MiyamotoNagaiPotential")
		.def(py::init<double, double, double>(), py::arg("M") = 1., py::arg("a") = 1., py::arg("b") = 1.);
	py::class_<StackelPotential, Potential>(torus, "StackelPotential")
		.def(py::init<double, double, double>(), py::arg("rho0") = 1., py::arg("Rs") = 1., py::arg("q") = 1.);

	// GalaxyPotential is a PotResidual and a Potential, pybind needs to know or the casts break
	py::class_<GalaxyPotential, Potential>(torus, "GalaxyPotential", py::multiple_inheritance())
		.def(py::init([](const std::string &file) {
			std::ifstream from(file);
			if (!from) throw py::value_error("couldnt open " + file);
			return new GalaxyPotential(from);
		}), py::arg("file"), "GalPot potential from a .Tpot file (PytTorus.galpot() for the ones that come with it)");

	py::class_<PyMultiPotential, Potential>(torus, "MultiPotential")
		.def(py::init([](std::vector<Potential*> pots) {
			if (pots.empty()) throw py::value_error("need at least one potential");
			Potential** list = new Potential*[pots.size()];
			std::copy(pots.begin(), pots.end(), list);
			return new PyMultiPotential(list, (int) pots.size());
		}), py::arg("pots"), py::keep_alive<1, 2>(), "sum of a list of potentials");
}
