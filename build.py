#!/usr/bin/env python3
"""Build the Software Center offline package with Python 3."""

import hashlib
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parent


def build_module():
    config_path = ROOT / "config.json.js"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    module = config["module"]
    module_path = ROOT / module
    if not (module_path / "install.sh").is_file():
        raise FileNotFoundError(module_path / "install.sh")
    (module_path / "version").write_text(config["version"], encoding="utf-8")

    def permissions(info):
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mode = 0o755 if info.isdir() or "/bin/" in info.name or info.name.endswith(".sh") else 0o644
        return info

    archive_path = ROOT / f"{module}.tar.gz"
    with tarfile.open(archive_path, "w:gz", format=tarfile.USTAR_FORMAT) as archive:
        archive.add(module_path, arcname=module, filter=permissions)
    # 软件中心使用此字段校验离线包。
    config["md5"] = hashlib.md5(archive_path.read_bytes()).hexdigest()
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=4) + "\n", encoding="utf-8", newline="\n")
    print(f"Built {archive_path.name} ({archive_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build_module()

