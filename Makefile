.PHONY: test
# 
# qypws makefile
#

VERSION:=1.8.7

ifndef CI_COMMIT_TAG
VERSION_TAG=$(VERSION)rc0
else
VERSION_TAG=$(VERSION)
endif

BUILDID=$(shell date +"%Y%m%d%H%M")
COMMITID=$(shell git rev-parse --short HEAD)

BUILDDIR:=build
DIST:=${BUILDDIR}/dist

MANIFEST=pyqgiswps/build.manifest

PYTHON:=python3

dirs:
	mkdir -p $(DIST)

version:
	echo $(VERSION_TAG) > VERSION

manifest: version
	echo name=$(shell $(PYTHON) setup.py --name) > $(MANIFEST) && \
    echo version=$(shell $(PYTHON) setup.py --version) >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST)

# Build dependencies
deps: dirs
	pip wheel -w $(DIST) -r requirements.txt

wheel: deps
	mkdir -p $(DIST)
	$(PYTHON) setup.py bdist_wheel --dist-dir=$(DIST)

deliver:
	twine upload -r storage $(DIST)/*

dist: dirs manifest
	rm -rf *.egg-info
	$(PYTHON) setup.py sdist --dist-dir=$(DIST)

clean:
	rm -rf $(DIST) *.egg-info


FLAVOR:=release

# Run tests with docker-test
test-%:
	$(MAKE) -C tests $* FLAVOR=$(FLAVOR)

lint:
	@flake8 --ignore=I pyqgiswps pyqgisservercontrib

test: lint manifest test-test

run: manifest
	$(MAKE) -C tests run FLAVOR=$(FLAVOR)

client-test:
	cd tests/clienttests && pytest -v $(PYTEST_ADDOPTS)

