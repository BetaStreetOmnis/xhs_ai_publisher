"""Keep imported singletons and legacy tests away from real account data."""

import os
import shutil
import tempfile


_test_data_dir = tempfile.mkdtemp(prefix="xhs-pytest-")
os.environ["XHS_DATA_DIR"] = _test_data_dir
os.environ["XHS_APP_DATA_DIR"] = _test_data_dir
os.environ.pop("XHS_WEB_API_TOKEN", None)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_unconfigure(config):
    shutil.rmtree(_test_data_dir, ignore_errors=True)
