"""Installation to .venv"""

import re

from setuptools import find_packages, setup


def get_version():
    """Return unfurl version from __init__.py."""
    with open("./__init__.py") as f:
        match = re.search(r'__version__ = "(.*)"', f.read())
        if match:
            return match.group(1)
        else:
            raise ValueError("Version string not found in __init__.py")


with open("README.md", "r") as f:
    long_description = f.read()


setup(
    name="athena",
    version=get_version(),
    packages=find_packages(),
    long_description=long_description,
    install_requires=[],
    package_data={"": ["*.json"]},  # Include all .json files in the package
    author="melo",
    author_email="melomacarono@proton.me",
)
