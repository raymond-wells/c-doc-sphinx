__all__ = [
    "ConfigurationKey",
    "Command",
    "CodeDocument",
]

from enum import Enum
from pprint import pformat
from textwrap import indent
from typing import Any, Sequence, Type, TypeVar


class ConfigurationKey(Enum):
    """
    Names of configuration values used to control aspects of the documentation
    generator.
    """

    OUTPUT_DIRECTORY = "output"
    PROJECT_ROOT = "project_root"
    SOURCE_PATH = "source_location"
    COMPILE_COMMANDS_LOCATION = "compile_commands"
    QUIET = "quiet"
    VERBOSE = "verbose"


T = TypeVar("T")


def autorepr(class_: T) -> T:
    """
    Decorates a slotted class with a `__repr__` method useful for
    debugging.
    """

    def __repr__(self) -> str:
        return "\n".join(
            [
                f"{self.__class__.__name__}(",
                *map(
                    lambda _a: indent(f"{_a}={pformat(getattr(self, _a))},", "    "),
                    self.__class__.__slots__,
                ),
                ")",
            ]
        )

    setattr(
        class_,
        "__repr__",
        __repr__,
    )

    return class_


@autorepr
class Command:
    """
    A compilation command entry within the compile commands manifest.
    """

    __slots__ = ["arguments", "file", "directory", "output"]

    def __init__(
        self, arguments: Sequence[str], file: str, directory: str, output: str
    ):
        self.arguments = arguments
        self.file = file
        self.directory = directory
        self.output = output


@autorepr
class CodeDocument:
    """
    Holds all code documentation extracted from the provided :any:`Command` entry.
    """

    __slots__ = [
        "command",
        "overview",
        "public_interface_files",
    ]

    def __init__(
        self,
        command: Command,
        overview: str,
        public_interface_files: Sequence[str],
    ):
        self.command = command
        self.overview = overview
        self.public_interface_files = public_interface_files
