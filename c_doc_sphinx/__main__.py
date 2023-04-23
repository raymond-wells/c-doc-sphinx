import os
import sys
from argparse import ArgumentParser
from logging import basicConfig
from pathlib import Path

from c_doc_sphinx.application import Application
from c_doc_sphinx.model import ConfigurationKey
from c_doc_sphinx.cli.command_line_configuration import CommandLineConfiguration


command_line_parser = CommandLineConfiguration()
configuration = command_line_parser.parse_argument_list(sys.argv[1:])

basicConfig(
    level=["INFO", "WARNING", "DEBUG"][
        configuration[ConfigurationKey.QUIET]
        + 2
        * (
            configuration[ConfigurationKey.VERBOSE]
            and not configuration[ConfigurationKey.QUIET]
        )
    ],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

Application(configuration).run()
