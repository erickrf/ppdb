# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license_ = f.read()

setup(
    name='ppdb',
    version='0.1.0',
    description='Interface for reading the Paraphrase Database (PPDB)',
    long_description=readme,
    author='Erick Fonseca',
    author_email='erickrfonseca@gmail.com',
    url='https://github.com/erickrf/ppdb',
    license=license_,
    packages=find_packages()
)
