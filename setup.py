import os
import re

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import pybind11

cpp_args = ['-std=c++17', '-stdlib=libc++', '-Wno-register', '-mmacosx-version-min=10.14', '-Wall']

ext_modules = [
    Extension(
        "PytTorus._torus",
        ["wrap.cpp", "./Torus/src/utils/WDMath.cc", "./Torus/src/utils/Compress.cc", "Torus/src/utils/Err.cc", "Torus/src/utils/CHB.cc"],
        include_dirs=[
            pybind11.get_include(),
            "./Torus/src/utils",  # Ensure correct include path
            "./Torus/include",  # Add if headers are in a separate include folder
        ],
        define_macros=[("_exception_handling_", None)],  # see TORUS_PATCH below
        language="c++",
        extra_compile_args=cpp_args,
    ),
]

# Torus reports fatal errors by calling exit(), which would kill the Python
# interpreter. So Torus/src/utils is never compiled as checked out: build_ext
# copies it into the build directory, applies TORUS_PATCH to the copy and
# compiles that with -D_exception_handling_, which makes those errors throw C++
# exceptions instead. The Torus/ checkout itself is not modified. See "Error
# handling" in README.md.
TORUS_UTILS = os.path.join("Torus", "src", "utils")
TORUS_PATCH = os.path.join("patches", "torus-exception-handling.patch")
_HUNK_HEADER = re.compile(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def _read_patch(path):
    """Parse a unified diff into {path within Torus/: [(old_lines, new_lines), ...]}."""
    with open(path, encoding="latin-1") as f:
        lines = f.read().replace("\r\n", "\n").split("\n")
    patches, hunks, i = {}, None, 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith("--- ") and i < len(lines) and lines[i].startswith("+++ "):
            target = lines[i][4:].split("\t")[0]
            hunks = patches.setdefault(target[2:] if target.startswith("b/") else target, [])
            i += 1
            continue
        header = _HUNK_HEADER.match(line)
        if header is None or hunks is None:
            continue  # the description at the top, "diff --git ...", "index ..."
        n_old, n_new = int(header.group(1) or 1), int(header.group(2) or 1)
        old, new = [], []
        while n_old > 0 or n_new > 0:
            if i >= len(lines):
                raise RuntimeError(f"{path}: the last hunk is incomplete")
            tag, text = lines[i][:1], lines[i][1:]
            i += 1
            if tag in (" ", ""):  # context; an empty context line may have lost its space
                old.append(text)
                new.append(text)
                n_old, n_new = n_old - 1, n_new - 1
            elif tag == "-":
                old.append(text)
                n_old -= 1
            elif tag == "+":
                new.append(text)
                n_new -= 1
            elif tag != "\\":  # "\ No newline at end of file"
                raise RuntimeError(f"{path}, line {i}: unexpected line in hunk: {lines[i - 1]!r}")
        hunks.append((old, new))
    return patches


def _apply_hunks(lines, hunks, name):
    """Apply (old_lines, new_lines) hunks to lines; each must match exactly one place."""
    for old, new in hunks:
        at = [k for k in range(len(lines) - len(old) + 1) if lines[k:k + len(old)] == old]
        if len(at) != 1:
            raise RuntimeError(
                f"{TORUS_PATCH} does not apply to Torus/{name}: a hunk matches {len(at)} places. "
                "If the Torus checkout has changed, update the patch to match it (or delete the "
                "patch if Torus now includes the change).")
        lines[at[0]:at[0] + len(old)] = new
    return lines


def _write_if_changed(path, data):
    """Write data to path, but leave the file (and its mtime) alone if it is unchanged."""
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return
    with open(path, "wb") as f:
        f.write(data)


def _patched_torus_utils(build_temp):
    """Copy Torus/src/utils into build_temp, apply TORUS_PATCH there, return the copy's path."""
    if not os.path.isdir(TORUS_UTILS):
        raise RuntimeError(
            f"{TORUS_UTILS} not found: check out https://github.com/PaulMcMillan-Astro/Torus into Torus/")
    patches = _read_patch(TORUS_PATCH)
    dest = os.path.join(build_temp, "torus-patched", "src", "utils")
    os.makedirs(dest, exist_ok=True)
    for name in sorted(os.listdir(TORUS_UTILS)):
        src = os.path.join(TORUS_UTILS, name)
        if not os.path.isfile(src):
            continue
        with open(src, "rb") as f:
            data = f.read()
        hunks = patches.pop("src/utils/" + name, None)
        if hunks:
            lines = data.decode("latin-1").replace("\r\n", "\n").split("\n")
            data = "\n".join(_apply_hunks(lines, hunks, "src/utils/" + name)).encode("latin-1")
        _write_if_changed(os.path.join(dest, name), data)
    if patches:
        raise RuntimeError(f"{TORUS_PATCH} patches files that are not in {TORUS_UTILS}: {sorted(patches)}")
    return dest


class BuildExtWithPatchedTorus(build_ext):
    """build_ext that compiles the patched copy of Torus/src/utils instead of the original."""

    def build_extensions(self):
        patched = _patched_torus_utils(self.build_temp)

        def redirect(path):
            norm = os.path.normpath(path)
            if norm == TORUS_UTILS or norm.startswith(TORUS_UTILS + os.sep):
                return os.path.normpath(os.path.join(patched, os.path.relpath(norm, TORUS_UTILS)))
            return path

        for ext in self.extensions:
            ext.sources = [redirect(p) for p in ext.sources]
            ext.include_dirs = [redirect(p) for p in ext.include_dirs]
        super().build_extensions()


setup(
    name="PytTorus",
    version="0.0.2",
    author="Sean Ly",
    author_email="seanly1101@gmail.com",
    description="Torus library for orbital mechanics",
    ext_modules=ext_modules,
    cmdclass={"build_ext": BuildExtWithPatchedTorus},
    packages=["PytTorus"],
    package_dir={"PytTorus": "PytTorus"},
    python_requires=">=3.7",
    install_requires=["pybind11"],
    package_data={"": ["Torus/src/utils/*.h", "Torus/src/utils/*.templates", "Torus/src/utils/*.cpp"]},  # Ensure headers are included in the package
    include_package_data=True,
)

