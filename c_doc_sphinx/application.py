__all__ = ["Application"]

import os
import pprint
import re
import shlex
from functools import cached_property
from io import TextIOWrapper
from itertools import chain
from logging import getLogger
from operator import itemgetter
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable, Mapping

import ujson
from pygments.lexers.c_cpp import CLexer

from c_doc_sphinx.model import CodeDocument, Command, ConfigurationKey
from c_doc_sphinx.utilities import handle_errors

_COMMENT_LINE_FILTER = re.compile(r"^\s*\*( |$)")
_CLANG_OPTION_MATCHER = re.compile(r"^-(I|D)")

_C_AUTODOC_TEMPLATE = dedent(
    """
    .. c:autodoc:: {filename_pattern}
       :clang: {clang_options}
    """
).strip()


class Application:
    """
    Scans an incoming `compile_commands.json` file, and processes any C source code found in order.

    Outputs
    =======

    * `<output-directory>/api.rst` -- An index of documentation for all C source files.
    * `<output-directory>/sources/**/*.rst` -- Individual documentation files for any sources found.
    """

    def __init__(self, configuration: Mapping[ConfigurationKey, Any]):
        self._configuration = configuration
        self._logger = getLogger(__name__)

    def run(self):
        """
        Executes the main application logic with the provided configuration.
        """
        with self._create_index_file() as _index:
            print("C Code Reference", file=_index)
            print("----------------", file=_index)
            print("", file=_index)
            print(".. toctree ::", file=_index)
            print("   :maxdepth: 2", file=_index)
            print("   :caption: Sources", file=_index)
            print("", file=_index)

            for document in self._gen_code_documentation():
                code_doc_file = Path("sources").joinpath(
                    Path(document.command.file)
                    .relative_to(self._configuration[ConfigurationKey.SOURCE_PATH])
                    .with_suffix(".rst")
                )
                print(f"  {code_doc_file}", file=_index)

                self._logger.debug("Obtained Document: %s", pprint.pformat(document))
                self._write_api_file(document)
                self._logger.info("Processed %s", document.command.file)

    def _create_index_file(self) -> TextIOWrapper:
        index_path = Path(
            self._configuration[ConfigurationKey.OUTPUT_DIRECTORY]
        ).joinpath("api.rst")
        index_path.parent.mkdir(exist_ok=True, parents=True)

        return index_path.open("w")

    def _write_api_file(self, document: CodeDocument):
        source_relative_path = Path(document.command.file).relative_to(
            self._configuration[ConfigurationKey.SOURCE_PATH]
        )

        output_doc_path = Path(
            self._configuration[ConfigurationKey.OUTPUT_DIRECTORY]
        ).joinpath("sources", source_relative_path.with_suffix(".rst"))

        self._logger.debug("Writing output to %s", output_doc_path)
        clang_options = ",".join(
            filter(
                _CLANG_OPTION_MATCHER.match,
                document.command.arguments,
            )
        )
        output_doc_path.parent.mkdir(exist_ok=True, parents=True)

        with open(output_doc_path, "w") as _f:
            print(
                Path(document.command.file).relative_to(
                    self._configuration[ConfigurationKey.SOURCE_PATH]
                )
            )
            print()
            if document.overview:
                print(
                    "Overview",
                    file=_f,
                )
                print(
                    "========\n",
                    file=_f,
                )
                print(document.overview + "\n", file=_f)

            if document.public_interface_files:
                print("Public Interface", file=_f)
                print("================\n", file=_f)
                print(
                    _C_AUTODOC_TEMPLATE.format(
                        filename_pattern=" ".join(
                            map(str, document.public_interface_files),
                        ),
                        clang_options=clang_options,
                    )
                    + "\n",
                    file=_f,
                )

            print("Implementation", file=_f)
            print("==============\n", file=_f)
            print(
                _C_AUTODOC_TEMPLATE.format(
                    filename_pattern=document.command.file,
                    clang_options=clang_options,
                ),
                file=_f,
            )

    def _gen_code_documentation(self) -> Iterable[CodeDocument]:
        for result in map(
            lambda _c: (_c, *handle_errors(self._process_command)(_c)),
            self._iter_commands(),
        ):
            if result[2] is None:
                yield result[1]
            else:
                self._logger.warning(
                    "Encountered error %s while processing %s. Skipping.",
                    result[2],
                    result[0].file,
                )

    def _process_command(self, command: Command) -> CodeDocument:
        public_interface_files = []
        lexer = CLexer()

        self._logger.debug("Simple header detection active.")
        if (header := Path(command.file).with_suffix(".h")).exists():
            self._logger.debug(
                "Found similar header %s, assuming public interface.", header
            )
            public_interface_files.append(header)

        overview = ""
        for file in chain(public_interface_files, [command.file]):
            with open(file) as _f:
                file_tokens = lexer.get_tokens(_f.read())
                possible_overview = next(
                    filter(
                        lambda _t: _t[0] != "Text.Whitespace",
                        file_tokens,
                    ),
                    None,
                )
                self._logger.debug("First token in %s: %s", file, possible_overview)
                if (
                    possible_overview
                    and str(possible_overview[0]) == "Token.Comment.Multiline"
                ):
                    overview_parts = [
                        _COMMENT_LINE_FILTER.sub("", _c)
                        for _c in possible_overview[1].strip().splitlines()[1:-1]
                    ]

                    overview = "\n".join(overview_parts)

        return CodeDocument(command, overview, public_interface_files)

    def _iter_commands(self) -> Iterable[Command]:
        return filter(
            self._determine_file_included,
            map(
                lambda _d: Command(
                    shlex.split(_d["command"]),
                    _d["file"],
                    _d["directory"],
                    _d["output"],
                ),
                self._compile_commands,
            ),
        )

    def _determine_file_included(self, command: Command) -> bool:
        """
        Checks whether a given :any:`Command.file` should be included in the final
        result.
        """
        return command.file.startswith(
            self._configuration[ConfigurationKey.SOURCE_PATH]
        )

    @cached_property
    def _compile_commands(self) -> Mapping[str, Any]:
        with open(
            os.path.join(
                *itemgetter(
                    ConfigurationKey.PROJECT_ROOT,
                    ConfigurationKey.COMPILE_COMMANDS_LOCATION,
                )(self._configuration)
            )
        ) as _f:
            return ujson.load(_f)
