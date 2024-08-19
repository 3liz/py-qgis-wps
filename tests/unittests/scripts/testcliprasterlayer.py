import processing

from qgis.processing import alg


@alg(name='testcliprasterlayer', label='Test Clip Raster Layer', group='test', group_label='Test scripts')
@alg.input(type=alg.RASTER_LAYER, name='INPUT', label='Raster Layer')
@alg.input(type=alg.EXTENT, name='EXTENT', label='Clip Extent')
@alg.input(type=alg.RASTER_LAYER_DEST, name='OUTPUT', label='Clipped Layer')
def testcliprasterlayer(instance, parameters, context, feedback, inputs):
    """
    This is a test function for clip raster layer
    """
    output = instance.parameterAsOutputLayer(parameters, 'OUTPUT', context)

    # Run clip
    _clip_result = processing.run("gdal:cliprasterbyextent", {
        'INPUT': parameters['INPUT'],
        'PROJWIN': parameters['EXTENT'],
        'NODATA': None,
        'OPTIONS': '',
        'DATA_TYPE': 0,
        'OUTPUT': output,
    }, context=context, feedback=feedback)

    return {'OUTPUT': output}
