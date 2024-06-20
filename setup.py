"""
    Install pacce package.
"""

from setuptools import setup, find_packages

setup(
    name="pacce",
    version="1.00",
    packages=find_packages(),
    author="Joao P. V. Benedetti & Rogerio Riffel",
    python_requires=">=3.10",
    install_requires=["astropy", "pandas", "scipy", "matplotlib"]
)
