# Python Project Template

[![License: AGPL-3.0-or-later](https://img.shields.io/github/license/GOKORURI007/python-project-template)](https://github.com/GOKORURI007/python-project-template/blob/master/LICENSE)

[English](./README.md) | [简体中文](./docs/README-zhCN.md)

## How to Use This Template

### Method 1: Use GitHub Template (Recommended)

1. Click the **"Use this template"** button at the top of this repository
2. Select **"Create a new repository"**
3. Enter your new repository name and description
4. Choose whether to make it public or private
5. Click **"Create repository"**

### Method 2: Clone and Modify

```bash
# Clone this repository
git clone https://github.com/YOUR_USERNAME/PythonProjectTemplate.git
cd PythonProjectTemplate

# Remove the original git history (optional)
rm -rf .git
git init

# Create your first commit
git add .
git commit -m "Initial commit from template"
```

### Method 3: Use with uv (Fast)

If you have [uv](https://github.com/astral-sh/uv) installed:

```bash
# Create a new project from this template
uv init --template PythonProjectTemplate my-new-project
cd my-new-project
```

## Getting Started

After creating your project from this template:

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Run the project**:
   ```bash
   uv run main.py
   ```

3. **Run tests**:
   ```bash
   uv run scripts/run_tests.py
   ```

4. **Format code**:
   ```bash
   uv run scripts/format.py
   ```

5. **Release code**:
   ```bash
   uv run scripts/release.py
   ```

## Project Structure

```
.
├── docs/             # Documentation files
├── scripts/          # Utility scripts
│   ├── format.py     # Code formatting script
│   ├── release.py    # Release and version management script
│   └── run_tests.py  # Test runner script
├── main.py           # Main entry point
├── pyproject.toml    # Project configuration
└── uv.lock           # Dependency lock file
```

## Next Steps

- Modify `main.py` to implement your project logic
- Update `pyproject.toml` with your project information
- Add your dependencies using `uv add <package-name>`
- Update this README with your project-specific information

