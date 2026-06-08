import sys
import os
import json
import subprocess
import inquirer
from tool.graph import testing_agent
from tool.eval_saver import save_evaluation_log
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"repo_path": "", "provider": "ollama", "model_name": "llama3.1", "gemini_api_key": ""}

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def run_git_command(command, repo_path):
    result = subprocess.run(command, cwd=repo_path, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None

def setup_git_hook(repo_path):
    abs_repo_path = os.path.abspath(repo_path)
    hook_path = os.path.join(abs_repo_path, ".git", "hooks", "pre-commit")
    python_path = sys.executable
    tool_main_path = os.path.abspath(__file__)
    
    # SELF-AWARE HOOK: Only triggers if the commit is happening in the exact target repository
    script_content = f"""#!/bin/bash
if [ "$PWD" != "{abs_repo_path}" ]; then
    exit 0
fi
{python_path} {tool_main_path} --run-hook
"""
    with open(hook_path, "w") as f:
        f.write(script_content)
    os.chmod(hook_path, 0o755)
    print(f"Successfully linked automated testing agent to pre-commit hook in: {abs_repo_path}")

def remove_git_hook(repo_path):
    abs_repo_path = os.path.abspath(repo_path)
    hook_path = os.path.join(abs_repo_path, ".git", "hooks", "pre-commit")
    if os.path.exists(hook_path):
        os.remove(hook_path)
        print(f"Successfully removed the automated testing hook from: {abs_repo_path}")
    else:
        print(f"No active hook found in: {abs_repo_path}")

def run_test_on_target(config, target_dir):
    print(f"\n[*] Running analysis using {config['model_name']}...")
    
    if config["provider"] == "gemini":
        os.environ["GOOGLE_API_KEY"] = config["gemini_api_key"]
    
    start_time = time.time()
    result = testing_agent.invoke({
        "directory": target_dir,
        "provider": config["provider"],
        "model_name": config["model_name"]
    })
    elapsed = f"{time.time() - start_time:.2f}s"
    
    print("\n" + "="*40)
    print(f"REPORT ({config['model_name']})")
    print("="*40)
    print(result.get("ai_report", "No analysis generated."))
    print("="*40 + "\n")
    
    # CREATE REPORT IN THE TARGET REPO
    if result["status"] == "failed":
        target_repo = os.path.abspath(config["repo_path"])
        report_file_path = os.path.join(target_repo, "AI_Regression_Report.md")
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write("# AI Continuous Testing Report\n\n")
            f.write(result.get("ai_report", "No analysis generated."))
        print(f"[*] Analysis saved to: {report_file_path}\n")
    
    bug_index = int(time.time())
    save_evaluation_log(
        target_repo_path=config["repo_path"],
        pytest_output=result.get("pytest_output", ""),
        ai_report=result.get("ai_report", ""),
        engine_name=config["model_name"],
        bug_index=bug_index,
        model_suffix="prod",
        elapsed_time=elapsed
    )
    
    # If this was a hook trigger, block the commit on failure
    if len(sys.argv) > 1 and sys.argv[1] == "--run-hook" and result["status"] == "failed":
        sys.exit(1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--run-hook":
        sys.exit(0)

def interactive_menu():
    config = load_config()
    while True:
        print(f"\n=== AI Testing Tool (Production) ===")
        print(f"Repo: {config['repo_path']}")
        print(f"Model: {config['model_name']}")
        
        choices = [
            "Configure Settings",
            "Enable Automated Hook in Target Repo",
            "Disable Automated Hook in Target Repo",
            "Run Test on Current Directory",
            "Run Test on Specific Commit Hash",
            "Exit"
        ]
        action = inquirer.prompt([inquirer.List("act", message="Action", choices=choices)])["act"]
        
        if action == "Configure Settings":
            repo_q = [inquirer.Text("path", message="Enter target repo path", default=config["repo_path"])]
            config["repo_path"] = inquirer.prompt(repo_q)["path"]
            
            provider_q = [inquirer.List("provider", message="Select AI Provider", choices=["ollama", "gemini"])]
            prov = inquirer.prompt(provider_q)["provider"]
            config["provider"] = prov
            
            if prov == "gemini":
                model_choices = ["gemini-3.5-flash", "gemini-3.1-pro-preview", "Custom Input"]
                model_q = [inquirer.List("model", message="Select Gemini Model", choices=model_choices)]
                selected_model = inquirer.prompt(model_q)["model"]
                if selected_model == "Custom Input":
                    custom_q = [inquirer.Text("model", message="Type specific Gemini model")]
                    config["model_name"] = inquirer.prompt(custom_q)["model"]
                else:
                    config["model_name"] = selected_model
                key_q = [inquirer.Text("key", message="Enter Google API Key", default=config["gemini_api_key"])]
                config["gemini_api_key"] = inquirer.prompt(key_q)["key"]
            else:
                model_q = [inquirer.Text("model", message="Enter Ollama model name", default="llama3.1")]
                config["model_name"] = inquirer.prompt(model_q)["model"]
            save_config(config)
            
        elif action == "Enable Automated Hook in Target Repo":
            if config["repo_path"]: setup_git_hook(config["repo_path"])
        elif action == "Disable Automated Hook in Target Repo":
            if config["repo_path"]: remove_git_hook(config["repo_path"])
        elif action == "Run Test on Current Directory":
            run_test_on_target(config, os.path.abspath(os.path.join(config["repo_path"], "tests")))
        elif action == "Run Test on Specific Commit Hash":
            hash_val = inquirer.prompt([inquirer.Text("h", message="Hash?")])["h"]
            run_git_command(["git", "checkout", hash_val], config["repo_path"])
            run_test_on_target(config, os.path.abspath(os.path.join(config["repo_path"], "tests")))
        else:
            break

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--run-hook":
        config = load_config()
        if not config["repo_path"]: sys.exit(0)
        run_test_on_target(config, os.path.join(config["repo_path"], "tests"))
    else:
        interactive_menu()

if __name__ == "__main__":
    main()