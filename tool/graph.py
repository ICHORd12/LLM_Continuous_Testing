from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
import subprocess
from tool.llm_analyzer import analyze_failure

class GraphState(TypedDict):
    directory: str
    provider: str
    model_name: str
    status: str
    pytest_output: str
    ai_report: Optional[str]

def run_tests_node(state: GraphState):
    directory = state.get("directory", "dummy_project/")
    result = subprocess.run(["pytest", directory], capture_output=True, text=True)
    
    if "collected 0 items" in result.stdout or "no tests ran" in result.stdout:
        return {
            "status": "passed", 
            "pytest_output": result.stdout,
            "ai_report": "Warning: No tests were discovered. Continuous testing skipped."
        }
    elif result.returncode == 0:
        return {"status": "passed", "pytest_output": result.stdout}
    else:
        return {"status": "failed", "pytest_output": result.stdout}

def analyze_node(state: GraphState):
    provider = state.get("provider", "ollama")
    model_name = state.get("model_name", "llama3.1")
    
    report = analyze_failure(state["pytest_output"], provider, model_name)
    return {"ai_report": report}

def router(state: GraphState):
    if state["status"] == "failed":
        return "analyze"
    return "end"

workflow = StateGraph(GraphState)

workflow.add_node("run_tests", run_tests_node)
workflow.add_node("analyze", analyze_node)
workflow.set_entry_point("run_tests")
workflow.add_conditional_edges(
    "run_tests",
    router,
    {
        "analyze": "analyze",
        "end": END
    }
)
workflow.add_edge("analyze", END)

testing_agent = workflow.compile()