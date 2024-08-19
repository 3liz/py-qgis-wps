.PHONY: test
# 
# qypws makefile
#
DEPTH=.

include $(DEPTH)/config.mk

BUILDDIR:=build
DIST:=${BUILDDIR}/dist

MANIFEST=pyqgiswps/build.manifest

PYTHON_PKG=pyqgiswps pyqgisservercontrib

TESTDIR=tests/unittests

dirs:
	mkdir -p $(DIST)

version:
	echo $(VERSION_TAG) > VERSION

manifest: version
	echo name=$(shell $(PYTHON) setup.py --name) > $(MANIFEST) && \
    echo version=$(shell $(PYTHON) setup.py --version) >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST)

deliver:
	twine upload -r storage $(DIST)/*

dist: dirs manifest
	rm -rf *.egg-info
	$(PYTHON) setup.py sdist --dist-dir=$(DIST)

clean:
	rm -rf $(DIST) *.egg-info


test: lint
	make -C tests test PYTEST_ADDOPTS=$(PYTEST_ADDOPTS)

install:
	pip install -U --upgrade-strategy=eager -e .

install-tests:
	pip install -U --upgrade-strategy=eager -r tests/requirements.txt

install-doc:
	pip install -U --upgrade-strategy=eager -r doc/requirements.txt

install-dev: install-tests install-doc

lint:
	@ruff check --output-format=concise $(PYTHON_PKG) $(TESTDIR)

lint-preview:
	@ruff check --preview $(PYTHON_PKG) $(TESTDIR)

lint-fix:
	@ruff check --preview --fix $(PYTHON_PKG) $(TESTDIR)

typing:
	mypy --config=$(tosrcdir)/mypy.ini -p pyqgiswps


# Run tests with docker-test
test-%:
	$(MAKE) -C tests $* FLAVOR=$(FLAVOR)

run: manifest
	$(MAKE) -C tests run FLAVOR=$(FLAVOR)

client-test:
	cd tests/clienttests && pytest -v $(PYTEST_ADDOPTS)

