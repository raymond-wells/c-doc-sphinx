import os
import sys
from argparse import ArgumentParser
from logging import basicConfig
from pathlib import Path

from c_doc_sphinx.application import Application
from c_doc_sphinx.model import ConfigurationKey

parser = ArgumentParser()
parser.add_argument(
    "-o",
    "--output",
    help="The destination directory to place RST files in. Relative to project root.",
    default="sphinx/source/_c_api",
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
    help="The source directory containing code. Must be relative to project root.",
    default="src",
)
parser.add_argument(
    "--compile-commands",
    help="A custom location for compile_commands.json, relative to project root.",
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

parsed_arguments = parser.parse_args(sys.argv[1:])
setattr(
    parsed_arguments, "project_root", os.path.abspath(parsed_arguments.project_root)
)

configuration = {
    ConfigurationKey.PROJECT_ROOT: Path(parsed_arguments.project_root)
    .absolute()
    .__str__(),
    ConfigurationKey.SOURCE_PATH: Path(parsed_arguments.project_root)
    .absolute()
    .joinpath(parsed_arguments.source_location)
    .absolute()
    .__str__(),
    ConfigurationKey.OUTPUT_DIRECTORY: Path(parsed_arguments.project_root)
    .absolute()
    .joinpath(parsed_arguments.output)
    .absolute()
    .__str__(),
    ConfigurationKey.COMPILE_COMMANDS_LOCATION: Path(parsed_arguments.project_root)
    .absolute()
    .joinpath(parsed_arguments.compile_commands)
    .absolute()
    .__str__(),
    ConfigurationKey.QUIET: parsed_arguments.quiet,
}

basicConfig(
    level=["INFO", "WARNING", "DEBUG"][
        parsed_arguments.quiet
        + 2 * (parsed_arguments.verbose and not parsed_arguments.quiet)
    ],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

Application(configuration).run()
