#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Privacy and Sensitive Information Scanner for Git Commits & Pushes.

Checks for:
1. Local machine absolute paths (Windows C:\\..., Unix /home/..., /Users/...)
2. Accounts, employee IDs (工号), real names, company names
3. Passwords, API Tokens, Private Keys, AWS Keys, JWTs, etc.
"""

import os
import sys
import re
import json
import fnmatch
import argparse
import subprocess
from pathlib import Path

# Ensure utf-8 output encoding across platforms
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_config(repo_root: Path, explicit_path: str = None) -> dict:
    config = {
        "settings": {"block_commit": True},
        "custom_keywords": [],
        "custom_patterns": [],
        "built_in_rules": {},
        "allowlist_files": [".privacy-config.example.json", "scripts/check_privacy.py"],
        "allowlist_patterns": []
    }
    
    # 1. Base template
    example_path = repo_root / ".privacy-config.example.json"
    if example_path.exists():
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except Exception:
            pass

    # 2. Local private config
    candidates = []
    if explicit_path and explicit_path != ".privacy-config.json":
        candidates.append(repo_root / explicit_path)
    candidates.extend([
        repo_root / ".privacy-config.json",
        repo_root / ".privacy-config.local.json"
    ])

    for cfg_p in candidates:
        if cfg_p.exists() and cfg_p.resolve() != example_path.resolve():
            try:
                with open(cfg_p, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    for kw in local_data.get("custom_keywords", []):
                        if kw not in config.setdefault("custom_keywords", []):
                            config["custom_keywords"].append(kw)
                    for pat in local_data.get("custom_patterns", []):
                        config.setdefault("custom_patterns", []).append(pat)
                    for r_k, r_v in local_data.get("built_in_rules", {}).items():
                        config.setdefault("built_in_rules", {})[r_k] = r_v
                    for af in local_data.get("allowlist_files", []):
                        if af not in config.setdefault("allowlist_files", []):
                            config["allowlist_files"].append(af)
                    for ap in local_data.get("allowlist_patterns", []):
                        if ap not in config.setdefault("allowlist_patterns", []):
                            config["allowlist_patterns"].append(ap)
            except Exception as e:
                print(f"{YELLOW}[Warning] Failed to parse local config {cfg_p}: {e}{RESET}", file=sys.stderr)
            break

    return config


BINARY_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff", ".psd", ".svgz",
    # Documents & Media
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".flac", ".mkv", ".webm",
    # Archives & Compressed
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Binaries & Libraries
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat", ".o", ".a",
    # Python bytecode
    ".pyc", ".pyo", ".pyd",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf"
}


def is_binary_file(file_path: Path) -> bool:
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(4096)
            if b"\x00" in chunk:
                return True
    except Exception:
        pass
    return False


def is_file_allowlisted(file_path: str, allowlist_patterns: list) -> bool:
    normalized_path = file_path.replace("\\", "/").lstrip("./")
    for pat in allowlist_patterns:
        norm_pat = pat.replace("\\", "/").lstrip("./")
        if fnmatch.fnmatch(normalized_path, norm_pat) or fnmatch.fnmatch(os.path.basename(normalized_path), norm_pat):
            return True
        if norm_pat.endswith("/*") and normalized_path.startswith(norm_pat[:-2] + "/"):
            return True
    return False


def is_allowlisted_match(matched_text: str, allowlist_regexes: list) -> bool:
    for regex in allowlist_regexes:
        if regex.search(matched_text):
            return True
    return False


def compile_rules(config: dict):
    compiled_rules = []
    
    # Custom keywords
    keywords = config.get("custom_keywords", [])
    case_sensitive = config.get("settings", {}).get("case_sensitive_keywords", False)
    flags = 0 if case_sensitive else re.IGNORECASE
    for kw in keywords:
        if kw.strip():
            escaped = re.escape(kw.strip())
            # For pure ASCII words, we can check word boundaries; but for non-ASCII/Chinese, match substring directly
            pattern = re.compile(escaped, flags)
            compiled_rules.append({
                "name": f"敏感关键词 (Sensitive Keyword: '{kw}')",
                "regex": pattern
            })

    # Custom regex patterns
    for item in config.get("custom_patterns", []):
        pat = item.get("regex")
        name = item.get("name", "自定义敏感模式")
        if pat:
            try:
                compiled_rules.append({
                    "name": name,
                    "regex": re.compile(pat)
                })
            except Exception as e:
                print(f"{YELLOW}[Warning] Invalid custom regex '{pat}': {e}{RESET}", file=sys.stderr)

    # Built-in rules
    for key, rule in config.get("built_in_rules", {}).items():
        if rule.get("enabled", True):
            name = rule.get("name", key)
            pat = rule.get("regex")
            if pat:
                try:
                    compiled_rules.append({
                        "name": name,
                        "regex": re.compile(pat)
                    })
                except Exception as e:
                    print(f"{YELLOW}[Warning] Invalid built-in regex '{pat}': {e}{RESET}", file=sys.stderr)

    # Allowlist patterns
    allowlist_regexes = []
    for pat in config.get("allowlist_patterns", []):
        try:
            allowlist_regexes.append(re.compile(pat))
        except Exception as e:
            print(f"{YELLOW}[Warning] Invalid allowlist pattern '{pat}': {e}{RESET}", file=sys.stderr)

    return compiled_rules, allowlist_regexes


def scan_line(line_content: str, line_no: int, file_path: str, rules: list, allowlist_regexes: list) -> list:
    violations = []
    for rule in rules:
        for match in rule["regex"].finditer(line_content):
            matched_str = match.group(0)
            if is_allowlisted_match(matched_str, allowlist_regexes):
                continue
            violations.append({
                "file": file_path,
                "line_no": line_no,
                "rule_name": rule["name"],
                "matched": matched_str,
                "context": line_content.strip()
            })
    return violations


def run_command(cmd: list) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        return ""
    return res.stdout


def scan_diff_output(diff_text: str, rules: list, allowlist_files: list, allowlist_regexes: list) -> list:
    violations = []
    current_file = None
    current_line_no = 0
    is_current_file_skipped = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                b_path = parts[3]
                current_file = b_path[2:] if b_path.startswith("b/") else b_path
                base_name = os.path.basename(current_file)
                if base_name in [".privacy-config.json", ".privacy-config.local.json"]:
                    violations.append({
                        "file": current_file,
                        "line_no": 1,
                        "rule_name": "私有隐私配置文件严禁提交 (Do NOT commit private config)",
                        "matched": base_name,
                        "context": "该文件包含您本地真实的敏感词与公司/工号规则，已被 .gitignore 忽略，绝不可提交到 Git 仓库！"
                    })
                is_current_file_skipped = is_file_allowlisted(current_file, allowlist_files) or Path(current_file).suffix.lower() in BINARY_EXTENSIONS
            continue

        if is_current_file_skipped or not current_file:
            continue

        if line.startswith("@@"):
            # Format: @@ -l,s +new_line,new_count @@ or @@ -l +new_line @@
            m = re.search(r"\+(\d+)(?:,\d+)?\s+@@", line)
            if m:
                current_line_no = int(m.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            line_violations = scan_line(added_content, current_line_no, current_file, rules, allowlist_regexes)
            violations.extend(line_violations)
            current_line_no += 1
        elif not line.startswith("-"):
            current_line_no += 1

    return violations


def scan_staged(rules: list, allowlist_files: list, allowlist_regexes: list) -> list:
    diff_text = run_command(["git", "diff", "--cached", "-U0"])
    return scan_diff_output(diff_text, rules, allowlist_files, allowlist_regexes)


def scan_push(rules: list, allowlist_files: list, allowlist_regexes: list) -> list:
    # Determine the remote tracking branch or diff range
    upstream = run_command(["git", "rev-parse", "--abbrev-ref", "@{upstream}"]).strip()
    if upstream:
        diff_text = run_command(["git", "diff", f"{upstream}..HEAD", "-U0"])
    else:
        # Check if origin/main exists
        origin_main = run_command(["git", "rev-parse", "--verify", "origin/main"]).strip()
        if origin_main:
            diff_text = run_command(["git", "diff", "origin/main..HEAD", "-U0"])
        else:
            diff_text = run_command(["git", "diff", "HEAD~1..HEAD", "-U0"])
            
    return scan_diff_output(diff_text, rules, allowlist_files, allowlist_regexes)


def scan_file(file_path: Path, rules: list, allowlist_files: list, allowlist_regexes: list) -> list:
    abs_file = file_path.resolve()
    rel_path = os.path.relpath(str(abs_file), str(Path.cwd().resolve())).replace("\\", "/")
    if is_file_allowlisted(rel_path, allowlist_files):
        return []
    if is_binary_file(file_path):
        return []
    
    violations = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                violations.extend(scan_line(line, idx, rel_path, rules, allowlist_regexes))
    except Exception as e:
        pass
    return violations


def scan_all_files(repo_root: Path, rules: list, allowlist_files: list, allowlist_regexes: list) -> list:
    # Use git ls-files to only check tracked files
    tracked_files_out = run_command(["git", "ls-files"])
    violations = []
    if tracked_files_out:
        for rel_file in tracked_files_out.splitlines():
            file_path = repo_root / rel_file.strip()
            if file_path.is_file():
                violations.extend(scan_file(file_path, rules, allowlist_files, allowlist_regexes))
    else:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", ".venv", "__pycache__"]]
            for file in files:
                file_path = Path(root) / file
                violations.extend(scan_file(file_path, rules, allowlist_files, allowlist_regexes))
    return violations


def report_violations(violations: list):
    print(f"\n{RED}{BOLD}{'='*78}{RESET}")
    print(f"{RED}{BOLD} [CRITICAL PRIVACY VIOLATION] 检测到潜在隐私或敏感信息泄露，操作已被强行终止！{RESET}")
    print(f"{RED}{BOLD}{'='*78}{RESET}\n")
    
    for i, v in enumerate(violations, 1):
        print(f"{YELLOW}[{i}] 文件: {v['file']} (第 {v['line_no']} 行){RESET}")
        print(f"    {BOLD}类型:{RESET} {v['rule_name']}")
        print(f"    {BOLD}匹配项:{RESET} {RED}{v['matched']}{RESET}")
        print(f"    {BOLD}代码行:{RESET} {v['context']}")
        print(f"{'-'*78}")

    print(f"\n{BOLD}防泄漏与整改指引：{RESET}")
    print(f" 1. {YELLOW}本机绝对路径{RESET}: 请改为相对路径（如使用 Path(__file__).resolve().parent 或 ./）")
    print(f" 2. {YELLOW}工号/姓名/公司名{RESET}: 严禁提交个人身份或公司专有标识，请使用通用变量或脱敏")
    print(f" 3. {YELLOW}密码/Token/私钥{RESET}: 必须使用环境变量（.env）或凭据管理器，严禁硬编码在代码库中")
    print(f" 4. {YELLOW}如果是误报{RESET}: 可在仓库根目录 {BOLD}.privacy-config.json{RESET} 的 allowlist_patterns 中添加白名单")
    print(f"{RED}{BOLD}{'='*78}\n{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Privacy and sensitive data leak checker for Git")
    parser.add_argument("--staged", action="store_true", help="Scan staged changes (git diff --cached) for pre-commit")
    parser.add_argument("--push", action="store_true", help="Scan unpushed commits for pre-push")
    parser.add_argument("--all", action="store_true", help="Scan all tracked files in the repository")
    parser.add_argument("--file", type=str, help="Scan a single specific file")
    parser.add_argument("--config", type=str, default=".privacy-config.json", help="Path to config file")
    args = parser.parse_args()

    repo_root = Path.cwd()
    config = load_config(repo_root, args.config)

    rules, allowlist_regexes = compile_rules(config)
    allowlist_files = config.get("allowlist_files", [])

    violations = []
    if args.staged:
        violations = scan_staged(rules, allowlist_files, allowlist_regexes)
    elif args.push:
        violations = scan_push(rules, allowlist_files, allowlist_regexes)
    elif args.file:
        violations = scan_file(Path(args.file), rules, allowlist_files, allowlist_regexes)
    else:  # Default to --all if no flag is provided
        violations = scan_all_files(repo_root, rules, allowlist_files, allowlist_regexes)

    if violations:
        report_violations(violations)
        sys.exit(1)
    else:
        print(f"{GREEN}[Privacy Check] ✓ 隐私信息安全检查通过，未发现敏感信息泄露。{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
