# conversation-logger

A Claude Code plugin that automatically saves your conversation history as Markdown files — no manual exporting needed.

## What it does

- Saves every Claude Code session as a `.md` file after each response
- Organizes files by project in a folder you choose
- Appends only new turns (never overwrites your manual edits)
- Auto-renames the MD file when you rename a session with `/rename`
- Filters out tool calls, thinking blocks, and slash command outputs — only real dialogue is saved

## Example output

```
D:/ai对话记录/
└── MyProject/
    └── my-session-title.md
```

Each file looks like:

```markdown
---
title: my-session-title
date: 2026-03-28
project: MyProject
session_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
---

## User

How do I set up a Stop hook?

---

## Claude

Here's how...

---
```

## Installation

```
/plugin install github:KunW.7/conversation-logger
```

Then run:

```
/reload-plugins
```

## Setup

After installing, just say:

> "Help me set up conversation logging"

Claude will ask where you want to save files, then configure everything automatically.

## Requirements

- Python 3.x (must be available in your PATH)
- Claude Code v2.0+

## How it works

The plugin installs a `Stop` hook in `~/.claude/settings.json`. After each Claude response, a Python script reads the session's JSONL file, extracts real conversation turns, and writes (or appends to) a Markdown file. A `.state.json` file tracks how many turns have been written per session so only new content is appended.
