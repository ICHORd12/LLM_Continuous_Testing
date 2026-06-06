import sys
import os
import json
import subprocess
import inquirer
from tool.graph import testing_agent

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
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def setup_git_hook(repo_path):
    abs_repo_path = os.path.abspath(repo_path)
    hook_path = os.path.join(abs_repo_path, ".git", "hooks", "pre-commit")
    
    python_path = sys.executable
    tool_main_path = os.path.abspath(__file__)
    
    script_content = f"#!/bin/bash\n{python_path} {tool_main_path} --run-hook\n"
    
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

def evaluate_repository(repo_path, commit_count, provider, model):
    abs_repo_path = os.path.abspath(repo_path)
    output_log_path = os.path.abspath("experiment_results.md")
    
    original_branch = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], abs_repo_path)
    if not original_branch:
        print("Error: Target path is not a valid git repository.")
        return

    git_log_output = run_git_command(["git", "log", "--format=%H", "-n", str(commit_count)], abs_repo_path)
    if not git_log_output:
        print("Error: Could not retrieve git logs.")
        return
    
    commits = git_log_output.splitlines()
    print(f"\nEvaluating {len(commits)} commits on {abs_repo_path} using {provider.upper()}...")
    
    with open(output_log_path, "w") as f:
        f.write(f"# Evaluation Log\nTarget: {abs_repo_path}\nEngine: {provider}\n\n")

    try:
        for idx, commit_hash in enumerate(commits, 1):
            print(f"[{idx}/{len(commits)}] Checking out {commit_hash[:7]}...")
            run_git_command(["git", "checkout", commit_hash], abs_repo_path)
            
            test_target_dir = os.path.join(abs_repo_path, "tests")
            initial_state = {"directory": test_target_dir, "provider": provider, "model_name": model}
            graph_result = testing_agent.invoke(initial_state)
            
            with open(output_log_path, "a") as f:
                f.write(f"## Commit: {commit_hash}\n")
                if graph_result["status"] == "passed":
                    f.write("**Status:** PASSED\n\n")
                else:
                    f.write("**Status:** FAILED\n\n")
                    f.write(f"{graph_result['ai_report']}\n\n")
    finally:
        run_git_command(["git", "checkout", original_branch], abs_repo_path)
        print(f"Finished. Results saved to {output_log_path}")

def interactive_menu():
    config = load_config()
    
    while True:
        os.system("clear")
        print("=== AI Continuous Testing Interface ===")
        print(f"Active Repo: {config['repo_path'] or 'Not Configured'}")
        print(f"Active Model: {config['provider'].upper()} ({config['model_name']})")
        print("=======================================")
        
        main_questions = [
            inquirer.List(
                "action",
                message="Select an action using arrow keys",
                choices=[
                    "Configure Target Repository",
                    "Configure AI Model / Credentials",
                    "Enable Tool Globally for Every Commit",
                    "Disable Tool Globally for Every Commit",
                    "Run Retroactive Evaluation (Time-Travel)",
                    "Exit"
                ],
            )
        ]
        
        action = inquirer.prompt(main_questions)["action"]
        
        if action == "Configure Target Repository":
            repo_q = [inquirer.Text("path", message="Enter the absolute or relative path to your project repo")]
            path = inquirer.prompt(repo_q)["path"]
            if os.path.exists(path):
                config["repo_path"] = path
                save_config(config)
            else:
                print("Invalid path. Press enter to return.")
                input()
                
        elif action == "Configure AI Model / Credentials":
            provider_q = [inquirer.List("provider", message="Select AI Provider", choices=["ollama", "gemini"])]
            prov = inquirer.prompt(provider_q)["provider"]
            config["provider"] = prov
            
            if prov == "gemini":
                model_q = [inquirer.Text("model", message="Enter Gemini model name", default="gemini-1.5-pro")]
                key_q = [inquirer.Text("key", message="Enter Google API Key", default=config["gemini_api_key"])]
                config["model_name"] = inquirer.prompt(model_q)["model"]
                config["gemini_api_key"] = inquirer.prompt(key_q)["key"]
            else:
                model_q = [inquirer.Text("model", message="Enter Ollama model name", default="llama3.1")]
                config["model_name"] = inquirer.prompt(model_q)["model"]
                
            save_config(config)
            
        elif action == "Enable Tool Globally for Every Commit":
            if not config["repo_path"]:
                print("Please configure a target repository first. Press enter.")
                input()
            else:
                setup_git_hook(config["repo_path"])
                print("Press enter to return.")
                input()
                
        elif action == "Disable Tool Globally for Every Commit":
            if not config["repo_path"]:
                print("Please configure a target repository first. Press enter.")
                input()
            else:
                remove_git_hook(config["repo_path"])
                print("Press enter to return.")
                input()
                
        elif action == "Run Retroactive Evaluation (Time-Travel)":
            if not config["repo_path"]:
                print("Please configure a target repository first. Press enter.")
                input()
            else:
                hist_q = [inquirer.Text("count", message="How many historical commits should we evaluate?", default="3")]
                count = int(inquirer.prompt(hist_q)["count"])
                
                if config["provider"] == "gemini":
                    os.environ["GOOGLE_API_KEY"] = config["gemini_api_key"]
                    
                evaluate_repository(config["repo_path"], count, config["provider"], config["model_name"])
                print("Press enter to return.")
                input()
                
        elif action == "Exit":
            sys.exit(0)

def main():
    config = load_config()
    if len(sys.argv) > 1 and sys.argv[1] == "--run-hook":
        if not config["repo_path"]:
            sys.exit(0)
        if config["provider"] == "gemini":
            os.environ["GOOGLE_API_KEY"] = config["gemini_api_key"]
            
        test_dir = os.path.join(os.path.abspath(config["repo_path"]), "tests")
        result = testing_agent.invoke({
            "directory": test_dir,
            "provider": config["provider"],
            "model_name": config["model_name"]
        })
        
        output_log_path = os.path.abspath("experiment_results.md")
        
        if result["status"] == "failed":
            print("\n=== AI Continuous Testing Regression Alert ===")
            print(result["ai_report"])
            print("==============================================\n")
            
            with open(output_log_path, "a") as f:
                f.write(f"\n## Pre-Commit Hook Alert\n")
                f.write(f"**Status:** FAILED\n\n")
                f.write(f"{result['ai_report']}\n\n")
                
            sys.exit(1)
        else:
            with open(output_log_path, "a") as f:
                f.write(f"\n## Pre-Commit Hook Alert\n")
                f.write(f"**Status:** PASSED\n\n")
            sys.exit(0)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()