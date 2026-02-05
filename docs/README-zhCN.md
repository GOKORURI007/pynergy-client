# Python Project Template

[![License: AGPL-3.0-or-later](https://img.shields.io/github/license/GOKORURI007/python-project-template)](https://github.com/GOKORURI007/python-project-template/blob/master/LICENSE)

[English](../README.md) | [简体中文](./README-zhCN.md)

## 如何使用这个模板

### 方法1：使用 GitHub 模板（推荐）

1. 点击仓库顶部的 **“使用此模板”**（Use this template）按钮
2. 选择 **“创建新仓库”**（Create a new repository）
3. 输入您的新仓库名称和描述
4. 选择是否公开或私有
5. 点击 **“创建仓库”**

### 方法2：克隆并修改

```bash
# 克隆此仓库
git clone https://github.com/YOUR_USERNAME/PythonProjectTemplate.git
cd PythonProjectTemplate

# 删除原始 git 历史（可选）
rm -rf .git
git init

# 创建您的第一次提交
git add .
git commit -m "从模板初始化"
```

### 方法3：使用 uv（快速）

如果您已安装 [uv](https://github.com/astral-sh/uv)：

```bash
# 从此模板创建新项目
uv init --template PythonProjectTemplate my-new-project
cd my-new-project
```

## 快速开始

从此模板创建项目后：

1. **安装依赖**：
   ```bash
   uv sync
   ```

2. **运行项目**：
   ```bash
   uv run main.py
   ```

3. **运行测试**：
   ```bash
   uv run scripts/run_tests.py
   ```

4. **格式化代码**：
   ```bash
   uv run scripts/format.py
   ```

5. **发布代码**:
   ```bash
   uv run scripts/release.py
   ```

## 项目结构

```
.
├── docs/             # 文档文件
├── scripts/          # 实用脚本
│   ├── format.py     # 代码格式化脚本
│   ├── release.py    # 发布和版本管理脚本
│   └── run_tests.py  # 测试运行器脚本
├── main.py           # 主入口
├── pyproject.toml    # 项目配置
└── uv.lock           # 依赖锁定文件
```

## 后续步骤

- 修改 `main.py` 来实现您的项目逻辑
- 更新 `pyproject.toml` 中的项目信息
- 使用 `uv add <包名>` 添加您的依赖
- 使用项目特定信息更新此 README
