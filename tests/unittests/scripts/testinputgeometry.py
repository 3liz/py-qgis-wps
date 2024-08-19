from qgis.core import QgsWkbTypes
from qgis.processing import alg


@alg(name='testinputgeometry', label='test geometry', group='test', group_label='Test scripts')
@alg.output(type=str, name='OUTPUT', label='Output text')
@alg.input(
    type=alg.GEOMETRY,
    name='INPUT',
    label='Vector point',
    geometryTypes=[QgsWkbTypes.PointGeometry],
    help="multipoint",
    allowMultipart=True,
)
def testgeom(instance, parameters, context, feedback, inputs):
    """
    This is a test function that does stuff
    """
    geom = instance.parameterAsGeometry(parameters, 'INPUT', context)
    if geom.isEmpty():
        out = "{}"
    else:
        out = geom.asJson()

    return {
      'OUTPUT': out,
    }
