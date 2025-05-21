.PHONY: test
#
# qypws makefile
#
DEPTH=.

include $(DEPTH)/config.mk

DIST:=dist

MANIFEST=pyqgiswps/build.manifest

PYTHON_PKG=pyqgiswps pyqgisservercontrib

TESTDIR=tests/unittests

PYPISERVER:=storage

dirs:
	mkdir -p $(DIST)

version:
	echo $(VERSION_TAG) > VERSION

manifest: version
	echo name=$(PROJECT_NAME) > $(MANIFEST) && \
	echo version=$(VERSION_TAG) >> $(MANIFEST) && \
	echo buildid=$(BUILDID)   >> $(MANIFEST) && \
	echo commitid=$(COMMITID) >> $(MANIFEST)

deliver:
	twine upload $(TWINE_OPTIONS) -r $(PYPISERVER) $(DIST)/*

dist: dirs manifest
	rm -rf *.egg-info
	$(PYTHON) -m build --no-isolation --sdist --outdir=$(DIST)

clean:
	rm -rf $(DIST) *.egg-info


test: lint
	make -C tests test PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)"

install:
	pip install -U --upgrade-strategy=eager -e .

install-dev:
	pip install -U --upgrade-strategy=eager -r requirements.dev

install-doc:
	pip install -U --upgrade-strategy=eager -r doc/requirements.txt

lint:
	@ruff check --output-format=concise $(PYTHON_PKG) $(TESTDIR)

lint-preview:
	@ruff check --preview $(PYTHON_PKG) $(TESTDIR)

lint-fix:
	@ruff check --preview --fix $(PYTHON_PKG) $(TESTDIR)

autopep8: lint-fix

typing:
	mypy --config=$(topsrcdir)/mypy.ini -p pyqgiswps

client-test:
	cd tests/clienttests && pytest -v $(PYTEST_ADDOPTS)

scan:
	@bandit -c pyproject.toml -r pyqgiswps
