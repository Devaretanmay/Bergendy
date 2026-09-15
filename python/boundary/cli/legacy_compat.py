import os
import shutil


__all__ = [
    "cmd_apply", "cmd_diff", "cmd_commit", "cmd_undo", "cmd_restore",
    "cmd_workflow_branch", "cmd_step", "cmd_workflow_run", "cmd_exec", "cmd_status",
    "cmd_run", "_topo_sort", "_resolve_real_binary", "_git_commit_execution",
    "_launch_agent", "_resolve_compartment", "_apply_execution",
    "_infer_step_properties", "_run_declared_workflow",
]
def cmd_apply(args): pass
def cmd_diff(args): pass
def cmd_commit(args): pass
def cmd_undo(args): pass
def cmd_restore(args): pass
def cmd_workflow_branch(args): pass
def cmd_step(args): pass
def cmd_workflow_run(args): pass
def cmd_exec(args): pass
def cmd_status(args): pass
def cmd_run(args): pass
def _topo_sort(graph): return list(graph.keys()) if hasattr(graph, "keys") else list(graph)
def _resolve_real_binary(name, root): return shutil.which(name)
def _git_commit_execution(*args, **kwargs): pass
def _launch_agent(*args, **kwargs): return 0
def _resolve_compartment(*args, **kwargs): return None
def _apply_execution(*args, **kwargs): pass
def _run_declared_workflow(ws_root, wf, cfg): pass
def _infer_step_properties(target: str, name_opt: str | None = None, comp_opt: str | None = None, type_opt: str | None = None) -> tuple[str, str, str, str]:
    target_clean = target.strip()
    is_file = os.path.exists(target_clean) or target_clean.endswith((".py", ".sh", ".js", ".ts", ".rb"))
    if is_file:
        base = os.path.splitext(os.path.basename(target_clean))[0]
        step_name = name_opt or base.replace("_", "-")
        py_bin = "python3" if shutil.which("python3") else "python"
        runners = {".py": f"{py_bin} {target_clean}", ".sh": f"bash {target_clean}", ".js": f"node {target_clean}", ".ts": f"node {target_clean}"}
        command = runners.get(os.path.splitext(target_clean)[1], target_clean)
        is_agent = any(k in target_clean.lower() for k in ["agent", "claude", "crewai", "langchain", "llm", "rag", "gpt", "prompt"])
        step_type = type_opt or ("agent" if is_agent else "process")
    else:
        first_word = target_clean.split()[0] if target_clean else "step"
        step_name = name_opt or os.path.basename(first_word).replace("_", "-")
        command = target_clean
        is_agent = any(k in target_clean.lower() for k in ["claude", "opencode", "codex", "agent", "crewai", "langchain"])
        step_type = type_opt or ("agent" if is_agent else "process")

    if comp_opt:
        compartment = comp_opt
    else:
        tc = target_clean.lower()
        comp_map = {
            "research": ["ocr", "scrape", "extract", "read", "audit", "search", "scan"],
            "builder": ["build", "patch", "rag", "excel", "write", "generate", "code"],
            "network": ["email", "send", "fetch", "api", "download", "http", "notify", "curl"],
            "tester": ["test", "verify", "check", "pytest"],
        }
        compartment = next((c for c, keywords in comp_map.items() if any(k in tc for k in keywords)), "default")

    return step_name, command, step_type, compartment