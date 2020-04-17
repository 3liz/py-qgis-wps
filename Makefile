.PHONY: test
# 
# qypws makefile
#

BUILDID=$(shell date +"%Y%m%d%H%M")
COMMITID=$(shell git rev-parse --short HEAD)

DIST=docker/dist

MANIFEST=pyqgiswps/build.manifest

PYTHON:=python3

dirs:
	mkdir -p $(DIST)

manifest:
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
	rm -rf $(DIST)


FLAVOR:=ltr

# Run tests with docker-test
docker-%:
	$(MAKE) -C tests $* FLAVOR=$(FLAVOR)

client-test:
	cd tests/clienttests && pytest -v $(PYTEST_ADDOPTS)

