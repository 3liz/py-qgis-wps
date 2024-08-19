from qgis.processing import alg


@alg(name='testalgfactory', label='test 2', group='test', group_label='Test scripts')
@alg.input(type=alg.STRING, name="IN1", label='In string')
@alg.input(type=str, name='IN2', label='In string 1', optional=True)
@alg.input(type=str, name='IN3', label='In string 2')
@alg.input(type=alg.SINK, name='SINK', label='Sink it!')
@alg.output(type=str, name='OUT', label='WAT')
def testalg(instance, parms, context, feedback, inputs):
    """
    This is a test function that does stuff
    """
    feedback.pushInfo("We got these inputs!!")
    feedback.pushInfo(inputs['IN1'])
    feedback.pushInfo(inputs['IN2'])
    feedback.pushInfo(inputs['IN3'])
    return {
      'OUT': 'wat',
    }
