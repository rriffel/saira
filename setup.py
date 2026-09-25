"""
    Install saira package.
"""

from setuptools import setup, find_packages

setup(
    name="saira",
    version="1.0.0",
    description="Self-consistent Algorithm for spectral Indices measuRements and Analysis",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "saira": [
            "suport_files/*",
            "examples/**/*",
            "assets/*",
        ],
    },
    include_package_data=True,
    author="Joao P. V. Benedetti & Rogerio Riffel",
    url="https://github.com/rriffel/saira",
    python_requires=">=3.10",
    install_requires=["astropy", "pandas", "scipy", "matplotlib", "PyQt5"],
)
