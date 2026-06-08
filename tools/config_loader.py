"""Configuration loader for TOML config files."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .config_models import (
    BuildFlags,
    LibraryDef,
    ObjectDef,
    ToolVersions,
    VersionConfig,
    VersionFlags,
)


@dataclass
class MergedConfig:
    """Merged configuration containing tools, build flags, and library definitions."""

    tools: ToolVersions = field(default_factory=ToolVersions)
    build: BuildFlags = field(default_factory=BuildFlags)
    libs: List[LibraryDef] = field(default_factory=list)
    progress_categories: Dict[str, str] = field(default_factory=dict)
    progress_report_args: List[str] = field(default_factory=list)
    version_num: int = 0


class ConfigLoader:
    """Loads and merges TOML configuration files."""

    def __init__(self, config_dir: Path) -> None:
        """Initialize the config loader.

        Args:
            config_dir: Path to the configuration directory.
        """
        self.config_dir = config_dir

    def load_toml(self, path: Path) -> Optional[dict]:
        """Load a TOML file, returning None if it doesn't exist.

        Args:
            path: Path to the TOML file.

        Returns:
            Parsed TOML data as a dictionary, or None if the file doesn't exist.
        """
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return tomllib.load(f)

    def parse_tool_versions(self, data: Optional[dict]) -> ToolVersions:
        """Parse tool versions from TOML data.

        Args:
            data: Parsed TOML data dictionary, or None.

        Returns:
            ToolVersions instance with loaded data.
        """
        if data is None:
            return ToolVersions()

        tools_data = data.get("tools", {})

        # Path overrides
        binutils_path = tools_data.get("binutils_path")
        compilers_path = tools_data.get("compilers_path")
        dtk_path = tools_data.get("dtk_path")
        objdiff_path = tools_data.get("objdiff_path")
        sjiswrap_path = tools_data.get("sjiswrap_path")
        wrapper_path = tools_data.get("wrapper_path")

        return ToolVersions(
            binutils_tag=tools_data.get("binutils_tag", "2.42-1"),
            compilers_tag=tools_data.get("compilers_tag", "20251118"),
            dtk_tag=tools_data.get("dtk_tag", "v1.8.0"),
            objdiff_tag=tools_data.get("objdiff_tag", "v3.5.1"),
            sjiswrap_tag=tools_data.get("sjiswrap_tag"),
            wibo_tag=tools_data.get("wibo_tag"),
            binutils_path=binutils_path,
            compilers_path=compilers_path,
            dtk_path=dtk_path,
            objdiff_path=objdiff_path,
            sjiswrap_path=sjiswrap_path,
            wrapper_path=wrapper_path,
        )

    def parse_build_flags(self, data: Optional[dict]) -> BuildFlags:
        """Parse build flags from TOML data.

        Args:
            data: Parsed TOML data dictionary, or None.

        Returns:
            BuildFlags instance with loaded data.
        """
        if data is None:
            return BuildFlags()

        build_data = data.get("build", {})

        return BuildFlags(
            linker_version=build_data.get("linker_version", "GC/1.2.5n"),
            asflags=build_data.get("asflags", []),
            ldflags=build_data.get("ldflags", []),
            cflags_base=build_data.get("cflags_base", []),
            cflags_runtime=build_data.get("cflags_runtime", []),
            cflags_rel=build_data.get("cflags_rel", []),
            cflags_debug=build_data.get("cflags_debug", []),
            cflags_release=build_data.get("cflags_release", []),
            cflags_warn_all=build_data.get("cflags_warn_all", []),
            cflags_warn_off=build_data.get("cflags_warn_off", []),
            cflags_warn_error=build_data.get("cflags_warn_error", []),
            ldflags_debug=build_data.get("ldflags_debug", []),
            ldflags_map=build_data.get("ldflags_map", []),
        )

    def parse_libraries(self, data: Optional[dict]) -> List[LibraryDef]:
        """Parse library definitions from TOML data.

        Args:
            data: Parsed TOML data dictionary, or None.

        Returns:
            List of LibraryDef instances.
        """
        if data is None:
            return []

        libraries = []
        libs_data = data.get("lib", [])

        for lib_data in libs_data:
            objects = []
            for obj_data in lib_data.get("object", []):
                objects.append(
                    ObjectDef(
                        name=obj_data.get("name", ""),
                        completed=obj_data.get("completed", False),
                        equivalent=obj_data.get("equivalent", False),
                        versions=obj_data.get("versions"),
                        add_to_all=obj_data.get("add_to_all"),
                        cflags=obj_data.get("cflags"),
                        asflags=obj_data.get("asflags"),
                        mw_version=obj_data.get("mw_version"),
                        progress_category=obj_data.get("progress_category"),
                        scratch_preset_id=obj_data.get("scratch_preset_id"),
                        shift_jis=obj_data.get("shift_jis"),
                        source=obj_data.get("source"),
                        src_dir=obj_data.get("src_dir"),
                        extra_cflags=obj_data.get("extra_cflags"),
                        extra_asflags=obj_data.get("extra_asflags"),
                        extra_clang_flags=obj_data.get("extra_clang_flags"),
                    )
                )

            libraries.append(
                LibraryDef(
                    name=lib_data.get("name", ""),
                    mw_version=lib_data.get("mw_version", ""),
                    cflags_preset=lib_data.get("cflags_preset"),
                    progress_category=lib_data.get("progress_category"),
                    cflags_extra=lib_data.get("cflags_extra", []),
                    objects=objects,
                )
            )

        return libraries

    def parse_progress_categories(self, data: Optional[dict]) -> Dict[str, str]:
        """Parse progress categories from TOML data.

        Args:
            data: Parsed TOML data dictionary, or None.

        Returns:
            Dictionary mapping category IDs to category names.
        """
        if data is None:
            return {}

        progress_data = data.get("progress", {})
        categories = progress_data.get("categories", {})
        return categories

    def load_default(self) -> MergedConfig:
        """Load the default configuration.

        Returns:
            MergedConfig with default values loaded from config/default.toml
            and config/libs.toml.
        """
        default_path = self.config_dir / "default.toml"
        data = self.load_toml(default_path)

        # Also load default libraries from config/libs.toml
        libs_path = self.config_dir / "libs.toml"
        libs_data = self.load_toml(libs_path)
        default_libs = self.parse_libraries(libs_data)

        # Parse progress report args
        progress_data = data.get("progress", {})
        progress_report_args = progress_data.get("progress_report_args", [])

        # Parse version_num from [project] section
        project_data = data.get("project", {})
        version_num = project_data.get("version_num", 0)

        return MergedConfig(
            tools=self.parse_tool_versions(data),
            build=self.parse_build_flags(data),
            libs=default_libs,
            progress_categories=self.parse_progress_categories(data),
            progress_report_args=progress_report_args,
            version_num=version_num,
        )

    def load_version(self, version: str, default: MergedConfig) -> MergedConfig:
        """Load version-specific configuration and merge with defaults.

        Args:
            version: The version identifier (e.g., "GAMEID").
            default: The default configuration to merge with.

        Returns:
            MergedConfig with version-specific overrides applied.
        """
        version_dir = self.config_dir / version

        # Load libs.toml for version
        libs_path = version_dir / "libs.toml"
        libs_data = self.load_toml(libs_path)

        # Load flags.toml for version
        flags_path = version_dir / "flags.toml"
        flags_data = self.load_toml(flags_path)

        # Parse version-specific libraries (from libs.toml)
        version_libs = self.parse_libraries(libs_data)

        # Parse version-specific flags (from flags.toml)
        version_flags = VersionFlags(
            cflags_extra=flags_data.get("cflags_extra", []) if flags_data else [],
            ldflags_extra=flags_data.get("ldflags_extra", []) if flags_data else [],
        )

        # Merge libraries: default libs + version libs
        # Version libs can override default libs by name
        merged_libs = default.libs.copy()
        version_lib_dict = {lib.name: lib for lib in version_libs}

        for i, lib in enumerate(merged_libs):
            if lib.name in version_lib_dict:
                version_lib = version_lib_dict[lib.name]
                # Merge: version-specific properties override defaults
                merged_libs[i] = LibraryDef(
                    name=lib.name,
                    mw_version=version_lib.mw_version or lib.mw_version,
                    cflags_preset=version_lib.cflags_preset or lib.cflags_preset,
                    progress_category=version_lib.progress_category or lib.progress_category,
                    cflags_extra=lib.cflags_extra + version_lib.cflags_extra,
                    objects=version_lib.objects or lib.objects,
                )

        # Add any new libraries from version that aren't in defaults
        for lib in version_libs:
            if lib.name not in [l.name for l in merged_libs]:
                merged_libs.append(lib)

        # Merge build flags: default + version-specific extras
        merged_build = BuildFlags(
            linker_version=default.build.linker_version,
            asflags=default.build.asflags.copy(),
            ldflags=default.build.ldflags + version_flags.ldflags_extra,
            cflags_base=default.build.cflags_base.copy(),
            cflags_runtime=default.build.cflags_runtime.copy(),
            cflags_rel=default.build.cflags_rel.copy(),
        )
        merged_build.cflags_base.extend(version_flags.cflags_extra)

        # Progress categories: use default, or override if provided in libs
        merged_progress = default.progress_categories.copy()

        return MergedConfig(
            tools=default.tools,
            build=merged_build,
            libs=merged_libs,
            progress_categories=merged_progress,
            version_num=default.version_num,
        )


def load_config(version: str, config_dir: Path) -> MergedConfig:
    """Convenience function to load and merge configuration.

    Args:
        version: The version identifier (e.g., "GAMEID").
        config_dir: Path to the configuration directory.

    Returns:
        MergedConfig with loaded and merged configuration.
    """
    loader = ConfigLoader(config_dir)
    default_config = loader.load_default()
    return loader.load_version(version, default_config)
