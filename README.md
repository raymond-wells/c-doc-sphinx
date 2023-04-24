# C Documentation for Sphinx

## Overview

C Documentation for Sphinx (henceforth `c-doc-sphinx`) is a very simple command utility designed to be used
in conjunction with the `hawkmoth` C tool and `compile_commands.json` to enable easy generation of good enough
looking documentation in Sphinx for C projects.

## Disclaimer

I created this tool mainly for my side projects. I neither have the time nor the resources to maintain or
add a great deal of features to this tool. I have not and probably will not test this tool against a 
large codebase-- unless a side-project evolves into one. I recommend against using this tool in a 
production environment for that reason.

If you do find this tool useful and wind up fixing a bug or extending it, then feel free to drop 
a pull request.

## Usage

```
usage: python -m c_doc_sphinx [-h] [-o OUTPUT] -r PROJECT_ROOT [-s SOURCE_LOCATION] [--compile-commands COMPILE_COMMANDS]
                              [-X [EXCLUDE_COMMANDS ...]] [-v] [-q]

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        The destination directory to place RST files in. Relative to current working directory.
  -r PROJECT_ROOT, --project-root PROJECT_ROOT
                        The root directory containing project files.
  -s SOURCE_LOCATION, --source-location SOURCE_LOCATION
                        The source directory containing code. If relative, treated as relative to project root.
  --compile-commands COMPILE_COMMANDS
                        A custom location for compile_commands.json. If relative, treated as relative to project root.
  -X [EXCLUDE_COMMANDS ...], --exclude-commands [EXCLUDE_COMMANDS ...]
                        A set of <key>=<regexp> mappings which determine the compile commands to exclude. Useful for filtering out
                        commands related to build targets that you do not want in documentation (e.g. test output).
  -v, --verbose         Use debug-level logging
```

### Standard CMake Project Example

**Default Layout**

``` text
+ .  # project root
  |-- compile_commands.json
  |-- src
    +-- main.c
  |-- sphinx
    +-- source
      +-- _c_api # Default output directory.
        +-- api.rst # Default master index.
        |-- sources # C Code Documentation Files
          +-- main.rst
```

**Command (working directory in project root)**

``` shell
python -m c_doc_sphinx -r . -o sphinx/source/_c_api -s src
```

### Embedding in your Sphinx Makefile

* Add your C source files as a prerequisite so that changes will trigger a re-run.
* Filter test output (`-X 'output=.*Test.dir'`, you may need to change this to fit your project).
* Write C Documentation to `./source/_c_api`.

``` makefile
C_SOURCES     = $(wildcard ../src/*.c ../src/**/*.c)

%: Makefile source/_c_api/api.rst
        @$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
        
source/_c_api/api.rst: $(C_SOURCES)
        @python -m c_doc_sphinx -r .. -s src -X 'output=.*Test.dir' -o './source/_c_api'
```

Then don't forget to add `_c_api/api.rst` to your root toctree in `index.rst` (or whatever other toctree you want to add it to, 
don't let me tell you what to do with your project).
