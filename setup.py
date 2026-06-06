from setuptools import setup, find_packages

setup(
    name="llm-continuous-testing",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "langchain-ollama",
        "langchain-google-genai",
        "langgraph",
        "pytest",
        "inquirer"
    ],
    entry_points={
        "console_scripts": [
            "continuous-test=tool.main:main",
        ],
    },
)