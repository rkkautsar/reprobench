from setuptools import setup, find_namespace_packages

setup(
    name="reprobench",
    version="0.1.0",
    entry_points={"console_scripts": ["reprobench = reprobench.console.main:cli"]},
    packages=find_namespace_packages(),
)
