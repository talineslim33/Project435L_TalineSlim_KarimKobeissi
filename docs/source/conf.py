import os
import sys

import os
import sys

# Add the project root directory and each service directory to sys.path
sys.path.insert(0, os.path.abspath('../../'))  # Root directory
sys.path.insert(0, os.path.abspath('../../customers_service'))
sys.path.insert(0, os.path.abspath('../../inventory_service'))
sys.path.insert(0, os.path.abspath('../../review_service'))
sys.path.insert(0, os.path.abspath('../../sales_service'))


# -- Project information -----------------------------------------------------
project = 'Project435L_TalineSlim_KarimKobeissi'
copyright = '2024, Taline and Karim'
author = 'Taline and Karim'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',     # Generate documentation from docstrings
    'sphinx.ext.napoleon',    # Support Google/NumPy style docstrings
    'sphinx.ext.viewcode',    # Add links to highlighted source code
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'
html_static_path = ['_static']

# Optional: Configure autodoc defaults
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
