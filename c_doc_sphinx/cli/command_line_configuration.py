__all__ = ["CommandLineConfiguration"]

from argparse import ArgumentParser
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from c_doc_sphinx.model import ConfigurationKey


class CommandLineConfiguration:
    """
    Parses the command line into a configuration mapping for the application,
    handling all of the complex defaulting rules involving project roots, output directories,
    etc.
    """

    def __init__(self):
        parser = ArgumentParser()
        parser.add_argument(
            "-o",
            "--output",
            help="The destination directory to place RST files in. Relative to current working directory.",
            default="",
        )
        parser.add_argument(
            "-r",
            "--project-root",
            help="The root directory containing project files.",
            required=True,
        )
        parser.add_argument(
            "-s",
            "--source-location",
            help="The source directory containing code. If relative, treated as relative to project root.",
            default="src",
        )
        parser.add_argument(
            "--compile-commands",
            help="A custom location for compile_commands.json. If relative, treated as relative to project root.",
            default="compile_commands.json",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            help="Use debug-level logging",
            action="store_true",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            help="Only log warnings and errors. Supercedes verbose mode.",
            action="store_true",
        )
        self._parser = parser

    def parse_argument_list(
        self, args: Sequence[str]
    ) -> Mapping[ConfigurationKey, Any]:
        """
        Parses the given argument list into a configuration mapping.
        """
        raw_result = {
            key: value
            for key, value in self._parser.parse_args(args).__dict__.items()
            if not key.startswith("_")
        }

        project_root = Path(os.path.normpath(raw_result["project_root"])).absolute()

        source_location = Path(raw_result["source_location"])
        if not source_location.is_absolute():
            source_location = project_root.joinpath(source_location)

        compile_commands = Path(raw_result["compile_commands"])
        if not compile_commands.is_absolute():
            compile_commands = project_root.joinpath(compile_commands)

        output_path = (
            Path(raw_result["output"]).absolute()
            if raw_result["output"]
            else project_root.joinpath(*"sphinx/source/_c_api".split())
        )

        return {
            ConfigurationKey.PROJECT_ROOT: project_root.__str__(),
            ConfigurationKey.SOURCE_PATH: os.path.normpath(source_location.__str__()),
            ConfigurationKey.COMPILE_COMMANDS_LOCATION: os.path.normpath(
                compile_commands.__str__()
            ),
            ConfigurationKey.OUTPUT_DIRECTORY: os.path.normpath(output_path.__str__()),
            ConfigurationKey.QUIET: raw_result["quiet"],
            ConfigurationKey.VERBOSE: raw_result["verbose"],
        }
