# coding: utf-8

from setuptools import setup, find_packages

setup(
    name="template-matching-by-opencv-for-rtsp",
    version="1.0.0",
    author="Latona_Open_Source",
    packages=find_packages("./src"),
    package_dir={"":"src"},
    install_requires=[],
    tests_require=[]
)
