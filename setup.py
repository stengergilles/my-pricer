from setuptools import setup
from Cython.Build import cythonize
import numpy # Import numpy

setup(
    ext_modules = cythonize("backtester_cython.pyx", compiler_directives={'language_level': "3"}),
    include_dirs=[numpy.get_include()] # Add numpy include directory
)