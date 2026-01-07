import logging
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.mikrotik.backup import log_mikrotik_diff


class MikroTikDiffTests(unittest.TestCase):
    def _write_export(self, path: Path, content: str) -> Path:
        path.write_text(content, encoding="utf-8")
        return path

    def test_detects_changes_and_writes_diff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            device_dir = Path(tmpdir) / "mikrotik" / "router1"
            device_dir.mkdir(parents=True, exist_ok=True)

            baseline = self._write_export(
                device_dir / "2026-01-01_000000_export.rsc",
                "/interface bridge\nadd name=bridge1\n",
            )
            current = self._write_export(
                device_dir / "2026-01-02_000000_export.rsc",
                "/interface bridge\nadd name=bridge1\n/system ntp client\nset enabled=yes\n",
            )
            os.utime(baseline, (1, 1))
            os.utime(current, (2, 2))

            logger = logging.getLogger("mikrotik.diff.test")
            outcome, diff_path = log_mikrotik_diff(current, logger, {"device": "router1"})

            self.assertIsNotNone(outcome.previous_path)
            self.assertEqual(baseline.resolve(), outcome.previous_path)
            self.assertTrue(outcome.config_changed)
            self.assertIsNotNone(diff_path)
            self.assertTrue(diff_path.exists())
            self.assertNotEqual(outcome.baseline_sha256, outcome.current_sha256)
            self.assertEqual(current.resolve().parent, diff_path.parent)

    def test_no_change_skips_diff_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            device_dir = Path(tmpdir) / "mikrotik" / "router1"
            device_dir.mkdir(parents=True, exist_ok=True)

            self._write_export(
                device_dir / "2026-01-01_000000_export.rsc",
                "/interface bridge\nadd name=bridge1\n",
            )
            current = self._write_export(
                device_dir / "2026-01-02_000000_export.rsc",
                "/interface bridge\nadd name=bridge1\n",
            )
            os.utime(device_dir / "2026-01-01_000000_export.rsc", (1, 1))
            os.utime(current, (2, 2))

            logger = logging.getLogger("mikrotik.diff.test")
            outcome, diff_path = log_mikrotik_diff(current, logger, {"device": "router1"})

            self.assertFalse(outcome.config_changed)
            self.assertIsNone(diff_path)
            self.assertFalse((current.with_suffix(".diff")).exists())


if __name__ == "__main__":
    unittest.main()
