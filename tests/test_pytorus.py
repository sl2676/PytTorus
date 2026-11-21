import numpy as np
import pytest
import PytTorus as p

# torus works in kpc, Myr, Msun so actions are kpc^2/Myr and velocities kpc/Myr


@pytest.fixture(scope="module")
def log_torus():
	phi = p.LogPotential(220 * p.kms, 0.9, 0.0)
	J = np.array([0.05, 0.02, 1.6])
	T = p.Torus()
	flag = T.AutoFit(J, phi)
	return T, phi, J, flag


# ---------------- units / numerics ----------------

def test_units():
	assert p.kms == pytest.approx(1.0227e-3, rel=1e-4)
	assert p.G == pytest.approx(4.4987e-12, rel=1e-4)


def test_gauss_legendre():
	x, w = p.GaussLegendre(7)
	xn, wn = np.polynomial.legendre.leggauss(7)
	order = np.argsort(x)
	assert np.allclose(x[order], xn, atol=1e-10)
	assert np.allclose(w[order], wn, atol=1e-9)


def test_qbulir():
	res, err = p.qbulir(lambda x: np.exp(-x * x), 0.0, 1.0)
	assert res == pytest.approx(0.7468241328124271, abs=1e-9)
	assert err >= 0


def test_qbulir_small_numbers():
	# the old version rounded anything under 1e-9 to 0
	res, err = p.qbulir(lambda x: 1e-10, 0.0, 1.0)
	assert res == pytest.approx(1e-10, rel=1e-9)


def test_qbulir_nested():
	res, err = p.qbulir(lambda y: p.qbulir(lambda x: x * y, 0.0, 1.0)[0], 0.0, 1.0)
	assert res == pytest.approx(0.25, abs=1e-9)


def test_zbrent():
	assert p.zbrent(lambda x: np.cos(x) - x, 0.0, 1.0) == pytest.approx(0.7390851332151607, abs=1e-7)


def test_special_functions():
	assert p.J0(0.0) == pytest.approx(1.0)
	assert p.LogGamma(5.0) == pytest.approx(np.log(24.0))
	assert p.HermiteH(3, 0.5) == pytest.approx(8 * 0.5**3 - 12 * 0.5)


# ---------------- errors dont kill python anymore ----------------

def test_math_error_raises():
	with pytest.raises(p.TorusError, match="ln"):
		p.ln(-1.0)
	assert p.ln(np.e) == pytest.approx(1.0)


def test_numerics_error_raises():
	with pytest.raises(p.TorusError, match="bracketed"):
		p.zbrent(lambda x: x * x + 1, 0.0, 1.0)


def test_python_error_in_callback():
	def bad(x):
		raise ValueError("nope")
	with pytest.raises(ValueError, match="nope"):
		p.qbulir(bad, 0.0, 1.0)


def test_unfitted_torus_raises():
	with pytest.raises(ValueError):
		p.Torus().Map3D([0.0, 0.0, 0.0])


# ---------------- potentials ----------------

def test_log_potential_flat_curve():
	v0 = 220 * p.kms
	phi = p.LogPotential(v0, 1.0, 0.0)
	for R in [2.0, 8.0, 20.0]:
		P, dPdR, dPdz = phi.forces(R, 0.0)
		assert R * dPdR == pytest.approx(v0 * v0)
	R = np.linspace(1, 10, 5)
	assert phi(R, 0 * R).shape == (5,)
	assert phi(8.0, 0.0) == pytest.approx(phi.forces(8.0, 0.0)[0])


def test_galpot_mcmillan17():
	# McMillan (2017) best model has v0 = 233.1 km/s at R0 = 8.21 kpc
	phi = p.galpot("PJM16_best")
	P, dPdR, dPdz = phi.forces(8.21, 0.0)
	assert np.sqrt(8.21 * dPdR) / p.kms == pytest.approx(233.1, abs=0.5)
	with pytest.raises(ValueError):
		p.galpot("not_a_potential")


def test_multi_potential():
	a = p.MiyamotoNagaiPotential(5e10, 3.0, 0.3)
	b = p.IsochronePotential(1e11, 1.0)
	both = p.MultiPotential([a, b])
	assert both(8.0, 0.5) == pytest.approx(a(8.0, 0.5) + b(8.0, 0.5))


# ---------------- tori ----------------

def test_isochrone_torus_exact():
	# toy map is an isochrone so in an isochrone potential the torus should be (almost) exact
	M, b = 1e11, 1.0
	J = np.array([0.05, 0.03, 1.0])
	T = p.Torus()
	assert T.AutoFit(J, p.IsochronePotential(M, b)) == 0
	GM = M * p.G
	L = abs(J[2]) + J[1]
	H = -2 * GM**2 / (2 * J[0] + L + np.sqrt(L * L + 4 * GM * b))**2
	assert T.energy() == pytest.approx(H, rel=1e-4)
	assert np.allclose(T.actions(), J)


def test_energy_constant_on_torus(log_torus):
	T, phi, J, flag = log_torus
	assert flag == 0
	th = np.random.default_rng(1).uniform(0, 2 * np.pi, (300, 3))
	w = T.Map3D(th)
	assert w.shape == (300, 6)
	R, z, vR, vz, vphi = w[:, 0], w[:, 1], w[:, 3], w[:, 4], w[:, 5]
	E = 0.5 * (vR**2 + vz**2 + vphi**2) + phi(R, z)
	assert np.std(E) / abs(np.mean(E)) < 1e-3
	assert np.mean(E) == pytest.approx(T.energy(), rel=1e-3)
	# Jphi = R vphi exactly
	assert np.allclose(R * vphi, J[2])
	assert np.all((R >= T.minR() - 1e-6) & (R <= T.maxR() + 1e-6))
	assert np.all(np.abs(z) <= T.maxz() + 1e-6)


def test_single_angles_match_batch(log_torus):
	T = log_torus[0]
	th = np.array([[0.1, 0.2, 0.3], [1.0, 2.0, 3.0]])
	w = T.Map3D(th)
	assert np.allclose(T.Map3D(th[1]), w[1])


def test_contains_point(log_torus):
	T = log_torus[0]
	w = T.Map3D([0.7, 1.9, 0.0])
	assert T.containsPoint(w[:3])
	found, v1, v2 = T.containsPoint_Vel(w[:3])
	assert found
	# the real velocity is one of the two (or one with vR, vz both flipped)
	cands = [v1, v2, v1 * [-1, -1, 1], v2 * [-1, -1, 1]]
	assert min(np.abs(c - w[3:]).max() for c in cands) < 1e-4
	assert not T.containsPoint([30.0, 0.0, 0.0])


def test_ebf_roundtrip(log_torus, tmp_path):
	T = log_torus[0]
	f = str(tmp_path / "tori.ebf")
	assert T.write_ebf(f, "t1", "w")
	T2 = p.Torus()
	assert T2.read_ebf(f, "t1")
	th = np.random.default_rng(2).uniform(0, 2 * np.pi, (20, 3))
	assert np.allclose(T2.Map3D(th), T.Map3D(th))
