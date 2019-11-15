#
# Definition to be used in tests
#
from qgis.core import QgsProcessingParameterVectorDestination

#
# Enable settings file extension in
# QgsProcessingParameterVectorDestination
#

class QgsProcessingParameterVectorDestinationEx(QgsProcessingParameterVectorDestination):

    def __init__(self, *args, fileExt=None, **kwargs):
        super().__init__(*args,**kwargs)
        self._fileExt = fileExt

    # Override
    def defaultFileExtension(self) -> str:
        return self._fileExt or super().defaultFileExtension()

