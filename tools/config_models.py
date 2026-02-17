from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ToolVersions:
    """Tool version configuration for decompilation project."""

    binutils_tag: str = "2.42-1"
    compilers_tag: str = "20251118"
    dtk_tag: str = "v1.8.0"
    objdiff_tag: str = "v3.5.1"
    sjiswrap_tag: Optional[str] = None
    wibo_tag: Optional[str] = None

    # Optional path overrides (if None, tools will be downloaded automatically)
    binutils_path: Optional[str] = None
    compilers_path: Optional[str] = None
    dtk_path: Optional[str] = None
    objdiff_path: Optional[str] = None
    sjiswrap_path: Optional[str] = None
    wrapper_path: Optional[str] = None


@dataclass
class BuildFlags:
    """Compiler and linker flags configuration."""

    linker_version: str = "GC/1.2.5n"

    # Assembler and linker flags
    asflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)

    # Base C/C++ flags (applied to all objects)
    cflags_base: List[str] = field(default_factory=list)

    # Runtime-specific C flags
    cflags_runtime: List[str] = field(default_factory=list)

    # REL module C flags
    cflags_rel: List[str] = field(default_factory=list)

    # Debug flags (appended when --debug is used)
    cflags_debug: List[str] = field(default_factory=list)

    # Release flags (appended when not --debug)
    cflags_release: List[str] = field(default_factory=list)

    # Warning flags
    cflags_warn_all: List[str] = field(default_factory=list)
    cflags_warn_off: List[str] = field(default_factory=list)
    cflags_warn_error: List[str] = field(default_factory=list)

    # Linker debug flags (appended when --debug is used)
    ldflags_debug: List[str] = field(default_factory=list)

    # Linker map flags (appended when --map is used)
    ldflags_map: List[str] = field(default_factory=list)


@dataclass
class ObjectDef:
    """Single object file definition with matching status.

    Attributes:
        name: Object file name
        completed: True = Matching (always linked), False = NonMatching (never linked)
        equivalent: True = Equivalent (linked only with --non-matching)
        versions: Optional list of versions where this object exists
                  (if None, exists in all versions)
    """

    name: str
    completed: bool = False
    equivalent: bool = False
    versions: Optional[List[str]] = None
    # Additional options (mirrors Object options in project.py)
    cflags: Optional[List[str]] = None
    asflags: Optional[List[str]] = None
    mw_version: Optional[str] = None
    progress_category: Optional[str] = None
    scratch_preset_id: Optional[int] = None
    shift_jis: Optional[bool] = None
    src_dir: Optional[str] = None


@dataclass
class LibraryDef:
    """Library containing object definitions."""

    name: str
    mw_version: str
    cflags_preset: Optional[str] = None
    progress_category: Optional[str] = None
    cflags_extra: List[str] = field(default_factory=list)
    objects: List[ObjectDef] = field(default_factory=list)


@dataclass
class VersionFlags:
    """Version-specific flag overrides."""

    cflags_extra: List[str] = field(default_factory=list)
    ldflags_extra: List[str] = field(default_factory=list)


@dataclass
class VersionConfig:
    """Configuration for a specific game version."""

    id: str
    linker_version: str
    libs: List[str] = field(default_factory=list)
    flags: VersionFlags = field(default_factory=VersionFlags)


@dataclass
class Config:
    """Root configuration container."""

    tools: ToolVersions = field(default_factory=ToolVersions)
    build_flags: BuildFlags = field(default_factory=BuildFlags)
    libraries: List[LibraryDef] = field(default_factory=list)
    versions: List[VersionConfig] = field(default_factory=list)
    default_version: str = ""
