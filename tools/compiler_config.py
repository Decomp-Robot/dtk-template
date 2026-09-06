"""Resolve a candidate's compiler command through the native build configuration."""

import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .project import Object, ProjectConfig


@dataclass
class CompilerOptions:
    mw_version: Optional[str] = None
    cflags: Optional[List[str]] = None
    extra_cflags: Optional[List[str]] = None
    shift_jis: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.mw_version is not None and not isinstance(self.mw_version, str):
            raise ValueError("mw_version must be a string")
        if self.shift_jis is not None and not isinstance(self.shift_jis, bool):
            raise ValueError("shift_jis must be a boolean")
        for flags in (self.cflags, self.extra_cflags):
            if flags is not None and (
                not isinstance(flags, list) or not all(isinstance(flag, str) for flag in flags)
            ):
                raise ValueError("cflags and extra_cflags must be lists of strings")

    @classmethod
    def from_json(cls, value: str) -> "CompilerOptions":
        try:
            return cls(**json.loads(value))
        except TypeError as error:
            raise ValueError("compiler-options accepts mw_version, cflags, extra_cflags, shift_jis") from error

    @classmethod
    def from_object(cls, obj: Object) -> "CompilerOptions":
        return cls(
            mw_version=obj.options["mw_version"], cflags=obj.options["cflags"],
            extra_cflags=obj.options["extra_cflags"], shift_jis=obj.options["shift_jis"],
        )


@dataclass
class CompilerConfiguration:
    mw_version: str
    cflags: List[str]
    extra_cflags: List[str]
    command: List[str]
    cwd: str
    object_options: CompilerOptions

    def to_json(self) -> str:
        result = asdict(self)
        result["object_options"] = {
            key: value for key, value in result["object_options"].items() if value is not None
        }
        return json.dumps(result)


def tool_path(argument: Optional[Path], configured: Optional[str]) -> Optional[Path]:
    if argument is not None:
        return argument
    return Path(configured) if configured else None


def compiler_configuration(
    config: ProjectConfig,
    library_name: str,
    source_name: str,
    fallback_object: Optional[str],
    options: Optional[CompilerOptions],
    substitute: Callable[[List[str]], List[str]],
) -> CompilerConfiguration:
    library = next((lib for lib in config.libs or [] if lib["lib"] == library_name), None)
    if library is None:
        raise ValueError(f"Unknown library: {library_name}")
    obj = next((obj for obj in library["objects"] if obj.name == source_name), None)
    if obj is None:
        fallback = next((obj for obj in library["objects"] if Path(obj.name).with_suffix("").as_posix() == fallback_object), None)
        inherited = CompilerOptions.from_object(fallback) if fallback is not None else CompilerOptions()
        obj = Object(False, source_name, **{
            key: value for key, value in asdict(inherited).items() if value is not None
        })
    accepted = CompilerOptions.from_object(obj)
    if options is not None:
        obj = Object(obj.completed, obj.name, **obj.options)
        for key, value in asdict(options).items():
            if value is not None:
                obj.options[key] = substitute(value) if key in ("cflags", "extra_cflags") else value
    obj = obj.resolve(config, library)
    flags = obj.compile_flags()
    command: List[str] = []
    wrapper = config.compiler_wrapper()
    if wrapper is not None:
        command.append(str(wrapper.resolve()) if wrapper.parent != Path(".") else str(wrapper))
    if obj.options["shift_jis"]:
        if not config.sjiswrap_path and not config.sjiswrap_tag:
            raise ValueError("ProjectConfig.sjiswrap_tag missing")
        command.append(str((config.sjiswrap_path or config.build_dir / "tools/sjiswrap.exe").resolve()))
    command.append(str((config.compilers() / obj.options["mw_version"] / "mwcceppc.exe").resolve()))
    arguments = shlex.split(" ".join(flags))
    for index, argument in enumerate(arguments):
        if argument in ("-i", "-I", "-ir") and index + 1 < len(arguments):
            arguments[index + 1] = str(Path(arguments[index + 1]).resolve())
        elif argument.startswith("-I") and len(argument) > 2:
            arguments[index] = "-I" + str(Path(argument[2:]).resolve())
    command.extend(arguments)
    command.append("-c")
    return CompilerConfiguration(
        mw_version=obj.options["mw_version"], cflags=obj.options["cflags"],
        extra_cflags=obj.options["extra_cflags"], command=command,
        cwd=str(Path.cwd()), object_options=accepted,
    )
