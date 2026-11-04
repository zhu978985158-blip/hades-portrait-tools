import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()


class InstallerSafety(unittest.TestCase):
    def prepare(self, folder, role, names=("GUI.pkg",)):
        game = folder / "Content/macOS/Packages"
        package = folder / "package"
        game.mkdir(parents=True)
        package.mkdir()
        backup_name = "原版备份" if role == "zagreus" else "安装前备份"
        for name in (backup_name, "安装资源"):
            (package / name).mkdir()
        rows = []
        for name in names:
            original, replacement = ("original:" + name).encode(), ("replacement:" + name).encode()
            (game / name).write_bytes(original)
            (package / backup_name / name).write_bytes(original)
            (package / "安装资源" / name).write_bytes(replacement)
            rows.append(dict(path=name, original_sha256=sha(original), replacement_sha256=sha(replacement)))
        (package / "安装清单.json").write_text(json.dumps(rows))
        script = package / "安装或恢复.py"
        shutil.copy2(REPO / "packages" / role / "安装或恢复.py", script)
        return game, package, rows, script

    def run_installer(self, script, game, mode, processes=""):
        with patch.dict(os.environ, {"HADES_PACKAGES_DIR": str(game)}), patch.object(sys, "argv", [str(script), mode]), patch("subprocess.run", return_value=SimpleNamespace(stdout=processes)), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(script), run_name="__main__")

    def test_install_restore_and_unknown_version(self):
        for role in ("zagreus", "zeus"):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as temp:
                game, package, rows, script = self.prepare(Path(temp), role)
                self.run_installer(script, game, "install")
                self.assertEqual(sha((game / "GUI.pkg").read_bytes()), rows[0]["replacement_sha256"])
                self.run_installer(script, game, "restore")
                self.assertEqual(sha((game / "GUI.pkg").read_bytes()), rows[0]["original_sha256"])
                (game / "GUI.pkg").write_bytes(b"unknown version")
                with self.assertRaises(AssertionError):
                    self.run_installer(script, game, "install")
                self.assertEqual((game / "GUI.pkg").read_bytes(), b"unknown version")

    def test_game_running_and_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            game, package, rows, script = self.prepare(Path(temp), "zeus")
            with self.assertRaises(SystemExit):
                self.run_installer(script, game, "install", "/games/Hades/Game.macOS.app/Contents/MacOS/Game")
            rows[0]["path"] = "../outside.pkg"
            (package / "安装清单.json").write_text(json.dumps(rows))
            with self.assertRaises(AssertionError):
                self.run_installer(script, game, "install")
            self.assertEqual((game / "GUI.pkg").read_bytes(), b"original:GUI.pkg")

    def test_symlink_outside_game_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            game, package, rows, script = self.prepare(folder, "zeus")
            outside = folder / "outside.pkg"
            outside.write_bytes(b"original:GUI.pkg")
            (game / "GUI.pkg").unlink()
            (game / "GUI.pkg").symlink_to(outside)
            with self.assertRaises(AssertionError):
                self.run_installer(script, game, "install")
            self.assertEqual(outside.read_bytes(), b"original:GUI.pkg")

    def test_replace_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            game, package, rows, script = self.prepare(Path(temp), "zeus", ("GUI.pkg", "Other.pkg"))
            actual_replace, calls = os.replace, []
            def fail_second(source, target):
                calls.append(target)
                if len(calls) == 2:
                    raise OSError("synthetic replacement failure")
                return actual_replace(source, target)
            with patch("os.replace", side_effect=fail_second), self.assertRaises(OSError):
                self.run_installer(script, game, "install")
            for row in rows:
                self.assertEqual(sha((game / row["path"]).read_bytes()), row["original_sha256"])
            self.assertFalse(list(game.glob("*.zeus-staging")))


if __name__ == "__main__":
    unittest.main()
