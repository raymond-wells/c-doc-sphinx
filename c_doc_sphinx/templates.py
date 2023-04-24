"""
A common set of templates for API files.
"""

__all__ = ["C_DOC_FILE"]

from textwrap import dedent
from jinja2 import Template

C_DOC_FILE = Template(
    dedent(
        r"""
{{relative_path}}
{%for _ in range(relative_path | length)%}-{%endfor%}

{%if overview -%}
Overview
========
{%- endif%}

{{overview}}
{%if public_interface_files -%}
Public Interface
================

.. c:autodoc:: {{public_interface_files}}
   :clang: {{clang_options}}
{%- endif%}

Implementation
==============

.. c:autodoc:: {{file}}
   :clang: {{clang_options}}

"""
    ).strip()
)
