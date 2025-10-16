# Poetry Pre-hook Plugin

A Poetry plugin that allows you to execute custom scripts before running `poetry install` and `poetry build` commands.

## Configuration

Configure your pre-hooks in your `pyproject.toml` file under the `[tool.poetry-prehook]` section:

```toml
[tool.poetry-prehook]
pre-install = [
    "python scripts/setup.py",
    "npm install"
]

pre-build = [
    "python scripts/generate_version.py",
    "npm run build"
]
```

## Usage

Once configured, the hooks will automatically run before the corresponding Poetry commands:

### Before poetry install

```bash
poetry install
```

This will:
1. Execute all scripts listed in `pre-install`
2. Run the normal `poetry install` command

### Before poetry build

```bash
poetry build
```

This will:
1. Execute all scripts listed in `pre-build`
2. Run the normal `poetry build` command
