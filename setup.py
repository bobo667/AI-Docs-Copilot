from setuptools import setup, find_packages

setup(
    name="ai-docs-copilot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4',
        'requests',
        "markdownify"
    ]
)
