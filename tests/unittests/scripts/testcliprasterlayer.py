
from qgis.processing import alg

import processing

@alg(name='testcliprasterlayer', label='Test Clip Raster Layer', group='test', group_label='Test scripts')
@alg.input(type=alg.RASTER_LAYER, name='INPUT', label='Raster Layer')
@alg.input(type=alg.EXTENT, name='EXTENT', label='Clip Extent')
@alg.input(type=alg.RASTER_LAYER_DEST, name='OUTPUT', label='Clipped Layer')
def testcliprasterlayer(instance, parameters, context, feedback, inputs):
    """
    This is a test function for clip raster layer
    """
    try:
        output = instance.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # Run clip
        clip_result = processing.run("gdal:cliprasterbyextent", {
            'INPUT': parameters[self.INPUT],
            'EXTENT': parameters[self.EXTENT],
            'NODATA': None,
            'OPTIONS': '',
            'DATA_TYPE': 0,
            'OUTPUT': output
        }, context=context, feedback=feedback)

        return { 'OUTPUT': output }

    except Exception:
        traceback.print_exc()

