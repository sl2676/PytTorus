# Define the default target
all: build_ext

# Define the build_ext target
build_ext:
	python setup.py build_ext -i

# run the tests
test: build_ext
	python -m pytest tests

# Add a clean target for removing the build artifacts
clean:
	rm -rf build
	rm -rf PytTorus/*.so
	rm -rf *.egg-info

.PHONY: all build_ext test clean
