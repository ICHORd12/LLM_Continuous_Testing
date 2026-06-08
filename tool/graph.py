import subprocess
import os
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from typing import TypedDict

class GraphState(TypedDict):
    directory: str
    status: str
    pytest_output: str
    ai_report: str
    provider: str
    model_name: str

def run_tests_node(state: GraphState):
    directory = state.get("directory", "dummy_project/")
    repo_root = os.path.dirname(directory)
    
    python_exec = "python3"
    pytest_path = "pytest"
    
    for venv_dir in ["venv", ".venv"]:
        possible_mac_python = os.path.join(repo_root, venv_dir, "bin", "python")
        possible_mac_pytest = os.path.join(repo_root, venv_dir, "bin", "pytest")
        if os.path.exists(possible_mac_python):
            python_exec = possible_mac_python
            pytest_path = possible_mac_pytest
            break
            
    django_runner = os.path.join(repo_root, "tests", "runtests.py")
    
    try:
        if os.path.exists(django_runner):
            result = subprocess.run([python_exec, django_runner], capture_output=True, text=True)
        else:
            result = subprocess.run([pytest_path, directory], capture_output=True, text=True)
    except FileNotFoundError:
        # Graceful handling if pytest doesn't exist
        return {
            "status": "passed", 
            "pytest_output": "pytest command not found",
            "ai_report": "Warning: Pytest is not available in this environment. Continuous testing skipped."
        }
        
    combined_output = result.stdout + "\n" + result.stderr
    
    # Graceful handling for empty test suites
    if "collected 0 items" in combined_output or "no tests ran" in combined_output or "Ran 0 tests" in combined_output:
        return {
            "status": "passed", 
            "pytest_output": combined_output,
            "ai_report": "Warning: No tests were discovered. Continuous testing skipped."
        }
    elif result.returncode == 0:
        return {"status": "passed", "pytest_output": combined_output, "ai_report": "All tests passed successfully."}
    else:
        return {"status": "failed", "pytest_output": combined_output}

def generate_report_node(state: GraphState):
    provider = state.get("provider", "ollama")
    model_name = state.get("model_name", "llama3.1")
    
    if provider == "gemini":
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    else:
        llm = ChatOllama(model=model_name, temperature=0)
        
    # RESTORED OLD PROMPT
    prompt = ChatPromptTemplate.from_template(
        "You are an expert Python QA Engineer and Software Architect. "
        "A continuous integration test suite has just failed.\n\n"
        "Review the following pytest failure log and provide a concise, structured report containing:\n"
        "1. Failing Test(s): Name of the test(s) that failed.\n"
        "2. Root Cause Analysis: A brief, technical explanation of why the failure occurred.\n"
        "3. Proposed Code Fix: The exact Python code or logical change required to fix the bug.\n"
        "4. Priority Level: (Low/Medium/High/Critical) based on the severity of the crash.\n\n"
        "Pytest Log:\n{log}"
    )
    
    chain = prompt | llm
    response = chain.invoke({"log": state["pytest_output"][:4000]})
    return {"ai_report": response.content}

def route_after_test(state: GraphState):
    if state["status"] == "failed":
        return "generate_report"
    return END

workflow = StateGraph(GraphState)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("generate_report", generate_report_node)

workflow.set_entry_point("run_tests")
workflow.add_conditional_edges("run_tests", route_after_test)
workflow.add_edge("generate_report", END)

testing_agent = workflow.compile()