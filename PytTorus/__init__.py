import os

from ._torus import *
from ._torus import TorusError

__version__ = "0.1.0"

# the GalPot potentials that come with torus (McMillan 2011 and 2017, Binney & Tremaine 08 etc)
pot_dir = os.path.join(os.path.dirname(__file__), "pot")


def pot_files():
	return sorted(f[:-5] for f in os.listdir(pot_dir) if f.endswith(".Tpot"))


def galpot(name="PJM16_best"):
	path = os.path.join(pot_dir, name + ".Tpot")
	if not os.path.exists(path):
		raise ValueError(f"no potential called {name}, pick one of {pot_files()}")
	return GalaxyPotential(path)
