import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.core.normalize import normalize_mikrotik_export


class NormalizeMikroTikExportTests(unittest.TestCase):
    def test_strips_backup_metadata_block(self) -> None:
        text = """# backup_metadata
# device: r1
# vendor: mikrotik
# backup_time: 2026-01-06_224908

/interface bridge
add name=bridge1
"""

        self.assertEqual(
            "/interface bridge\nadd name=bridge1",
            normalize_mikrotik_export(text),
        )

    def test_strips_routeros_timestamp_comment(self) -> None:
        text = """# 2026-01-07 00:49:07 by RouterOS 7.19
# software id = ABCD-1234
/ip address
add address=10.0.0.1/24 interface=ether1
"""

        self.assertEqual(
            "# software id = ABCD-1234\n/ip address\nadd address=10.0.0.1/24 interface=ether1",
            normalize_mikrotik_export(text),
        )

    def test_preserves_other_comments_and_trims_blank_lines(self) -> None:
        text = """# custom note
/ip firewall filter
add action=accept chain=input comment="allow management"


"""

        self.assertEqual(
            "# custom note\n/ip firewall filter\nadd action=accept chain=input comment=\"allow management\"",
            normalize_mikrotik_export(text),
        )


if __name__ == "__main__":
    unittest.main()
