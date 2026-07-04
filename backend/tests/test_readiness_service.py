import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.readiness_service import _contains_write_privilege


class ReadinessServiceTests(unittest.TestCase):
    def test_select_only_grant_is_read_only(self):
        self.assertFalse(_contains_write_privilege(["GRANT SELECT ON default.* TO easydatasus_ro"]))

    def test_write_grant_is_detected(self):
        self.assertTrue(_contains_write_privilege(["GRANT SELECT, INSERT ON default.* TO user"]))


if __name__ == "__main__":
    unittest.main()
