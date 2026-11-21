"""Errors in PytTorus._torus must raise Python exceptions, not end the interpreter.

The C++ code used to call exit() on bad input, which ended the Python process
(or a Jupyter kernel) without raising anything. Each risky call here runs in a
fresh interpreter, so a regression shows up as a failing test instead of
killing the pytest process along with it.
"""
import json
import os
import pickle
import signal
import subprocess
import sys

import pytest

try:
    import PytTorus
    from PytTorus import _torus as t
except ImportError as exc:  # pragma: no cover
    raise ImportError("Build the extension first: python setup.py build_ext --inplace") from exc

# Make the child interpreters import the same PytTorus as this one.
_PACKAGE_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(PytTorus.__file__)))
_CHILD_ENV = dict(
    os.environ,
    PYTHONPATH=os.pathsep.join(filter(None, [_PACKAGE_PARENT, os.environ.get("PYTHONPATH")])),
)

# Runs the code in argv[1], then prints a JSON line saying whether and what it
# raised. Code that defines `result` reports its repr.
_CHILD = r'''
import json, sys, types
import PytTorus._torus as t

def matrix(rows):
    m = t.Matrix(len(rows), len(rows[0]))
    for i, row in enumerate(rows):
        m.set_row(i, t.Vector(row))
    return m

def spline_table():
    return t.Vector([0.0, 1.0, 2.0]), t.Vector([0.0, 1.0, 4.0]), t.Vector([0.0, 0.0, 0.0])

def nan_inside(x):
    # f(0) < 0 < f(1), so a root is bracketed, but f is NaN in between: rtsafe cannot converge.
    return (-1.0, 1.0) if x == 0.0 else (1.0, 1.0) if x == 1.0 else (float("nan"), 1.0)

def step(x):
    # A discontinuity, so qbulir cannot reach a tight tolerance.
    return 1.0 if x > 1.0 / 3.0 else 0.0

namespace = dict(globals())
try:
    exec(sys.argv[1], namespace)
except Exception as exc:
    outcome = {"raised": type(exc).__name__, "bases": [c.__name__ for c in type(exc).__mro__],
               "message": str(exc), "msgs": getattr(exc, "msgs", None), "index": getattr(exc, "index", None)}
else:
    outcome = {"raised": None, "result": repr(namespace.get("result"))}
print(json.dumps(outcome))  # only reached if the interpreter survived
'''


def run_isolated(code):
    """Run code in a fresh interpreter; fail if that interpreter dies, else report what was raised."""
    proc = subprocess.run([sys.executable, "-c", _CHILD, code], capture_output=True, text=True,
                          timeout=120, env=_CHILD_ENV)
    if proc.returncode < 0:
        how = f"was killed by {signal.Signals(-proc.returncode).name}"
    else:
        how = f"exited with status {proc.returncode}"
    assert proc.returncode == 0 and proc.stdout.strip(), (
        f"the interpreter did not survive {code!r}: it {how}\nstderr:\n{proc.stderr}")
    outcome = json.loads(proc.stdout.strip().splitlines()[-1])
    outcome["stderr"] = proc.stderr
    return outcome


def assert_raises(code, exc_name, message):
    outcome = run_isolated(code)
    assert outcome["raised"] == exc_name, outcome
    assert message in outcome["message"], outcome
    return outcome


# The three calls that used to end the interpreter.

def test_ln_of_negative_number_raises_value_error():
    assert_raises("t.ln(-1.0)", "ValueError", "ln() of argument <= 0")


def test_rtsafe_without_bracketed_root_raises_value_error():
    assert_raises("t.rtsafe(lambda x: (x*x + 1.0, 2.0*x), 0.0, 1.0, 1e-8)",
                  "ValueError", "root must be bracketed")


def test_torus_error_raises_torus_except():
    outcome = assert_raises('t.TorusError("boom", -1)', "TorusExcept", "boom")
    assert "RuntimeError" in outcome["bases"]
    assert outcome["msgs"] == "boom"
    assert outcome["index"] == -1


def test_interpreter_keeps_working_after_errors():
    # As in a notebook: one interpreter hits several errors and carries on.
    code = """
caught = []
for call in (lambda: t.ln(-1.0),
             lambda: t.rtsafe(lambda x: (x*x + 1.0, 2.0*x), 0.0, 1.0, 1e-8),
             lambda: t.TorusError("boom", -1)):
    try:
        call()
    except Exception as e:
        caught.append(type(e).__name__)
result = (caught, t.ln(1.0))
"""
    outcome = run_isolated(code)
    assert outcome["raised"] is None, outcome
    assert outcome["result"] == "(['ValueError', 'ValueError', 'TorusExcept'], 0.0)"


# Other error paths: they called exit(1), crashed with SIGFPE, or printed an
# error and then returned -1 or a meaningless result.

@pytest.mark.parametrize("code, message", [
    # Torus MathError()
    ("t.ld(0.0)", "ld() of argument <= 0"),
    ("t.lg(-2.0)", "lg() of argument <= 0"),
    ("t.LogGamma(-2.0)", "LogGamma called at z = -n"),
    ("t.GammaP(-1.0, 1.0)", "invalid arguments in GammaP()"),
    ("t.Jn(-1, 1.0)", "negative n in Jn(x)"),
    ("t.Y0(-1.0)", "negative argument in Y0(x)"),
    ("t.MathError('my message')", "error in Mathematics: my message"),
    # Root finders
    ("t.rtsafe(None, lambda x: types.SimpleNamespace(f=x*x + 1.0, df=2.0*x), 0.0, 1.0, 1e-8)",
     "root must be bracketed"),
    ("t.zbrent(lambda x: x*x + 1.0, 0.0, 1.0, 1e-8)", "root must be bracketed"),
    # Table lookup, interpolation, quadrature
    ("t.find(0, 4, t.Vector([0, 1, 2, 3]), 10)", "x out of range"),
    ("t.find(0, 4, t.Vector([1, 1, 1, 1]), 5)", "x[0] == x[n-1]"),  # was SIGFPE
    ("t.find_for_polev(0, 4, 2, t.Vector([1, 1, 1, 1]), 5)", "x[0] == x[n-1]"),  # was SIGFPE
    ("t.polint(t.Vector([1.0, 1.0]), t.Vector([1.0, 2.0]), 2, 0.5, 0.0, 0.0)", "not distinct"),
    ("t.qsplin(*spline_table(), 3, 0.0, 0.5, 5.0)", "x2 not in range"),
    ("t.qsplin(*spline_table(), 3, 0.0, 1.5, 0.5)", "x1 > x2"),
    ("t.qsplin(*spline_table(), 3, -1.0, 0.0, 1.0)", "integral diverging"),
    ("t.gauss_fit(0.0, t.Vector([1.0, 0.0, 1.0]), t.Vector([0.0, 0.0, 0.0]), 2)", "D must be 3"),
    # Linear algebra (these returned -1)
    ("t.CholeskyDecomposition(matrix([[1.0, 2.0], [2.0, 1.0]]), 2)", "not positive definite"),
    ("t.LUDecomposition(matrix([[0.0, 0.0], [1.0, 2.0]]), 2, t.Vector([0, 0]), 1)", "singular matrix"),
    ("t.GaussJordan(matrix([[1.0, 2.0], [2.0, 4.0]]), 2, matrix([[1.0], [1.0]]), 1)", "singular matrix"),
    ("t.GaussJordan(matrix([[1.0, 2.0], [2.0, 4.0]]), 2, t.Vector([1.0, 1.0]))", "singular matrix"),
    ("t.GaussBack(matrix([[0.0, 0.0], [0.0, 0.0]]), 2, t.Vector([1.0, 1.0]))", "singular matrix"),
])
def test_bad_input_raises_value_error(code, message):
    assert_raises(code, "ValueError", message)


@pytest.mark.parametrize("code, message", [
    ("t.rtsafe(nan_inside, 0.0, 1.0, 1e-8)", "rtsafe: maximum number of iterations exceeded"),
    ("t.rtsafe(None, lambda x: types.SimpleNamespace(f=nan_inside(x)[0], df=1.0), 0.0, 1.0, 1e-8)",
     "rtsafe: maximum number of iterations exceeded"),
    ("t.qbulir(step, 0.0, 1.0, 1e-10, 0.0)", "qbulir: maximum number of iterations exceeded"),
])
def test_no_convergence_raises_runtime_error(code, message):
    assert_raises(code, "RuntimeError", message)


def test_torus_warning_does_not_raise():
    # A non-negative index is a warning in Torus: it is printed and execution continues.
    outcome = run_isolated('result = t.TorusError("only a warning", 2)')
    assert outcome["raised"] is None, outcome
    assert outcome["result"] == "None"
    assert "WARNING: only a warning" in outcome["stderr"]


@pytest.mark.parametrize("code, expected", [
    ("result = t.CholeskyDecomposition(matrix([[4.0, 12.0, -16.0], [12.0, 37.0, -43.0], [-16.0, -43.0, 98.0]]), 3)", 0),
    ("result = t.LUDecomposition(matrix([[2.0, 1.0], [1.0, 2.0]]), 2, t.Vector([0, 0]), 1)", 0),
    ("result = t.GaussBack(matrix([[2.0, 1.0], [1.0, 3.0]]), 2, t.Vector([1.0, 1.0]))", 0),
    ("result = t.LUDet3(matrix([[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 4.0]]))", 24.0),
    # A row of zeros: LUDecomposition rejects the matrix, but its determinant is simply 0.
    ("result = t.LUDet3(matrix([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0], [4.0, 5.0, 6.0]]))", 0.0),
    ("result = t.rtsafe(lambda x: (x*x - 2.0, 2.0*x), 0.0, 2.0, 1e-12)", 2 ** 0.5),
    ("result = t.zbrent(lambda x: x*x - 2.0, 0.0, 2.0, 1e-12)", 2 ** 0.5),
    ("result = t.qbulir(lambda x: x*x, 0.0, 1.0, 1e-10, 0.0)", 1.0 / 3.0),
    ("result = t.qsplin(*spline_table(), 3, 0.0, 0.5, 1.5)", 1.25),
])
def test_valid_input_still_returns_result(code, expected):
    outcome = run_isolated(code)
    assert outcome["raised"] is None, outcome
    assert float(outcome["result"]) == pytest.approx(expected, rel=1e-9)
    assert "error" not in outcome["stderr"].lower()  # e.g. no "ERROR in Numerics: ..." printed


def test_torus_except_class():
    assert issubclass(t.TorusExcept, RuntimeError)
    exc = t.TorusExcept("GenPar: division by zero", -4)
    assert (exc.msgs, exc.index) == ("GenPar: division by zero", -4)
    assert str(exc) == "GenPar: division by zero (index -4)"
    copy = pickle.loads(pickle.dumps(exc))  # e.g. raised in a multiprocessing worker
    assert type(copy) is t.TorusExcept
    assert (copy.msgs, copy.index) == (exc.msgs, exc.index)
