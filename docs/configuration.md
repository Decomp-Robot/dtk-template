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
[tools]
binutils_tag = "2.42-1"
compilers_tag = "20251118"
dtk_tag = "v1.8.0"
objdiff_tag = "v3.5.1"
sjiswrap_tag = "v1.2.2"
wibo_tag = "1.0.0"

[build]
linker_version = "GC/1.3.2"

# Assembler flags ($VERSION is replaced at runtime)
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
cflags_preset = "runtime"  # or "base", "rel"
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
cflags_preset = "base"
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

Override flags for specific objects:

```toml
[[lib.object]]
name = "special.c"
completed = true
cflags = ["-extra-flag"]      # Additional cflags
asflags = ["-asm-flag"]        # Additional asflags
mw_version = "GC/1.3.2"        # Different compiler version
```

## {VERSION}/flags.toml

Version-specific flag overrides (these are appended to base flags):

```toml
cflags_extra = ["-DEXTRA_DEFINE"]
ldflags_extra = ["-extra_linker_flag"]
```
