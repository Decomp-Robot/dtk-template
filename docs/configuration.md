# Configuration

Configuration is stored in TOML files in the `config/` directory.

## File Structure

```
config/
├── default.toml       # Shared base configuration (tool versions, flags, presets)
├── libs.toml         # Default library definitions
└── {VERSION}/
    ├── libs.toml     # Version-specific libraries (adds to defaults)
    ├── flags.toml    # Version-specific flag overrides
    ├── config.yml    # decomp-toolkit config (unchanged)
    └── build.sha1   # Build verification hashes
```

## default.toml

Contains tool versions and build flags shared across all game versions.

```toml
[project]
default_version = "GAMEID"
version_num = 0  # Numeric version for $VERSION_NUM substitution

[tools]
binutils_tag = "2.42-1"
compilers_tag = "20251118"
dtk_tag = "v1.8.0"
objdiff_tag = "v3.5.1"
sjiswrap_tag = "v1.2.2"
wibo_tag = "1.0.0"

[build]
linker_version = "GC/1.3.2"

# Assembler flags ($VERSION and $VERSION_NUM are replaced at runtime)
asflags = [
    "-mgekko",
    "-I build/$VERSION/include",
]

# C flags with presets
cflags_base = [...]
cflags_runtime = [...]  # For runtime libraries
cflags_rel = [...]      # For REL modules

# Debug/Release flags (appended based on --debug)
cflags_debug = [...]
cflags_release = [...]

# Warning flags (set by --warn)
cflags_warn_all = [...]
cflags_warn_off = [...]
cflags_warn_error = [...]

# Linker flags
ldflags = [...]

# Progress categories
[progress.categories]
game = "Game Code"
sdk = "SDK Code"

# objdiff report args
progress_report_args = []
```

## libs.toml

Default library definitions common to all games.

```toml
[[lib]]
name = "Runtime.PPCEABI.H"
mw_version = "GC/1.3.2"
cflags_preset = "runtime"  # "base", "runtime", "rel", or "game"
progress_category = "sdk"

[[lib.object]]
name = "Runtime.PPCEABI.H/global_destructor_chain.c"
completed = false
```

## {VERSION}/libs.toml

Version-specific libraries. These are merged with (and can override) defaults from `config/libs.toml`.

```toml
# Add game-specific libraries
[[lib]]
name = "Game"
mw_version = "GC/1.3.2"
cflags_preset = "game"
progress_category = "game"

[[lib.object]]
name = "main.c"
completed = true
```

## Object Matching Status

Objects can have three matching states:

```toml
# Always linked (Matching)
completed = true

# Never linked (NonMatching)
completed = false

# Linked only with --non-matching flag (Equivalent)
equivalent = true
```

## Version-Specific Objects

Objects can be restricted to specific versions:

```toml
[[lib.object]]
name = "region_specific.c"
completed = true
versions = ["GAMEID_PAL"]  # Only for PAL version
```

## Per-Object Options

Override compilation settings for specific objects. These options are passed
directly to the underlying build system's Object constructor.

```toml
[[lib.object]]
name = "special.c"
completed = true

# Override compiler flags (replaces library-level cflags entirely)
cflags = ["-nodefaults", "-proc gekko", "-O4,p"]

# Additional cflags appended to the library-level cflags
extra_cflags = ["-extra-flag"]

# Additional assembler flags
extra_asflags = ["-asm-flag"]

# Additional flags for clangd/compile_commands.json
extra_clang_flags = ["-Wno-something"]

# Use a different MWCC version for this object
mw_version = "GC/2.7"

# Disable Shift-JIS wrapping (sjiswrap) for this file
# Default is true (inherited from ProjectConfig). Set to false for
# files without Japanese characters to avoid sjiswrap overhead.
shift_jis = false

# Source directory for this object's .c/.cpp files
# Default is config.src_dir (usually "src")
src_dir = "src/sdk"

# Override the source file path (default is same as name)
source = "sdk/audio/output.c"

# Assembler flags override (replaces library-level asflags entirely)
asflags = ["-mgekko", "-I include"]

# Progress category override
progress_category = "sdk"

# decomp.me scratch preset ID
scratch_preset_id = 42

# Whether to add this object to all link units
# Default is true (inherited from ProjectConfig)
add_to_all = false
```

## {VERSION}/flags.toml

Version-specific flag overrides (these are appended to base flags):

```toml
cflags_extra = ["-DEXTRA_DEFINE"]
ldflags_extra = ["-extra_linker_flag"]
```

## Cflags Presets

Libraries specify a `cflags_preset` that determines which base flags are used:

| Preset | Flags Used |
|--------|-----------|
| `"base"` (default) | `cflags_base` + `lib.cflags_extra` |
| `"game"` | `cflags_base` + `lib.cflags_extra` (same as base, explicit for game code) |
| `"runtime"` | `cflags_base` + `cflags_runtime` |
| `"rel"` | `cflags_base` + `cflags_rel` |

## Flag Substitution

The following placeholders in flag arrays are replaced at configure time:

| Placeholder | Replaced With |
|-------------|--------------|
| `$VERSION` | Version string (e.g., `"GXXE01"`) |
| `$VERSION_NUM` | Numeric version from `[project].version_num` |
