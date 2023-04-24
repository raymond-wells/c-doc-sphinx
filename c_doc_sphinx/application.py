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
from c_doc_sphinx.templates import C_DOC_FILE

_COMMENT_LINE_FILTER = re.compile(r"^\s*\*( |$)")
_CLANG_OPTION_MATCHER = re.compile(r"^-(I|D)")


class Application:
    """
    Scans an incoming `compile_commands.json` file, and processes any C source code found in order.

    Outputs
    =======

    * ``<output-directory>/api.rst`` -- A master index of documentation for all C source files.
    * ``<output-directory>/sources/**/*.rst`` -- Individual documentation files for any sources found.
    """

    def __init__(self, configuration: Mapping[ConfigurationKey, Any]):
        self._configuration = configuration
        self._logger = getLogger(__name__)
        self._lexer = CLexer()

    def run(self):
        """
        Executes the main application logic with the provided configuration.
        """
        seen = set()
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

                # Skip processing if we've already seen the file.
                if code_doc_file in seen:
                    continue

                # Prevent cases where some targets would result in duplicate code files.
                print(f"   {code_doc_file}", file=_index)

                self._logger.debug("Obtained Document: %s", pprint.pformat(document))
                self._write_api_file(document)
                self._logger.info("Processed %s", document.command.file)

                seen.add(code_doc_file)

    def _create_index_file(self) -> TextIOWrapper:
        """
        Creates the master index file ``api.rst`` within the output location.
        Will also create the output location if it does not already exist.

        Returns:
            A fully hydrated :any:`TextIOWrapper` allowing for output to the
            master index file. Caller is responsible for closing this resource.
        """
        index_path = Path(
            self._configuration[ConfigurationKey.OUTPUT_DIRECTORY]
        ).joinpath("api.rst")
        index_path.parent.mkdir(exist_ok=True, parents=True)

        return index_path.open("w")

    def _write_api_file(self, document: CodeDocument):
        """
        Writes a file containing documentation for a single C file discovered by scanning
        ``compile_commands.json``.

        Parameters:
            document: The :any:`CodeDocument` containing contextual information for
                      the source file to process.
        """
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
            _f.write(
                C_DOC_FILE.render(
                    dict(
                        relative_path=Path(document.command.file)
                        .relative_to(self._configuration[ConfigurationKey.SOURCE_PATH])
                        .__str__(),
                        overview=document.overview,
                        clang_options=clang_options,
                        public_interface_files=" ".join(
                            map(str, document.public_interface_files)
                        ),
                        file=str(document.command.file),
                    )
                )
            )

    def _gen_code_documentation(self) -> Iterable[CodeDocument]:
        """
        Generates a series of :any:`CodeDocument` instances containing extracted code documentation
        context gleaned successfully from the contens of the compile commands.
        """
        for command in self._iter_commands():
            try:
                yield self._process_command(command)
            except Exception as e:
                self._logger.warning(
                    "Encountered error %s while processing %s. Skipping.",
                    str(e),
                    command.file,
                    exc_info=self._configuration[ConfigurationKey.VERBOSE],
                )

    def _process_command(self, command: Command) -> CodeDocument:
        """
        Takes in a :any:`Command` and produces a :any:`CodeDocument` containing
        any public interface files and overview found.

        Overview resolution is performed by looking for a comment that begins as the first
        non-whitespace token of the first file in this order:

        * Public Interface Files
        * The implementation file, itself.


        .. note::
            At the time of writing, this method assumes that the public interface files are
            co-located with the source file, and that they share basenames. E.g.:
            ``src/gui/window.h`` would be a public interface file of ``src/gui/window.c``.

            Since this tool is primarily for my personal use, I tend toward this convention.
            However, a future change may allow for customization of the header resolution
            algorithm.

        Parameters:
            command: Provides access to the source file and possible header file locations.

        Returns:
            A fully-hydrated :any:`CodeDocument` instance containing extracted overview and
            public interface files.
        """
        public_interface_files = []

        self._logger.debug("Simple header detection active.")
        if (header := Path(command.file).with_suffix(".h")).exists():
            self._logger.debug(
                "Found similar header %s, assuming public interface.", header
            )
            public_interface_files.append(header)

        overview = ""
        for file in chain(public_interface_files, [command.file]):
            with open(file) as _source_file:
                file_tokens = self._lexer.get_tokens(_source_file.read())
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
            self._command_included,
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

    def _command_included(self, command: Command) -> bool:
        """
        Checks whether a given :any:`Command.file` should be included in the final
        result.
        """
        return (
            not any(
                map(
                    lambda _f: _f[1].match(getattr(command, _f[0], "")),
                    self._configuration[ConfigurationKey.EXCLUSION_FILTERS],
                )
            )
        ) and command.file.startswith(self._configuration[ConfigurationKey.SOURCE_PATH])

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
