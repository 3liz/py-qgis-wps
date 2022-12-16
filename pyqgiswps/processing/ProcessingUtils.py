""" Processing utilities
"""
import os

from lxml import etree
from qgis.core import QgsProcessingAlgorithm
from processing.core.Processing import RenderingStyles


def setLayerVariables(alg, output_name, context, feedback=None, **kwargs):
    """ Set variables to output layers

        Note that this is a style setting
    """
    feedback = feedback or context.feedback
    if isinstance(alg, QgsProcessingAlgorithm):
        alg = alg.id()

    style = RenderingStyles.getStyle(alg, output_name)
    if not style:
        feedback.pushInfo('Style not found for: %s/%s' % (alg, output_name))
        return

    # Read the qml file
    # Check for variable in <customproperties>
    tree = etree.parse(style)
    varnames = tree.find(".//customproperties/property[@key='variableNames']")
    varvalues = tree.find(".//customproperties/property[@key='variableValues']")
    if varnames is None:
        feedback.pushInfo('No variables properties defined in %s' % style)
        return

    variables = {}
    if 'value' in varnames.attrib:
        variables[varnames.attrib.pop('value')] = varvalues.attrib.pop('value')
    else:
        names = (x.text for x in varnames.getchildren())
        values = (x.text for x in varvalues.getchildren())
        variables.update((k, v) for k, v in zip(names, values))
        etree.strip_elements(varnames, 'value')
        etree.strip_elements(varvalues, 'value')

    variables.update(kwargs)

    if len(variables) == 1:
        k, v = next((k, v) for k, v in variables.items())
        varnames.attrib['value'] = k
        varvalues.attrib['value'] = str(v)
    else:
        for k, v in variables.items():
            etree.SubElement(varnames, "value").text = k
            etree.SubElement(varvalues, "value").text = str(v)

    # Save data
    output_file = os.path.join(context.workdir, output_name + '.qml')
    feedback.pushInfo('Saving style file %s' % output_file)
    with open(output_file, 'w') as fp:
        fp.write(etree.tostring(tree, encoding="unicode"))
