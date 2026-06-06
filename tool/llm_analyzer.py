import os
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

def analyze_failure(pytest_output: str, provider: str = "ollama", model_name: str = "llama3.1") -> str:
    if provider == "gemini":
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.2)
    else:
        llm = ChatOllama(model=model_name, temperature=0.2) 
    
    prompt = f"""
    You are an automated debugging assistant for a continuous testing pipeline.
    Analyze the following test failure. 
    1. Identify which test failed.
    2. Explain the difference between the expected and actual output.
    3. Assign a priority level (High, Medium, Low) for fixing it based on severity.
    
    Test Output:
    {pytest_output}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content