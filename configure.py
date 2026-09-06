#!/usr/bin/env python3
"""
Configuration loader for decompilation projects.
Loads settings from TOML config files.

Usage:
    python3 configure.py
    ninja

Append --help to see available options.
"""

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.config_loader import load_config
from tools.project import (
    Object,
    ProgressCategory,
    ProjectConfig,
    calculate_progress,
    generate_build,
    is_windows,
)


def get_available_versions(config_dir: Path) -> List[str]:
    """Scan config directory for available game versions."""
    versions = []
    if not config_dir.exists():
        return versions
    for entry in config_dir.iterdir():
        if entry.is_dir() and (entry / "config.yml").exists():
            versions.append(entry.name)
    return sorted(versions)


def get_default_version(config_dir: Path) -> Optional[str]:
    """Load default version from config/default.toml."""
    default_path = config_dir / "default.toml"
    if default_path.exists():
        with open(default_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("default_version")
    return None


# Discover available versions from config directory
CONFIG_DIR = Path("config")
AVAILABLE_VERSIONS = get_available_versions(CONFIG_DIR)
DEFAULT_VERSION = get_default_version(CONFIG_DIR) or (AVAILABLE_VERSIONS[0] if AVAILABLE_VERSIONS else "GAMEID")

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "mode",
    choices=["configure", "progress"],
    default="configure",
    help="script mode (default: configure)",
    nargs="?",
)
parser.add_argument(
    "-v",
    "--version",
    type=str.upper,
    choices=AVAILABLE_VERSIONS if AVAILABLE_VERSIONS else None,
    default=None,
    help="version to build" + (f" (available: {', '.join(AVAILABLE_VERSIONS)})" if AVAILABLE_VERSIONS else ""),
)
parser.add_argument(
    "--build-dir",
    metavar="DIR",
    type=Path,
    default=Path("build"),
    help="base build directory (default: build)",
)
parser.add_argument(
    "--binutils",
    metavar="BINARY",
    type=Path,
    help="path to binutils (optional)",
)
parser.add_argument(
    "--compilers",
    metavar="DIR",
    type=Path,
    help="path to compilers (optional)",
)
parser.add_argument(
    "--map",
    action="store_true",
    help="generate map file(s)",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="build with debug info (non-matching)",
)
if not is_windows():
    parser.add_argument(
        "--wrapper",
        metavar="BINARY",
        type=Path,
        help="path to wibo or wine (optional)",
    )
parser.add_argument(
    "--dtk",
    metavar="BINARY | DIR",
    type=Path,
    help="path to decomp-toolkit binary or source (optional)",
)
parser.add_argument(
    "--objdiff",
    metavar="BINARY | DIR",
    type=Path,
    help="path to objdiff-cli binary or source (optional)",
)
parser.add_argument(
    "--sjiswrap",
    metavar="EXE",
    type=Path,
    help="path to sjiswrap.exe (optional)",
)
parser.add_argument(
    "--ninja",
    metavar="BINARY",
    type=Path,
    help="path to ninja binary (optional)",
)
parser.add_argument(
    "--verbose",
    action="store_true",
    help="print verbose output",
)
parser.add_argument(
    "--non-matching",
    dest="non_matching",
    action="store_true",
    help="builds equivalent (but non-matching) or modded objects",
)
parser.add_argument(
    "--warn",
    dest="warn",
    type=str,
    choices=["all", "off", "error"],
    help="how to handle warnings",
)
parser.add_argument(
    "--no-progress",
    dest="progress",
    action="store_false",
    help="disable progress calculation",
)
args = parser.parse_args()

# Determine version
version = args.version or DEFAULT_VERSION

# Load configuration from TOML
toml_config = load_config(version, Path("config"))

# Create project config
config = ProjectConfig()

# Apply tool versions from config
config.binutils_tag = toml_config.tools.binutils_tag
config.compilers_tag = toml_config.tools.compilers_tag
config.dtk_tag = toml_config.tools.dtk_tag
config.objdiff_tag = toml_config.tools.objdiff_tag
config.sjiswrap_tag = toml_config.tools.sjiswrap_tag
config.wibo_tag = toml_config.tools.wibo_tag

# Command-line tool paths override the project TOML settings
config.binutils_path = args.binutils or (Path(toml_config.tools.binutils_path) if toml_config.tools.binutils_path else None)
config.compilers_path = args.compilers or (Path(toml_config.tools.compilers_path) if toml_config.tools.compilers_path else None)
config.dtk_path = args.dtk or (Path(toml_config.tools.dtk_path) if toml_config.tools.dtk_path else None)
config.objdiff_path = args.objdiff or (Path(toml_config.tools.objdiff_path) if toml_config.tools.objdiff_path else None)
config.sjiswrap_path = args.sjiswrap or (Path(toml_config.tools.sjiswrap_path) if toml_config.tools.sjiswrap_path else None)
config.ninja_path = args.ninja

# Version
config.version = version
version_num = toml_config.version_num

# Build settings
config.build_dir = args.build_dir
config.generate_map = args.map
config.non_matching = args.non_matching
config.progress = args.progress
if not is_windows():
    config.wrapper = args.wrapper or (Path(toml_config.tools.wrapper_path) if toml_config.tools.wrapper_path else None)

# Don't build asm unless we're --non-matching
if not config.non_matching:
    config.asm_dir = None

# Project paths
config.config_path = Path("config") / version / "config.yml"
config.check_sha_path = Path("config") / version / "build.sha1"

# Reconfig deps
config.reconfig_deps = []

# Scratch preset
config.scratch_preset_id = None

# Build flags - substitute $VERSION and $VERSION_NUM
version_str = version
version_num_str = str(version_num)

def subst(flags: List[str]) -> List[str]:
    return [f.replace("$VERSION_NUM", version_num_str).replace("$VERSION", version_str) for f in flags]

# Get base cflags from config
cflags_base = list(toml_config.build.cflags_base)

# Add debug/release flags
if args.debug:
    cflags_base.extend(toml_config.build.cflags_debug)
else:
    cflags_base.extend(toml_config.build.cflags_release)

# Add warning flags
if args.warn == "all":
    cflags_base.extend(toml_config.build.cflags_warn_all)
elif args.warn == "off":
    cflags_base.extend(toml_config.build.cflags_warn_off)
elif args.warn == "error":
    cflags_base.extend(toml_config.build.cflags_warn_error)

config.asflags = subst(toml_config.build.asflags)
config.ldflags = subst(toml_config.build.ldflags)
if args.debug:
    config.ldflags.extend(toml_config.build.ldflags_debug)
if args.map:
    config.ldflags.extend(toml_config.build.ldflags_map)

# Get cflags for runtime and REL
cflags_runtime = cflags_base + toml_config.build.cflags_runtime
cflags_rel = cflags_base + toml_config.build.cflags_rel

config.linker_version = toml_config.build.linker_version

# Build library config for project.py
# Map LibraryDef to dict format expected by project.py
config.libs = []
for lib in toml_config.libs:
    # Get appropriate cflags based on preset
    if lib.cflags_preset == "runtime":
        lib_cflags = cflags_runtime
    elif lib.cflags_preset == "rel":
        lib_cflags = cflags_rel
    else:
        lib_cflags = cflags_base

    lib_cflags = subst(lib_cflags + lib.cflags_extra)

    # Filter objects based on version and handle "equivalent" status
    objects = []
    for obj in lib.objects:
        # Skip objects that don't apply to this version
        if obj.versions is not None and version not in obj.versions:
            continue

        # Determine if object should be linked:
        # - completed = True: always link (Matching)
        # - equivalent = True: link only with --non-matching
        # - otherwise: don't link (NonMatching)
        if obj.completed:
            obj_completed = True
        elif obj.equivalent and args.non_matching:
            obj_completed = True  # Link with --non-matching
        else:
            obj_completed = False

        obj_options: Dict[str, Any] = {}
        if obj.add_to_all is not None:
            obj_options["add_to_all"] = obj.add_to_all
        if obj.cflags is not None:
            obj_options["cflags"] = subst(obj.cflags)
        if obj.asflags is not None:
            obj_options["asflags"] = subst(obj.asflags)
        if obj.mw_version is not None:
            obj_options["mw_version"] = obj.mw_version
        if obj.progress_category is not None:
            obj_options["progress_category"] = obj.progress_category
        if obj.scratch_preset_id is not None:
            obj_options["scratch_preset_id"] = obj.scratch_preset_id
        if obj.shift_jis is not None:
            obj_options["shift_jis"] = obj.shift_jis
        if obj.source is not None:
            obj_options["source"] = obj.source
        if obj.src_dir is not None:
            obj_options["src_dir"] = obj.src_dir
        if obj.extra_cflags is not None:
            obj_options["extra_cflags"] = subst(obj.extra_cflags)
        if obj.extra_asflags is not None:
            obj_options["extra_asflags"] = subst(obj.extra_asflags)
        if obj.extra_clang_flags is not None:
            obj_options["extra_clang_flags"] = obj.extra_clang_flags

        objects.append(Object(obj_completed, obj.name, **obj_options))

    lib_config: Dict[str, Any] = {
        "lib": lib.name,
        "mw_version": lib.mw_version,
        "cflags": lib_cflags,
        "progress_category": lib.progress_category or "game",
        "objects": objects
    }
    config.libs.append(lib_config)

# Progress categories
config.progress_categories = [
    ProgressCategory(k, v)
    for k, v in toml_config.progress_categories.items()
]
config.progress_each_module = args.verbose
config.progress_report_args = toml_config.progress_report_args
config.warn_missing_config = True
config.warn_missing_source = False

# Optional callback (keep for backward compat)
# Uncomment and modify as needed
# def link_order_callback(module_id: int, objects: List[str]) -> List[str]:
#     if not config.non_matching:
#         return objects
#     if module_id == 0:  # DOL
#         return objects + ["dummy.c"]
#     return objects
# config.link_order_callback = link_order_callback

# Run in requested mode
if args.mode == "configure":
    generate_build(config)
elif args.mode == "progress":
    calculate_progress(config)
else:
    sys.exit("Unknown mode: " + args.mode)
