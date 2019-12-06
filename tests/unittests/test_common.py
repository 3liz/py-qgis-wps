
import os
import pytest

#
# Disable asynchronous tests if running with FAKEREDIS
#
# Use as decorator for tests requiring asynchronous
# Execution
async_test = pytest.mark.skipif(os.getenv('FAKEREDIS','').lower() in ('y','yes','1'), reason="Async test disabled")

