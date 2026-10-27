"""Isolate the biometrics test suite from live service state.

The tests import ``biometrics/main.py``, which loads persistent queues and the
face bank from ``BIOMETRICS_DATA_DIR``. Without pointing that at a scratch
directory, running the suite would append mock items to the real
``data/media_store.json`` used by the running service.
"""

import os
import tempfile

os.environ.setdefault(
    "BIOMETRICS_DATA_DIR", tempfile.mkdtemp(prefix="biometrics-root-tests-")
)
