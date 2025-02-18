from setuptools import setup, find_packages

setup(
    name="cased-tf",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Click>=8.0",
        "requests>=2.25.0",
        "PyYAML>=5.1",
    ],
    entry_points={
        "console_scripts": [
            "cased-tf=cased_tf:cli",
        ],
    },
    python_requires=">=3.7",
    author="Cased",
    author_email="support@cased.com",
    description="Cased Terraform Analysis Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cased/cli",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
    ],
)
