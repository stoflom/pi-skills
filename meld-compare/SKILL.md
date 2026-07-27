---
name: meld-compare
description: Compare files visually using Meld GUI. Use when you need to see side-by-side differences between two files or need to manually review changes.
---

# Meld File Comparison

## Purpose

Meld is a visual file comparison tool that opens a GUI window with two files side-by-side, highlighting differences. Use this skill when you need to visually inspect file changes or compare content in a user-friendly way.

## Setup

Meld should be installed on your system. Install if not present:
```bash
sudo apt install meld    # Debian/Ubuntu
sudo pacman -S meld      # Arch
# or use your package manager
```

## Usage

### Compare Two Files

```bash
meld /path/to/file1 /path/to/file2
```

### Compare Working Directory to Git Version

If you have uncommitted changes to a file:
```bash
meld <file> <(git show HEAD~1:<file>)
```

### Compare Two Git Stages

```bash
meld <(git show HEAD:<file>) <(git show :<file>)
```

### Compare File with Git HEAD

```bash
meld <(git show HEAD:<file>) /path/to/file
```

## Tips

- Meld can be configured via `~/.config/meld/meldpreferences.xml`
- Use `meld --help` for additional options
- Works best with text files (code, configs, logs)
- Supports filtering with `-l` flag: `meld -l "*.txt"`