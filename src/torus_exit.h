// setup.py forces this into every torus file (-include) and swaps exit() for torus_exit()
// torus_exit throws instead of killing python, its defined in src/utils/wrap_err.cpp
#pragma once
[[noreturn]] void torus_exit(int code);
