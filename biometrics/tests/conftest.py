"""Test bootstrap: point the service at a throwaway data dir and force the
local-storage fallback before ``config`` (and therefore ``main``) is imported.
"""

import os
import sys
import tempfile
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

os.environ["BIOMETRICS_DATA_DIR"] = tempfile.mkdtemp(prefix="biometrics-test-")
os.environ["BIOMETRICS_ALLOW_LOCAL_STORAGE"] = "1"
os.environ["BIOMETRICS_PRELOAD_MODEL"] = "0"

# Make sure a real R2 config in the ambient environment cannot flip the tests
# onto the network, and that no API key gates the endpoints.
for _name in (
    "MATCH_THRESHOLD",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT_URL",
    "R2_PUBLIC_DOMAIN",
    "BIOMETRICS_API_KEY",
):
    os.environ.pop(_name, None)
