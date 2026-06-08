import os
import re
import subprocess
from datetime import datetime

def _extract_failing_test_file(pytest_output: str) -> str:
    """Scans raw pytest output logs using regex to automatically find failing test files."""
    if not pytest_output:
        return "Unknown Test File"
        
    matches = re.findall(r"FAILED\s+([^\s]+\.py)", pytest_output)
    if matches:
        unique_files = sorted(set(matches))
        clean_files = [f.split("rich/")[-1] if "rich/" in f else f for f in unique_files]
        return ", ".join(clean_files)
        
    match = re.search(r"=\s+FAILURES\s+=.*?\n([^\s]+\.py):\d+:", pytest_output, re.DOTALL)
    if match:
        f = match.group(1)
        return f.split("rich/")[-1] if "rich/" in f else f
        
    return "Could not automatically extract test file"

def save_evaluation_log(target_repo_path: str, pytest_output: str, ai_report: str, engine_name: str, bug_index: int, model_suffix: str, elapsed_time: str = "N/A"):
    """Compiles metrics and outputs a structured markdown log including execution time."""
    bugs_dir = os.path.join(os.getcwd(), "bugs")
    os.makedirs(bugs_dir, exist_ok=True)
    
    filename = f"bug_{bug_index}_{model_suffix}.md"
    filepath = os.path.join(bugs_dir, filename)
    
    try:
        commit_hash = subprocess.check_output(
            ["git", "-C", target_repo_path, "rev-parse", "HEAD"], 
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit_hash = "UNKNOWN_COMMIT_HASH"

    repo_name = os.path.basename(os.path.normpath(target_repo_path))
    test_file = _extract_failing_test_file(pytest_output)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        f"# Evaluation Case {bug_index:02d} ({model_suffix.upper()}): [Short Bug Description]",
        f"- **Target Repository:** {repo_name}",
        f"- **Evaluation Date:** {current_time}",
        f"- **Fix Commit Hash:** {commit_hash}",
        f"- **Test File Evaluated:** `{test_file}`",
        f"- **LLM Engine:** {engine_name}",
        f"- **Execution Time:** {elapsed_time}",
        "",
        "## 1. Pytest Failure Stack Trace (Input)",
        "```text",
        f"{pytest_output.strip()}",
        "```",
        "",
        "## 2. LLM Proposed Code Fix (Output)",
        f"{ai_report.strip()}",
        "",
        "## 3. Ground Truth (Human Developer Fix)",
        "```python",
        "# Paste the actual diff from the GitHub PR commit here",
        "```",
        "",
        "## 4. Evaluation Categorization",
        "- [ ] **EXACT MATCH:** The LLM proposed the exact code fix used by the developers.",
        "- [ ] **FUNCTIONAL MATCH:** The LLM used a different syntax/approach, but it successfully resolves the root cause and passes the test.",
        "- [ ] **PARTIAL MATCH:** The LLM correctly identified the file and line causing the issue, but its proposed code fix was flawed or incomplete.",
        "- [ ] **FAILURE:** The LLM misdiagnosed the issue completely (e.g., blamed dependencies or unrelated code).",
        "",
        "## 5. Notes / Observations",
        "- ",
        ""
    ]
    
    template = "\n".join(lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)
        
    print(f"  [✓] Log saved: bugs/{filename} ({elapsed_time})")
    return filepath