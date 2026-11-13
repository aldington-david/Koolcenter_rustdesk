"""Run with python3 -m unittest discover -s tests -v on Linux (BusyBox required)."""

import os
from pathlib import Path
import shlex
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rustdesk-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.koolshare = self.root / "koolshare"
        self.data = self.koolshare / "configs/rustdesk"
        self.data.mkdir(parents=True)
        for directory in ("bin", "scripts", "perp", "init.d", "res", "webs"):
            (self.koolshare / directory).mkdir()
        (self.root / "upload").mkdir()
        (self.root / "mounts").write_text(
            "/dev/sda1 /tmp/mnt/sda1 ext4 rw,relatime 0 0\n"
            "/dev/sda1 /jffs ext4 rw,relatime 0 0\n"
        )

    def mapped(self, source):
        return (source.replace("/koolshare", str(self.koolshare))
                .replace("/tmp/upload", str(self.root / "upload"))
                .replace("/proc/mounts", str(self.root / "mounts")))

    def shell(self, body, *, installer=False):
        if installer:
            source = (ROOT / "rustdesk/install.sh").read_text()
            source = source[source.index("get_model() {"):source.rindex("\ninstall\n")]
            source = source.replace("/tmp/${module}", str(self.root / "package"))
        else:
            source = (ROOT / "rustdesk/scripts/rustdesk_config.sh").read_text()
            source = source[source.index("set_lock() {"):source.index("\ncase $1 in\n")]
        prelude = f"""
echo_date() {{ echo "$@"; }}
dbus() {{ echo "$*" >> {shlex.quote(str(self.root / 'dbus.log'))}; }}
sync() {{ :; }}
uname() {{ echo 4.1.52; }}
df() {{ printf 'Filesystem Size Used Available Use%% Mounted on\\n/dev/sda1 117G 2G 115G 2%% /tmp/mnt/sda1\\n'; }}
mount() {{ printf '/dev/sda1 on /tmp/mnt/sda1 type ext4 (rw)\\n/tmp/mnt/sda1/.koolshare_jffs on /jffs type ext4 (rw,bind)\\n'; }}
rustdesk_db_flie_path={shlex.quote(str(self.data) + '/')}
hbbsCMD={shlex.quote(str(self.koolshare / 'bin/hbbs'))}
hbbrCMD={shlex.quote(str(self.koolshare / 'bin/hbbr'))}
hbbs_used_port=21116
ALWAYS_USE_RELAY=N
bin_all_run=1
DIR={shlex.quote(str(self.root / 'package'))}
module=rustdesk
"""
        return subprocess.run(
            ["busybox", "ash"], input=prelude + self.mapped(source) + "\n" + body,
            text=True, capture_output=True, timeout=15, cwd=self.root,
        )

    def test_usb_bind_mount_hidden_by_df_can_start(self):
        result = self.shell('start_jffs_test start || exit $?; echo START_ALLOWED')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("START_ALLOWED", result.stdout)
        self.assertNotIn("jffs分区不支持db文件读写", result.stdout)

    def test_extra_usb_mounts_do_not_block_start(self):
        result = self.shell("""
df() { echo '/dev/sda1 117G 2G 115G 2% /jffs'; }
mount() { printf '/dev/sda1 on /tmp/mnt/sda1 type ext4 (rw)\\n/dev/sda1 on /jffs type ext4 (rw)\\n/dev/sda1 on /opt type ext4 (rw)\\n/dev/sda1 on /tmp/mnt/extra type ext4 (rw)\\n'; }
start_jffs_test start || exit $?
echo START_ALLOWED
""")
        self.assertIn("START_ALLOWED", result.stdout)

    def test_native_jffs2_on_kernel_4_1_stays_protected(self):
        (self.root / "mounts").write_text("/dev/mtdblock9 /jffs jffs2 rw 0 0\n")
        result = self.shell('start_jffs_test start || exit $?; echo START_ALLOWED')
        self.assertNotIn("START_ALLOWED", result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usb2jffs", result.stdout.lower())

    def test_directory_failure_stops_start_before_process_launch(self):
        blocked = self.root / "file-not-directory"
        blocked.write_text("keep")
        result = self.shell(f"""
uname() {{ echo 4.19.183; }}
rustdesk_db_flie_path={shlex.quote(str(blocked) + '/')}
configServerEnv() {{ :; }}
stop_process() {{ :; }}
check_port_used() {{ :; }}
start_process() {{ echo PROCESSES_STARTED; }}
close_port() {{ :; }}
open_port() {{ :; }}
start
""")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("PROCESSES_STARTED", result.stdout)
        self.assertEqual(blocked.read_text(), "keep")

    def test_newer_kernel_keeps_existing_native_jffs2_support(self):
        (self.root / "mounts").write_text("/dev/mtdblock9 /jffs jffs2 rw 0 0\n")
        result = self.shell('uname() { echo 4.19.183; }; start_jffs_test start || exit $?; echo START_ALLOWED')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("START_ALLOWED", result.stdout)

    def test_status_returns_both_processes_in_one_response(self):
        result = self.shell("""
rustdesk_enable=1
pidof() { echo 123; }
http_response() { [ "$#" -eq 1 ] || exit 1; printf '%s' "$1"; }
check_status
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hbbs 进程运行正常", result.stdout)
        self.assertIn("hbbr 进程运行正常", result.stdout)

    def test_launchers_set_persistent_home_and_config(self):
        result = self.shell("""
perpctl() { :; }
detect_running_status() { :; }
start_hbbs
start_hbbr
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("hbbs", "hbbr"):
            launcher = (self.koolshare / f"perp/{name}/rc.main").read_text()
            self.assertIn('export HOME="', launcher)
            self.assertIn('export XDG_CONFIG_HOME="', launcher)
            self.assertIn("|| exit 1", launcher)

    @unittest.skipUnless(shutil.which("qemu-arm"), "Install qemu-user to test the ARM server binaries")
    def test_arm_servers_use_launchers_and_keep_existing_data(self):
        (self.koolshare / "scripts/base.sh").write_text("")
        for name in ("hbbs", "hbbr"):
            binary = ROOT / f"rustdesk/bin/{name}"
            version = subprocess.check_output(["qemu-arm", str(binary), "--version"], text=True)
            self.assertEqual(version.strip(), f"{name} 1.1.16")
            wrapper = self.koolshare / f"bin/{name}"
            wrapper.write_text(f'#!/bin/sh\nexec qemu-arm {shlex.quote(str(binary))} "$@"\n')
            wrapper.chmod(0o755)

        keys = subprocess.check_output(
            ["qemu-arm", str(ROOT / "rustdesk/bin/rustdesk-utils"), "genkeypair"], text=True
        ).splitlines()
        public, private = (line.split()[-1] for line in keys)
        for filename, value in (("id_ed25519", private), ("id_ed25519.pub", public)):
            (self.data / filename).write_text(value)
        database = self.data / "db_v2.sqlite3"
        with sqlite3.connect(database) as db:
            db.execute("CREATE TABLE upgrade_check (value TEXT)")
            db.execute("INSERT INTO upgrade_check VALUES ('keep-existing-data')")

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        result = self.shell(f"""
perpctl() {{ :; }}
detect_running_status() {{ :; }}
rustdesk_hbbs_port={port}
rustdesk_is_encrypted=1
configServerEnv
start_jffs_test start || exit $?
start_hbbs
start_hbbr
""")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bad_home = self.root / "invalid-home"
        bad_home.write_text("not a directory")
        env = dict(os.environ, HOME=str(bad_home), XDG_CONFIG_HOME=str(bad_home / ".config"))
        processes = []
        try:
            for name in ("hbbs", "hbbr"):
                processes.append(subprocess.Popen(
                    ["busybox", "ash", str(self.koolshare / f"perp/{name}/rc.main"), "start"],
                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                ))
            deadline = time.monotonic() + 15
            ready = False
            logs = []
            while time.monotonic() < deadline:
                log_paths = [self.root / f"upload/rustdesk_{name}_run_log.txt" for name in ("hbbs", "hbbr")]
                logs = [path.read_text() if path.exists() else "" for path in log_paths]
                if any(process.poll() is not None for process in processes):
                    break
                try:
                    for number in range(port - 1, port + 4):
                        with socket.create_connection(("127.0.0.1", number), timeout=.1):
                            pass
                    ready = all("Start" in log for log in logs)
                except OSError:
                    pass
                if ready:
                    break
                time.sleep(.1)
            self.assertTrue(ready, "\n".join(logs))
            self.assertTrue(all("Failed to store" not in log for log in logs), "\n".join(logs))
            self.assertTrue(list((self.data / ".config").rglob("*.toml")))
        finally:
            for process in processes:
                process.terminate()
                process.wait(timeout=5)
        self.assertEqual((self.data / "id_ed25519").read_text(), private)
        self.assertEqual((self.data / "id_ed25519.pub").read_text(), public)
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute("SELECT value FROM upgrade_check").fetchone()[0], "keep-existing-data")
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def make_install_package(self):
        package = self.root / "package"
        for directory in ("bin", "scripts", "res", "webs"):
            (package / directory).mkdir(parents=True)
            (package / directory / "fixture").write_text("fixture")
        (package / "version").write_text("1.4.9")
        (package / "uninstall.sh").write_text("#!/bin/sh\n")
        for name in ("hbbs", "hbbr", "rustdesk-utils"):
            (package / f"bin/{name}").write_text(
                "#!/bin/sh\ncase $1 in\n--version) echo 'server 1.1.16';;\n"
                "genkeypair) printf 'Public Key: generated-public\\nSecret Key: generated-private\\n';;\nesac\n"
            )

    def test_upgrade_keeps_disk_keys_and_database(self):
        self.make_install_package()
        (self.data / "id_ed25519").write_text("disk-private")
        (self.data / "id_ed25519.pub").write_text("disk-public")
        (self.data / "db_v2.sqlite3").write_bytes(b"existing-database")
        result = self.shell("""
dbus() {
  if [ "$1" = get ]; then
    case $2 in
      rustdesk_enable) echo 0;;
      rustdesk_key_priv) echo stale-private;;
      rustdesk_key_pub) echo stale-public;;
    esac
  else
    echo "$*" >> dbus.log
  fi
}
exit_install() { :; }
install_now
""", installer=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.data / "id_ed25519").read_text(), "disk-private")
        self.assertEqual((self.data / "id_ed25519.pub").read_text(), "disk-public")
        self.assertEqual((self.data / "db_v2.sqlite3").read_bytes(), b"existing-database")
        self.assertIn("rustdesk_key_pub=disk-public", (self.root / "dbus.log").read_text())


if __name__ == "__main__":
    unittest.main()
