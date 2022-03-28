
import os
import pytest

# Use as decorator for tests requiring asynchronous
# Execution
async_test = pytest.mark.skipif(os.getenv('QGSWPS_DISABLE_ASYNC_TEST','').lower() in ('y','yes','1'), reason="Async test disabled")

