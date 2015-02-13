"""pyramid_debugtoolbar_dogpile installation script.
"""
import os
from setuptools import setup
from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.md")).read()
README = README.split("\n\n", 1)[0] + "\n"

requires = ['pyramid_debugtoolbar>=2.2', ]

setup(
    name="pyramid_debugtoolbar_dogpile",
    author="Jonathan Vanasco",
    author_email="jonathan@findmeon.com",
    url="https://github.com/jvanasco/pyramid_debugtoolbar_dogpile",
    version="0.0.4",
    description="dogpile support for pyramid_debugtoolbar",
    keywords="web pyramid",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
    ],
    long_description=README,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    test_suite="tests",
)
