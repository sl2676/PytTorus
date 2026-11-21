#include <iostream>
#include <streambuf>
#include <stdexcept>
#include <string>
#include "Err.h"

namespace py = pybind11;

// what torus_exit throws, shows up in python as PytTorus.TorusError
struct TorusFatal : public std::runtime_error {
	using std::runtime_error::runtime_error;
};

// torus always prints why to cerr right before it calls exit()
// so cerr goes through this and we keep the last line for the python error
class ErrTee : public std::streambuf {
public:
	std::streambuf* orig;
	std::string line, last;
	ErrTee() : orig(std::cerr.rdbuf(this)) {}
	~ErrTee() { std::cerr.rdbuf(orig); }
protected:
	int overflow(int c) override {
		if (c == traits_type::eof()) return 0;
		if (c == '\n') {
			if (!line.empty()) last = line;
			line.clear();
		} else {
			line += (char) c;
		}
		return orig->sputc(c);
	}
	int sync() override { return orig->pubsync(); }
};

static ErrTee err_tee;

// every exit() in torus got swapped for this by setup.py
[[noreturn]] void torus_exit(int code) {
	std::string msg = err_tee.line.empty() ? err_tee.last : err_tee.line;
	err_tee.line.clear();
	err_tee.last.clear();
	msg.erase(0, msg.find_first_not_of(" \t"));
	if (msg.empty()) msg = "torus called exit(" + std::to_string(code) + ")";
	throw TorusFatal(msg);
}

void init_err(py::module_ &torus) {
	py::register_exception<TorusFatal>(torus, "TorusError", PyExc_RuntimeError);
	torus.def("toruserrno", []() { return toruserrno; }, "last torus warning code (0 = none)");
}
