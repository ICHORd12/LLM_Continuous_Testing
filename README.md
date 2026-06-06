LLM Continuous Testing Agent
============================

# Installation
1. Start the local Ollama server: `ollama start` (Ensure llama3.1 is pulled).
2. Activate a Python virtual environment:
   `python3 -m venv .venv`
   `source .venv/bin/activate`
3. Install the package:
   `pip install -e .`

# Usage
Once installed, the interactive CLI tool is available globally. Simply type:
`continuous-test`

Use the arrow keys to configure your target repository and start time-travel evaluations.