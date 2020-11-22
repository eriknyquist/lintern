import unittest
import os
from setuptools import setup, find_packages

from lintern import __version__

HERE = os.path.abspath(os.path.dirname(__file__))
README = os.path.join(HERE, "README.rst")

with open(README, 'r') as f:
    long_description = f.read()

setup(
    name='lintern',
    version=__version__,
    description=('Rewrites C code to fix common complaints from static analysis checkers'),
    long_description=long_description,
    url='http://github.com/eriknyquist/lintern',
    author='Erik Nyquist',
    author_email='eknyquist@gmail.com',
    license='Apache 2.0',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False
)
