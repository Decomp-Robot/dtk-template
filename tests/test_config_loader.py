"""Configuration must use the toolchain and flags declared in TOML."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.config_loader import load_config
from tools.project import ProjectConfig, load_build_config


TOML = """[project]
default_version = "GAMEID"
version_num = 7

[tools]
binutils_tag = "binutils-test"
compilers_tag = "compilers-test"
dtk_tag = "dtk-test"
objdiff_tag = "objdiff-test"
sjiswrap_tag = "sjiswrap-test"
wibo_tag = "wibo-test"

[build]
linker_version = "GC/2.6"
cflags_base = ["-O4,p"]
cflags_release = ["-DNDEBUG=1"]
cflags_debug = ["-DDEBUG=1"]
cflags_warn_error = ["-W error"]
ldflags_map = ["-mapunused"]

[progress]
progress_report_args = ["--config", "functionRelocDiffs=data_value"]
"""


class ConfigLoaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config_dir = self.root / "config"
        (self.config_dir / "GAMEID").mkdir(parents=True)
        (self.config_dir / "GAMEID" / "config.yml").touch()
        self.default = self.config_dir / "default.toml"
        self.default.write_text(TOML, encoding="utf-8")

    def test_configured_values_survive_version_merge(self):
        config = load_config("GAMEID", self.config_dir)

        self.assertEqual(config.tools.dtk_tag, "dtk-test")
        self.assertEqual(config.tools.wibo_tag, "wibo-test")
        self.assertEqual(config.build.linker_version, "GC/2.6")
        self.assertEqual(config.version_num, 7)
        self.assertEqual(config.build.cflags_base, ["-O4,p"])
        self.assertEqual(config.build.cflags_release, ["-DNDEBUG=1"])
        self.assertEqual(config.build.cflags_debug, ["-DDEBUG=1"])
        self.assertEqual(config.build.cflags_warn_error, ["-W error"])
        self.assertEqual(config.build.ldflags_map, ["-mapunused"])
        self.assertEqual(
            config.progress_report_args, ["--config", "functionRelocDiffs=data_value"],
        )

    def test_missing_required_toml_values_fail(self):
        required = (
            "version_num", "binutils_tag", "compilers_tag", "dtk_tag",
            "objdiff_tag", "sjiswrap_tag", "wibo_tag", "linker_version",
        )
        for name in required:
            with self.subTest(name=name):
                without_value = "\n".join(
                    line for line in TOML.splitlines() if not line.startswith(f"{name} =")
                )
                self.default.write_text(without_value, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, f"default.toml.*{name}"):
                    load_config("GAMEID", self.config_dir)

    def test_missing_default_file_fails(self):
        self.default.unlink()

        with self.assertRaises(FileNotFoundError):
            load_config("GAMEID", self.config_dir)

    def test_missing_default_version_does_not_select_first_directory(self):
        self.default.write_text(
            TOML.replace('default_version = "GAMEID"\n', ''), encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "configure.py")],
            cwd=self.root, capture_output=True, text=True, check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("default_version", result.stderr)

    def test_toml_tool_paths_and_command_line_precedence(self):
        self.default.write_text(
            TOML.replace('wibo_tag = "wibo-test"',
                         'wibo_tag = ""\nwrapper_path = "custom-wrapper"\ndtk_path = "custom-dtk"'),
            encoding="utf-8",
        )
        (self.root / "custom-dtk").touch()
        script = Path(__file__).resolve().parents[1] / "configure.py"

        result = subprocess.run(
            [sys.executable, str(script)], cwd=self.root,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ninja = (self.root / "build.ninja").read_text(encoding="utf-8")
        self.assertIn("custom-wrapper", ninja)
        self.assertIn("custom-dtk", ninja)
        self.assertNotIn("build/tools/wibo", ninja)

        (self.root / "cli-dtk").touch()
        result = subprocess.run(
            [sys.executable, str(script), "--dtk", "cli-dtk", "--wrapper", "cli-wrapper"],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ninja = (self.root / "build.ninja").read_text(encoding="utf-8")
        self.assertIn("cli-wrapper", ninja)
        self.assertIn("cli-dtk", ninja)
        self.assertNotIn("custom-wrapper", ninja)
        self.assertNotIn("custom-dtk", ninja)

    def test_empty_wibo_tag_uses_wine(self):
        self.default.write_text(TOML.replace('wibo_tag = "wibo-test"', 'wibo_tag = ""'),
                                encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "configure.py")],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        ninja = (self.root / "build.ninja").read_text(encoding="utf-8")
        self.assertNotIn("build/tools/wibo", ninja)
        self.assertIn("wine", ninja)
        tools_target = next(line for line in ninja.splitlines() if line.startswith("build tools:"))
        self.assertNotIn(" wine ", f" {tools_target} ")

    def test_custom_dtk_path_with_empty_tag_accepts_generated_config(self):
        path = self.root / "config.json"
        config_data = {"version": "1.8.3", "modules": [], "links": [], "units": []}
        path.write_text(json.dumps(config_data), encoding="utf-8")
        config = ProjectConfig()
        config.dtk_path = self.root / "custom-dtk"
        config.dtk_tag = ""

        self.assertEqual(load_build_config(config, path), config_data)


if __name__ == "__main__":
    unittest.main()
