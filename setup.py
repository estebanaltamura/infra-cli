from setuptools import setup, find_packages

setup(
    name="infra",
    version="0.1.0",
    description="CLI to manage ephemeral dev environments with ngrok + Terraform",
    author="Tu Nombre",
    author_email="tu@email.com",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "typer[all]",
        "requests",
        "python-dotenv",
    ],
    entry_points={
        'console_scripts': [
            'infra=infra.scripts.cli:app',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)

