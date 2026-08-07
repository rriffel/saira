"""
    Install pacce package.
"""

from setuptools import setup, find_packages

setup(
    name="pacce",
    version="1.0.0",
    description="Python Algorithm to Compute Continuum and Equivalent widths",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "pacce": [
            "suport_files/*",
            "examples/**/*",
        ],
    },
    include_package_data=True,
    author="Joao P. V. Benedetti & Rogerio Riffel",
    url="https://github.com/rriffel/pacce",
    python_requires=">=3.10",
    install_requires=["astropy", "pandas", "scipy", "matplotlib"],
)
