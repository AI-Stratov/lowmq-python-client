from setuptools import (
    setup,
    find_packages,
)

__version__: str = "0.0.1"

setup(
    name="lowmq-python-client",
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pydantic>=2.6.4",
        "aiohttp>=3.9.3",
    ],
)
