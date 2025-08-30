# llmprimer (macOS)

A tiny CLI that scans a repository, respects your `.gitignore`, and writes a single context file you can paste into LLMs:

```
LLMContext/repository_dump.txt
```

It prints a directory tree first, then appends the contents of each included file with a header line like:

```
--- File: path/inside/repo.ext ---
```

## Features

* Respects `.gitignore` (via `pathspec`/gitwildmatch rules)
* Skips common folders: `.git`, `node_modules`, `__pycache__`, virtualenvs, etc.
* Language‑specific filtering by file extension(s)
* Stores a **local** copy of your chosen language config for repeatable runs

## Requirements

* macOS with the default **zsh** shell
* **Python 3.9+**
* Python packages: `inquirer`, `pathspec`

> Script location used in examples:
>
> `/Users/danielrothenpieler/Documents/git/llmprimer/llmprimer.py`

---

## Quick Start (recommended: simple symlink)

This installs nothing system‑wide and is easy to undo.

1. **Install Python deps into the Python you will use**

```bash
python3 -m pip install --upgrade pip
python3 -m pip install inquirer pathspec
```

2. **Make the script executable**

```bash
chmod +x \
  "/Users/danielrothenpieler/Documents/git/llmprimer/llmprimer.py"
```

3. **Create a `~/bin` and symlink the script as `llmprimer`**

```bash
mkdir -p "$HOME/bin"
ln -sf \
  "/Users/daniel/git/tools/llmprimer/llmprimer.py" \
  "$HOME/bin/llmprimer"
```

4. **Ensure `~/bin` is on your PATH** (zsh):

```bash
if ! grep -q 'export PATH="$HOME/bin:$PATH"' ~/.zshrc; then
  echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
fi
source ~/.zshrc
```

5. **Verify**

```bash
which llmprimer   # should print /Users/<you>/bin/llmprimer
llmprimer         # should launch the tool
```

> Prefer `/usr/local/bin`? Use: `sudo ln -sf <script> /usr/local/bin/llmprimer`.

---

## Using a virtual environment (recommended for isolation)

If you want `llmprimer` to always run with a specific venv/conda env, create a tiny wrapper script that calls that env’s Python, so imports always work.

### Option A — Python venv

```bash
# Create a venv next to the script (or wherever you prefer)
python3 -m venv \
  "/Users/danielrothenpieler/Documents/git/llmprimer/.venv"

# Install deps inside the venv
"/Users/danielrothenpieler/Documents/git/llmprimer/.venv/bin/python" \
  -m pip install --upgrade pip inquirer pathspec

# Wrapper in ~/bin
cat > "$HOME/bin/llmprimer" <<'SH'
#!/usr/bin/env bash
"/Users/danielrothenpieler/Documents/git/llmprimer/.venv/bin/python" \
  "/Users/danielrothenpieler/Documents/git/llmprimer/llmprimer.py" "$@"
SH
chmod +x "$HOME/bin/llmprimer"
```

### Option B — Conda env

```bash
# Create/activate your env
conda create -n llmprimer python=3.11 -y
conda activate llmprimer
conda install -c conda-forge python-inquirer pathspec -y

# Wrapper in ~/bin (adjust your conda path if needed)
PY=$(python -c 'import sys; print(sys.executable)')
cat > "$HOME/bin/llmprimer" <<SH
#!/usr/bin/env bash
"$PY" \
  "/Users/danielrothenpieler/Documents/git/llmprimer/llmprimer.py" "$@"
SH
chmod +x "$HOME/bin/llmprimer"
```

---

## Configuration

The tool needs a configuration that maps a **language name** to a list of file **extensions** to include. There are two places it looks:

* **Local config** (preferred on reruns):
  `./LLMContext/config.json` in the repository you run the tool from
* **Global config** (first‑run / template):
  `config.json` next to `llmprimer.py` (the script directory)

**First run behavior**

* If a local config exists, it is used immediately.
* Otherwise, you’ll be prompted to select a language from the **global** config; the chosen language block will be copied to `./LLMContext/config.json` for future runs.

### Example `config.json`

```json
{
  "python": {
    "extensions": [".py", ".toml", ".md", ".txt", ".yml", ".yaml"]
  },
  "svelte": {
    "extensions": [".svelte", ".ts", ".js", ".css", ".md"]
  },
  "node": {
    "extensions": [".js", ".mjs", ".cjs", ".ts", ".json", ".md"]
  }
}
```

> Keep the lists tight—exclude binaries and giant assets to keep the dump readable.

### Exclusions

Out of the box the script ignores:

```
.git, .idea, __pycache__, node_modules, .venv, venv, LLMContext
```

It **also** respects your `.gitignore` (via `pathspec`), so anything ignored by Git won’t be included.

---

## Usage

From the **root of the repository** you want to summarize:

```bash
llmprimer
```

On first run (if using a global config) you’ll select a language. The output appears at:

```
LLMContext/repository_dump.txt
```

Open it on macOS with:

```bash
open LLMContext/repository_dump.txt
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'inquirer'`

You installed packages into a different Python than the one running the command. Fix by installing into the same interpreter your command uses:

```bash
# See which interpreter runs when you call llmprimer
head -1 "$(command -v llmprimer)"   # shows the shebang or wrapper
command -v python3                   # which python3 your shell sees

# Install there
python3 -m pip install inquirer pathspec
```

If you use a venv/conda env, prefer the **wrapper script** approach above so the correct Python is always used.

### `zsh: command not found: llmprimer`

Make sure `~/bin` is on your PATH and the symlink or wrapper exists:

```bash
ls -l "$HOME/bin/llmprimer"
echo $PATH | tr ':' '\n' | nl
```

### Permissions

If you see a permission error, ensure the script/wrapper is executable:

```bash
chmod +x "$HOME/bin/llmprimer"
```

---

## Uninstall

```bash
rm -f "$HOME/bin/llmprimer"
# (Optional) remove PATH line from ~/.zshrc if you added it specifically for ~/bin
```

---

## Notes

* macOS uses forward slashes in paths already; the tool normalizes paths internally for cross‑platform consistency.
* Large repos can produce large dumps; keep your `extensions` list and `.gitignore` tidy.

Happy summarizing! 🎯
