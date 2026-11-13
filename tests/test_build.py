import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build


class BuildTests(unittest.TestCase):
    def test_offline_package_paths_modes_version_and_checksum(self):
        with tempfile.TemporaryDirectory(prefix="rustdesk build ") as directory:
            root = Path(directory)
            module = root / "rustdesk"
            (module / "bin").mkdir(parents=True)
            (module / "install.sh").write_text("#!/bin/sh\n")
            (module / "bin/hbbs").write_bytes(b"binary-fixture")
            (module / ".valid").write_text("hnd\nqca\nmtk\n", newline="\n")
            config_path = root / "config.json.js"
            config_path.write_text(json.dumps({"module": "rustdesk", "version": "1.4.9"}))
            with patch.object(build, "ROOT", root):
                build.build_module()
            archive_path = root / "rustdesk.tar.gz"
            with tarfile.open(archive_path) as archive:
                self.assertTrue(all(name == "rustdesk" or name.startswith("rustdesk/") for name in archive.getnames()))
                self.assertEqual(archive.getmember("rustdesk/install.sh").mode, 0o755)
                self.assertEqual(archive.getmember("rustdesk/bin/hbbs").mode, 0o755)
                self.assertEqual(archive.extractfile("rustdesk/version").read(), b"1.4.9")
                self.assertEqual(archive.extractfile("rustdesk/.valid").read(), b"hnd\nqca\nmtk\n")
            self.assertEqual(json.loads(config_path.read_text())["md5"], hashlib.md5(archive_path.read_bytes()).hexdigest())
            self.assertNotIn(b"\r\n", config_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
