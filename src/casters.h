// numpy <-> torus Vector, PSPD, PSPT so everything just takes and gives arrays
// (this replaces my old Vector and Matrix classes, numpy already does all of that)
#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "Vector.h"
#include "Types.h"

namespace py = pybind11;

template<class V>
py::array_t<double> to_numpy(const V& v, int n) {
	py::array_t<double> out(n);
	auto o = out.mutable_unchecked<1>();
	for (int i = 0; i < n; i++) o(i) = v(i);
	return out;
}

template<class V>
bool from_numpy(py::handle src, V& v, int n) {
	auto arr = py::array_t<double, py::array::c_style | py::array::forcecast>::ensure(src);
	if (!arr || arr.ndim() != 1 || arr.shape(0) != n) return false;
	auto a = arr.unchecked<1>();
	for (int i = 0; i < n; i++) v[i] = a(i);
	return true;
}

namespace pybind11 { namespace detail {
	template<int N> struct type_caster<Vector<double, N>> {
		// the macro chokes on the comma in Vector<double, N> so it gets a name first
		using VecN = Vector<double, N>;
		PYBIND11_TYPE_CASTER(VecN, const_name("numpy.ndarray"));
		bool load(handle src, bool) { return from_numpy(src, value, N); }
		static handle cast(const Vector<double, N>& v, return_value_policy, handle) { return to_numpy(v, N).release(); }
	};
	template<> struct type_caster<PSPD> {
		PYBIND11_TYPE_CASTER(PSPD, const_name("numpy.ndarray"));
		bool load(handle src, bool) { return from_numpy(src, value, 4); }
		static handle cast(const PSPD& v, return_value_policy, handle) { return to_numpy(v, 4).release(); }
	};
	template<> struct type_caster<PSPT> {
		PYBIND11_TYPE_CASTER(PSPT, const_name("numpy.ndarray"));
		bool load(handle src, bool) { return from_numpy(src, value, 6); }
		static handle cast(const PSPT& v, return_value_policy, handle) { return to_numpy(v, 6).release(); }
	};
}}
