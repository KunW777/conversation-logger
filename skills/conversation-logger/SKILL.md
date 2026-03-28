---
name: conversation-logger
description: Set up automatic saving of Claude Code conversation history as Markdown files. Use this skill whenever the user wants to log, save, export, or record conversation history to files, or wants conversations automatically saved as markdown. Trigger on phrases like "save conversations", "log chat history", "auto-save sessions", "record dialogue", "conversation to md".
---

# Conversation Logger Setup

This skill configures a Stop hook that automatically saves every Claude Code session as a Markdown file after each response.

## What it does

- Creates `~/.claude/scripts/jsonl_to_md.py` — reads the session JSONL and writes a clean MD file
- Adds a `Stop` hook to `~/.claude/settings.json` — triggers the script after every Claude response
- Organizes files by project in the user's chosen output folder
- Appends only new turns on subsequent responses (preserves any manual edits)
- Auto-renames the MD file when the session is renamed via `/rename`

## Setup steps

### Step 1: Ask for output directory

Ask the user: "Where would you like to save your conversation logs? (e.g. `D:/ai对话记录` or `C:/Users/you/Documents/Claude Logs`)"

Wait for their answer before proceeding.

### Step 2: Create the Python script

Create the file at `C:/Users/<username>/.claude/scripts/jsonl_to_md.py` (detect the home directory automatically using `Path.home()`).

Use the exact script content from `scripts/jsonl_to_md.py` bundled with this skill, but replace `OUTPUT_ROOT` with the user's chosen directory.

### Step 3: Update settings.json

Read `~/.claude/settings.json`. Add the Stop hook under the `hooks` key. If a `Stop` key already exists, append to its array rather than replacing it.

```json
"hooks": {
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "python C:/Users/<username>/.claude/scripts/jsonl_to_md.py"
        }
      ]
    }
  ]
}
```

Use the actual home directory path, not the placeholder.

### Step 4: Confirm

Tell the user:
- Where the script was saved
- That the hook is active
- What the MD files will look like (organized by project subfolder, named after session title)
- That they can rename sessions with `/rename` and the MD filename will update automatically

## MD file format

Each session produces one file:

```
<output_dir>/<project_name>/<session_title>.md
```

Frontmatter:
```yaml
---
title: <session title or session ID>
date: <YYYY-MM-DD>
project: <project folder name>
session_id: <uuid>
---
```

Conversation turns use `## <UserName>` / `## Claude` headers separated by `---`.

## Notes

- The script waits 1 second after trigger to ensure JSONL is fully written
- Tool calls, thinking blocks, and slash command outputs are filtered out — only real dialogue is saved
- A `.state.json` tracks message counts per session to enable append-only updates
- If the user has manually edited an MD file, new turns are still appended at the end (existing content is never overwritten)
