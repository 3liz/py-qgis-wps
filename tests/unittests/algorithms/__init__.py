from .TestAlgorithmProvider import TestAlgorithmProvider


class Test:
    def __init__(self):
        pass


def WPSClassFactory(iface):

    iface.registerProvider(TestAlgorithmProvider())
    return Test()
