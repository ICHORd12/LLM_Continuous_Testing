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
        You are an expert Python debugging assistant for a continuous testing pipeline.
        Analyze the following test failure output. DO NOT give generic advice. 
        
        You MUST provide your response in the following strict format:
        
        ### 1. Failing Test(s)
        Name the exact test function(s) or file(s) that failed.
        
        ### 2. Root Cause Analysis
        Explain precisely why the actual output differs from the expected output based on the stack trace.
        
        ### 3. Proposed Code Fix
        Provide a specific, actionable Python code snippet to fix the bug. If it is a configuration error, provide the exact terminal command to fix it.
        
        ### 4. Priority Level
        Assign High, Medium, or Low based on severity.
        
        Test Output:
        {pytest_output}
        """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    content = response.content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and 'text' in block:
                return block['text']
                
    return str(content)