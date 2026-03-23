# uv-release
Minimal release tool for Python projects using uv.

## Features
- Bump versions: major, minor, patch.
- Commit changes and tag Git automatically.
- Optional confirmation (--yes) and force release (--force).
- Show current version: --version.
- Preview version bump before committing.

## Installation

### Clone the repository and install using pip
`pip install -e .`

### Run once using uvx
`uvx --from https://github.com/mkwant/uv-release.git release`

### Install using uv tool:
```
uv tool install --from https://github.com/mkwant/uv-release.git uv-release
```

## Usage
```
# Show help
release --help

# Bump patch version
release patch

# Skip confirmation
release minor --yes

# Force release on dirty Git repo
release major --force

# Show version
release --version
```

Notes: Requires uv and a Git repo with at least one commit. Only updates pyproject.toml and uv.lock.