from setuptools import (
    setup,
    find_packages,
)

__version__: str = "0.0.3"

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lowmq-client",
    version=__version__,
    description="Python asynchronous client for interacting with LowMQ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pydantic>=2.6.4",
        "aiohttp>=3.9.3",
    ],
)
