from setuptools import setup, find_packages

setup(
    name="infra",
    version="0.1.0",
    packages=find_packages(where="INFRA"),   # si estás usando la estructura /src
    package_dir={"": "INFRA"},
    install_requires=[
        "typer[all]",
        "requests",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "infra=infra.scripts.cli:app",  # apunta al comando principal
        ],
    },
)
