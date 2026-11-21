import json
import multiprocessing as mp
import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import numpy as np
import PytTorus as p

# galaxy lab: a 3d milky way where every star sits on its own torus
# run from the repo root:  PYTHONPATH=. python examples/galaxy_lab/galaxy_lab.py
# then open http://localhost:8000 in your browser
#
# the trick: on a torus a star just moves its angles forward at constant speed
# (theta = theta0 + omega t) and the position only depends on theta_R and theta_z
# (theta_phi just spins it around). so each star gets a little G x G table over
# (theta_R, theta_z) and the browser can animate it forever without torus

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "galaxy_cache.npz")
VERSION = 1
G = 24          # table size per star
M = 48          # resolution of the 4d torus you get when you click a star
PORT = 8000

N_DISC, N_LOCAL, N_HALO = 1600, 1000, 250
pot = None
fit_lock = threading.Lock()


def vc(R):
	P, dPdR, dPdz = pot.forces(R, 0.0)
	return np.sqrt(R * dPdR)


def sample_actions(rng):
	# kind: 0 = disc, 1 = local (the ones that get kicked), 2 = halo, 3 = the sun
	# everything in kpc km/s and converted at the end
	J, kind = [[10.0, 1.0, 1910.0]], [3]
	for i in range(N_DISC):
		Rg = 0
		while not 3.0 < Rg < 13.0:
			Rg = rng.gamma(2.0, 2.6)    # exponential disc, R exp(-R/Rd)
		J.append([min(rng.exponential(15.0), 120.0), min(rng.exponential(6.0), 60.0), Rg * vc(Rg) / p.kms])
		kind.append(0)
	# stars at the suns radius, narrow in Jphi so the phase spiral comes out sharp
	for i in range(N_LOCAL):
		J.append([rng.uniform(3, 10), rng.uniform(0.7, 6.7)**2, rng.uniform(1890, 1910)])
		kind.append(1)
	# halo, big puffy orbits and some go backwards
	for i in range(N_HALO):
		J.append([rng.uniform(100, 600), rng.uniform(100, 1500), rng.uniform(-1500, 1500)])
		kind.append(2)
	return np.array(J) * p.kms, np.array(kind)


def angle_grid(n):
	th = np.linspace(0, 2 * np.pi, n, endpoint=False)
	TR, TZ = np.meshgrid(th, th, indexing="ij")
	return np.column_stack([TR.ravel(), TZ.ravel(), np.zeros(n * n)])


def init_worker():
	global pot
	# torus prints debug stuff while it fits, send that to /dev/null
	devnull = os.open(os.devnull, os.O_WRONLY)
	os.dup2(devnull, 1)
	pot = p.galpot("PJM16_best")


def fit_star(J):
	T = p.Torus()
	try:
		flag = T.AutoFit(J, pot)
	except p.TorusError:
		return None
	if flag not in (0, -2):
		return None
	w = T.Map3D(angle_grid(G))
	dphi = (w[:, 2] + np.pi) % (2 * np.pi) - np.pi
	table = np.column_stack([w[:, 0], w[:, 1], dphi, w[:, 4] / p.kms]).astype(np.float32)
	return T.omega(), table, [T.energy(), T.minR(), T.maxR(), T.maxz(), flag]


def build():
	global pot
	pot = p.galpot("PJM16_best")
	if os.path.exists(CACHE):
		c = np.load(CACHE)
		if int(c["version"]) == VERSION:
			print("loaded the galaxy from the cache")
			return {k: c[k] for k in c.files}
	rng = np.random.default_rng(42)
	J, kind = sample_actions(rng)
	print(f"fitting {len(J)} tori on {mp.cpu_count()} cores (only the first time, then its cached)...")
	t0 = time.time()
	with mp.Pool(mp.cpu_count(), initializer=init_worker) as pool:
		res = pool.map(fit_star, J, chunksize=8)
	keep = [i for i, r in enumerate(res) if r is not None]
	print(f"done in {time.time() - t0:.1f}s ({len(J) - len(keep)} fits failed and got dropped)")
	data = {
		"version": VERSION,
		"J": J[keep],
		"kind": kind[keep],
		"omega": np.array([res[i][0] for i in keep]),
		"table": np.array([res[i][1] for i in keep]),
		"info": np.array([res[i][2] for i in keep]),
		"theta0": rng.uniform(0, 2 * np.pi, (len(keep), 3)),
	}
	np.savez(CACHE, **data)
	return data


def quiet(fn):
	# same as init_worker but just while fn runs
	sys.stdout.flush()
	saved, devnull = os.dup(1), os.open(os.devnull, os.O_WRONLY)
	os.dup2(devnull, 1)
	try:
		return fn()
	finally:
		os.dup2(saved, 1)
		os.close(saved)
		os.close(devnull)


def torus_surface(data, k):
	# refits the torus live and maps a fine (theta_R, theta_z) grid, thats the 4d torus
	with fit_lock:
		T = p.Torus()
		t0 = time.time()
		flag = quiet(lambda: T.AutoFit(data["J"][k], pot))
		ms = (time.time() - t0) * 1000
		w = T.Map3D(angle_grid(M))
	return {"M": M, "flag": flag, "ms": ms, "R": w[:, 0].tolist(), "z": w[:, 1].tolist(),
		"vR": (w[:, 3] / p.kms).tolist(), "vz": (w[:, 4] / p.kms).tolist()}


def main():
	data = build()
	meta = json.dumps({
		"n": len(data["J"]), "G": G,
		"omega": data["omega"].tolist(),
		"theta0": data["theta0"].tolist(),
		"kind": data["kind"].tolist(),
		"J": (data["J"] / p.kms).tolist(),
		"info": data["info"].tolist(),
		"sun": int(np.argmax(data["kind"] == 3)),
	}).encode()
	tables = data["table"].astype(np.float32).tobytes()

	class Lab(BaseHTTPRequestHandler):
		def log_message(self, *args):
			pass

		def send(self, body, ctype, code=200):
			self.send_response(code)
			self.send_header("Content-Type", ctype)
			self.send_header("Content-Length", str(len(body)))
			self.end_headers()
			self.wfile.write(body)

		def do_GET(self):
			url = urlparse(self.path)
			if url.path in ("/", "/index.html"):
				with open(os.path.join(HERE, "index.html"), "rb") as f:
					self.send(f.read(), "text/html; charset=utf-8")
			elif url.path == "/api/meta":
				self.send(meta, "application/json")
			elif url.path == "/api/tables":
				self.send(tables, "application/octet-stream")
			elif url.path == "/api/torus":
				k = int(parse_qs(url.query)["id"][0])
				self.send(json.dumps(torus_surface(data, k)).encode(), "application/json")
			else:
				self.send(b"not found", "text/plain", 404)

	print(f"galaxy lab is up, open http://localhost:{PORT} in your browser (ctrl+c to stop)")
	ThreadingHTTPServer(("127.0.0.1", PORT), Lab).serve_forever()


if __name__ == "__main__":
	main()
