"""pyramid_debugtoolbar_dogpile installation script.
"""
import os
import re

from setuptools import find_packages
from setuptools import setup

HERE = os.path.abspath(os.path.dirname(__file__))

long_description = description = "dogpile support for pyramid_debugtoolbar"
with open(os.path.join(HERE, "README.md")) as r_file:
    long_description = r_file.read()
# store version in the init.py
with open(
    os.path.join(HERE, "src", "pyramid_debugtoolbar_dogpile", "__init__.py")
) as v_file:
    VERSION = re.compile(r'.*__VERSION__ = "(.*?)"', re.S).match(v_file.read()).group(1)


requires = [
    "dogpile.cache",
    "pyramid",
    "pyramid_debugtoolbar",
]
tests_require = [
    "pyramid",
    "pytest",
]
testing_extras = tests_require + []


setup(
    name="pyramid_debugtoolbar_dogpile",
    version=VERSION,
    url="https://github.com/jvanasco/pyramid_debugtoolbar_dogpile",
    author="Jonathan Vanasco",
    author_email="jonathan@findmeon.com",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web pyramid",
    license="MIT",
    packages=find_packages(
        where="src",
    ),
    package_dir={"": "src"},
    package_data={"pyramid_debugtoolbar_dogpile": ["py.typed"]},
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=tests_require,
    extras_require={
        "testing": testing_extras,
    },
    test_suite="tests",
)
