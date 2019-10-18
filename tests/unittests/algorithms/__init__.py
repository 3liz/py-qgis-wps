
from .TestAlgorithmProvider import  TestAlgorithmProvider

class Test:
    def __init__(self):
        pass


def WPSClassFactory( iface: 'WPSServerInterface' ) -> Test:

    iface.registerProvider( TestAlgorithmProvider() )
    return Test()


