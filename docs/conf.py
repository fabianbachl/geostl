"""Sphinx configuration for the geostl documentation."""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

# -- Project information -----------------------------------------------------
project = "geostl"
author = "Fabian Bachl"
copyright = "2026, Fabian Bachl"  # noqa: A001 (Sphinx reads this module global)

try:
    release = _version("geostl")
except PackageNotFoundError:  # docs built from a source tree without an install
    release = "0.0.0"
version = release

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# -- Autodoc -----------------------------------------------------------------
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "signature"

# -- Napoleon (Google-style docstrings) --------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
# Render "Attributes:" as :ivar: info-fields so they don't collide with the
# dataclass fields autodoc already documents (avoids duplicate-object warnings).
napoleon_use_ivar = True

# -- Intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "furo"
html_title = f"geostl {release}"
