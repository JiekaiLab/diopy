# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 17:43:55 2021

@author: fenghuijian
"""
import os
from setuptools import setup, find_packages

path = os.path.abspath(os.path.dirname(__file__))

try:
  with open(os.path.join(path, 'README.md')) as f:
    long_description = f.read()
except Exception as e:
  long_description = "The scRNA-seq data IO between R and Python(Python version)"
  

setup(
    name = "pyscdior",
    version = "0.2.0",
    keywords = ["scRNA-seq", "hdf5", "data IO", "scanpy"],
    description = "The scRNA-seq data IO between R and Python(Python version)",
    long_description = long_description,
    long_description_content_type='text/markdown',
    python_requires=">=3.5.0",
    license = "GPL-3.0 License",

    url = ["https://github.com/JiekaiLab/scDIOR", "https://github.com/fenghuijian/pyscdior"],
    author = "Huijian Feng",
    author_email = "fenghuijian@outlook.com",

    packages = find_packages(),
    include_package_data = True,
    requires = ["scipy", "scanpy","pandas", "numpy", "anndata","re","os","h5py","typing"],
    platforms = "any",

    scripts = []
)
