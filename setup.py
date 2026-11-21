import glob
import os
import re
import shutil
import sys

from setuptools import setup, Extension
import pybind11

# torus calls exit() whenever something goes wrong which kills python (and jupyter kernels)
# so we never compile Torus/ directly. we copy the sources we need into build/torus,
# swap every exit() for torus_exit() (it throws, see src/utils/wrap_err.cpp) and build that
# copy instead. the Torus submodule itself never gets touched
TORUS = "Torus/src"
PATCHED = os.path.join("build", "torus")
EBF = "libebf_c_cpp-0.0.3"

torus_sources = [
    "Torus.cc", "Fit.cc", "GeneratingFunction.cc", "Toy_Isochrone.cc",
    "Point_ClosedOrbitCheby.cc", "Point_None.cc", "Orb.cc",
    "pot/IsochronePot.cc", "pot/KeplerPot.cc", "pot/LogPot.cc", "pot/MiyamotoNagaiPot.cc",
    "pot/MultiPot.cc", "pot/StackelPot.cc", "pot/falPot.cc",
    "utils/CHB.cc", "utils/Compress.cc", "utils/Err.cc", "utils/Numerics.cc", "utils/PJMCoords.cc",
    "utils/PJMNum.cc", "utils/PJMebf.cc", "utils/Random.cc", "utils/WDMath.cc", "utils/jjb_utils.cc",
]


def patch_torus():
    if not os.path.exists(os.path.join(TORUS, "Torus.h")):
        sys.exit("Torus/ is empty, run: git submodule update --init")
    for sub in ["", "pot", "utils"]:
        os.makedirs(os.path.join(PATCHED, sub), exist_ok=True)
        for f in glob.glob(os.path.join(TORUS, sub, "*")):
            if not f.endswith((".h", ".cc", ".cpp", ".templates")):
                continue
            with open(f, encoding="latin-1") as src:
                code = src.read()
            code = re.sub(r"\bstd::exit\s*\(", "torus_exit(", code)
            code = re.sub(r"\bexit\s*\(", "torus_exit(", code)
            # register is gone in c++17 (clang errors on it)
            code = re.sub(r"\bregister\s+", "", code)
            out = os.path.join(PATCHED, sub, os.path.basename(f))
            # only write when it changed so we dont rebuild everything every time
            if os.path.exists(out):
                with open(out, encoding="latin-1") as old:
                    if old.read() == code:
                        continue
            with open(out, "w", encoding="latin-1") as dst:
                dst.write(code)
    shutil.copy("src/torus_exit.h", os.path.join(PATCHED, "torus_exit.h"))


patch_torus()

cpp_args = ["-std=c++17", "-O2", "-Wno-register", "-include", os.path.abspath(os.path.join(PATCHED, "torus_exit.h"))]
if sys.platform == "darwin":
    cpp_args += ["-stdlib=libc++"]

ext_modules = [
    Extension(
        "PytTorus._torus",
        ["wrap.cpp"]
        + [os.path.join(PATCHED, f) for f in torus_sources]
        + [os.path.join(EBF, "src/cpp/ebf.cpp"), os.path.join(EBF, "src/cpp/ebftable.cpp")],
        include_dirs=[
            pybind11.get_include(),
            PATCHED,
            os.path.join(PATCHED, "pot"),
            os.path.join(PATCHED, "utils"),
            os.path.join(EBF, "include"),
        ],
        # the wrap files get included into wrap.cpp so setuptools has to be told about them
        depends=glob.glob("src/**/*.cpp", recursive=True) + glob.glob("src/*.h"),
        define_macros=[("EBFLANGOPTCPP", None)],
        language="c++",
        extra_compile_args=cpp_args,
    ),
]

setup(
    name="PytTorus",
    version="0.1.0",
    author="Sean Ly",
    author_email="seanly1101@gmail.com",
    description="Python bindings for the Torus Mapper (Binney & McMillan 2016)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="GPL-2.0",
    ext_modules=ext_modules,
    packages=["PytTorus"],
    package_data={"PytTorus": ["pot/*.Tpot"]},
    python_requires=">=3.8",
    install_requires=["numpy"],
)
