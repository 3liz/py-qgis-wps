
PROJECT_NAME=py-qgis-wps

BUILDDIR=${shell pwd}/build

main: html

html: build
	mkdir -p ${BUILDDIR}/html
	sphinx-build -b html ./  ${BUILDDIR}/html

pdf: build
	mkdir -p ${BUILDDIR}/latex
	sphinx-build -b latex ./  ${BUILDDIR}/latex
	cd ${BUILDDIR}/latex && pdflatex ${PROJECT_NAME}.tex

md: build
	 mkdir -p ${BUILDDIR}/md
	 sphinx-build -b markdown ./  ${BUILDDIR}/md

build: templates
templates: configuration.rst

configuration.rst: ../pyqgiswps/config.yml configuration.rst.j2
	./jtpl.py -c $^

clean:
	rm -r ${BUILDDIR}

serve:
	python3 -m http.server -d ./build/html

