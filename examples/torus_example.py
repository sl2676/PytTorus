import numpy as np
import PytTorus as p

print("\\***************\\")
print("|TESTING TORI|")
print("\\***************\\")

# torus units are kpc, Myr, Msun so 220 km/s is 220 * p.kms
# and actions are kpc^2/Myr (1 kpc km/s = p.kms kpc^2/Myr)

print("\nlog potential")
phi = p.LogPotential(220 * p.kms, 0.9, 0.0)
print(f"Phi(8, 0) = {phi(8.0, 0.0)}")

print("---------------------")
print("AutoFit")
J = np.array([0.05, 0.02, 1.6])
T = p.Torus()
flag = T.AutoFit(J, phi)
print(T)
print(f"flag: {flag}")
print(f"frequencies: {T.omega()}")
print(f"R between {T.minR():.3f} and {T.maxR():.3f} kpc, zmax {T.maxz():.3f} kpc")

print("---------------------")
print("Map3D")
th = np.random.uniform(0, 2 * np.pi, (5, 3))
w = T.Map3D(th)
for i in range(len(w)):
	print(f"theta {np.round(th[i], 2)} -> R {w[i, 0]:.3f} z {w[i, 1]:.3f} vphi {w[i, 5] / p.kms:.1f} km/s")

print("---------------------")
print("energy check")
th = np.random.uniform(0, 2 * np.pi, (1000, 3))
w = T.Map3D(th)
E = 0.5 * (w[:, 3]**2 + w[:, 4]**2 + w[:, 5]**2) + phi(w[:, 0], w[:, 1])
print(f"torus energy {T.energy()}, mean along orbit {E.mean()}, scatter {np.std(E) / abs(E.mean()):.2e}")

print("---------------------")
print("milky way (McMillan 2017)")
mw = p.galpot("PJM16_best")
P, dPdR, dPdz = mw.forces(8.21, 0.0)
print(f"vc at the sun: {np.sqrt(8.21 * dPdR) / p.kms:.1f} km/s")

J_sun = np.array([30.0, 10.0, 1900.0]) * p.kms
maddie = p.Torus()
flag = maddie.AutoFit(J_sun, mw)
print(maddie)
print(f"flag: {flag}")
print(f"periods (Myr): {2 * np.pi / maddie.omega()}")

x = maddie.Map3D([0.0, 0.0, 0.0])[:3]
found, v1, v2 = maddie.containsPoint_Vel(x)
print(f"velocities at {np.round(x, 3)}: {v1 / p.kms} and {v2 / p.kms} km/s")
