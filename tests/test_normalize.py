import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.core.normalize import normalize_mikrotik_export


class NormalizeMikroTikExportTests(unittest.TestCase):
    def test_preserves_backup_metadata_block(self) -> None:
        text = """# backup_metadata
# device: r1
# vendor: mikrotik
# backup_time: 2026-01-06_224908

/interface bridge
add name=bridge1
"""

        self.assertEqual(
            "# backup_metadata\n# device: r1\n# vendor: mikrotik\n# backup_time: 2026-01-06_224908\n\n/interface bridge\nadd name=bridge1",
            normalize_mikrotik_export(text),
        )

    def test_preserves_comments_and_trims_blank_lines(self) -> None:
        text = "# 2026-01-07 00:49:07 by RouterOS 7.19\r\n# software id = ABCD-1234  \r\n/ip address\r\nadd address=10.0.0.1/24 interface=ether1  \r\n\r\n\r\n"

        self.assertEqual(
            "# 2026-01-07 00:49:07 by RouterOS 7.19\n# software id = ABCD-1234\n/ip address\nadd address=10.0.0.1/24 interface=ether1",
            normalize_mikrotik_export(text),
        )


if __name__ == "__main__":
    unittest.main()
