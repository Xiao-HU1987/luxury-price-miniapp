#!/usr/bin/env python3
import subprocess
import sys
import os
from datetime import datetime

PROJECT_DIR = "/Users/huxiao/Public/测试项目-1-26.6.27"
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "auto_git_sync.log")
BRANCH = "master"


def log(message):
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    print(log_line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)


def run_git_command(args):
    result = subprocess.run(
        ["git"] + args,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main():
    log("=" * 50)
    log("开始自动同步到GitHub")
    
    try:
        code, stdout, stderr = run_git_command(["status", "--short"])
        if code != 0:
            log(f"获取git状态失败: {stderr}")
            return False
        
        if not stdout:
            log("没有检测到文件变更，无需同步")
            return True
        
        changed_files = stdout.split("\n")
        log(f"检测到 {len(changed_files)} 个文件变更")
        for f in changed_files:
            log(f"  {f}")
        
        code, stdout, stderr = run_git_command(["add", "-A"])
        if code != 0:
            log(f"git add失败: {stderr}")
            return False
        log("已添加所有变更文件")
        
        commit_msg = f"自动同步 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        code, stdout, stderr = run_git_command(["commit", "-m", commit_msg])
        if code != 0:
            log(f"git commit失败: {stderr}")
            return False
        log(f"已提交: {commit_msg}")
        
        code, stdout, stderr = run_git_command(["push", "origin", BRANCH])
        if code != 0:
            log(f"git push失败: {stderr}")
            return False
        log("已成功推送到GitHub")
        
        log("同步完成 ✓")
        return True
        
    except Exception as e:
        log(f"发生异常: {str(e)}")
        return False
    finally:
        log("=" * 50)
        log("")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)