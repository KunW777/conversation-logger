#!/usr/bin/env python3
# Claude Code Stop hook: 将当前 session 的对话历史保存为 Markdown 文件。
# 保存位置: D:/ai对话记录/<项目名>/<标题>.md
# state 以 session_id 为 key，用 last_line 追踪 JSONL 处理位置。
import json
import re
import sys
import os
import time
from datetime import datetime
from pathlib import Path

OUTPUT_ROOT = Path("D:/ai对话记录")
STATE_FILE = OUTPUT_ROOT / ".state.json"


def sanitize_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()[:80]


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "").strip()
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p)
    return ""


def is_real_user_message(entry: dict) -> bool:
    if entry.get("isMeta"):
        return False
    msg = entry.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        return False
    text = content.strip()
    if not text:
        return False
    if text.startswith("<local-command") or text.startswith("<command-name>"):
        return False
    return True


def build_turn(msg: dict) -> str:
    role_header = "## Kun" if msg["role"] == "user" else "## Claude"
    return "\n".join([role_header, "", msg["content"], "", "---", "", ""])


def main():
    time.sleep(1)  # 等待 JSONL 完成写入

    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    transcript_path = payload.get("transcript_path")
    if not transcript_path or not os.path.exists(transcript_path):
        sys.exit(0)

    session_id = payload.get("session_id", "unknown")

    messages = []
    custom_title = None
    first_timestamp = None
    project_cwd = None
    total_lines = 0

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            total_lines = line_num
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")

            if entry_type == "custom-title":
                custom_title = entry.get("customTitle", "").strip()

            elif entry_type == "user" and is_real_user_message(entry):
                text = extract_text(entry["message"].get("content", ""))
                if not text:
                    continue
                ts = entry.get("timestamp", "")
                if not first_timestamp and ts:
                    first_timestamp = ts
                if not project_cwd:
                    project_cwd = entry.get("cwd", "")
                messages.append({"role": "user", "content": text, "line": line_num})

            elif entry_type == "assistant":
                content = entry.get("message", {}).get("content", [])
                text = extract_text(content)
                if not text:
                    continue
                if text.strip() in ("No response requested.", "No response requested"):
                    continue
                messages.append({"role": "assistant", "content": text, "line": line_num})

    if not messages:
        sys.exit(0)

    # 合并连续的同角色消息，保留第一条的行号
    merged = [messages[0].copy()]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1]["content"] += "\n\n" + msg["content"]
            # 保持 line 为该组第一条的行号，不更新
        else:
            merged.append(msg.copy())

    # 项目名和日期
    project_name = Path(project_cwd).name if project_cwd else "unknown"
    if first_timestamp:
        try:
            dt = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
            date_str = dt.astimezone().strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 当前应有的文件名
    title = custom_title or session_id
    safe_title = sanitize_filename(title)
    output_dir = OUTPUT_ROOT / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    current_file = output_dir / f"{safe_title}.md"

    # 读取 state（兼容旧的 msg_count 格式）
    state = load_state()
    prev = state.get(session_id, {"file": None, "last_line": 0})
    prev_file = Path(prev["file"]) if prev.get("file") else None
    prev_last_line = prev.get("last_line", 0)

    # 旧格式迁移：有 msg_count 但没有 last_line → 重置为 0 触发全量重写
    if "msg_count" in prev and "last_line" not in prev:
        prev_last_line = 0

    # 如果有旧文件且名字不同 → 更新 frontmatter title 并重命名
    if prev_file and prev_file.exists() and prev_file != current_file:
        content = prev_file.read_text(encoding="utf-8")
        content = re.sub(r"^title: .+$", f"title: {title}", content, count=1, flags=re.MULTILINE)
        prev_file.write_text(content, encoding="utf-8")
        prev_file.rename(current_file)

    if not current_file.exists() or prev_last_line == 0:
        # 首次写入：生成完整文件
        header = "\n".join([
            "---",
            f"title: {title}",
            f"date: {date_str}",
            f"project: {project_name}",
            f"session_id: {session_id}",
            "---", "",
        ])
        body = "".join(build_turn(m) for m in merged)
        current_file.write_text(header + body, encoding="utf-8")

    else:
        # 追加：只写入行号 > prev_last_line 的新消息
        new_messages = [m for m in merged if m["line"] > prev_last_line]
        if not new_messages:
            sys.exit(0)
        addition = "".join(build_turn(m) for m in new_messages)
        existing = current_file.read_text(encoding="utf-8")
        current_file.write_text(existing.rstrip("\n") + "\n\n" + addition, encoding="utf-8")

    # 更新 state：存 last_line（JSONL 总行数）
    state[session_id] = {"file": str(current_file), "last_line": total_lines}
    save_state(state)


if __name__ == "__main__":
    main()
