# holpy

用 Python 实现的高阶逻辑（HOL）定理证明器与证明助手。

## 安装

```bash
pip install holpy
```

需要 Python 3.10 或更高版本。理论库已随包分发，无需额外下载。`z3-solver`
是核心依赖。

## 快速开始

```python
from holpy.logic import basic

basic.load_theory("logic")
print("logic theory loaded")
```

内置理论位于 `holpy/library`。用户创建的理论写入平台数据目录（Linux 下通常
是 `~/.local/share/holpy`），也可以通过 `$HOLPY_USER_DIR` 指定。若需要改写
内置理论，可将 `$HOLPY_LIBRARY_DIR` 指向可写的工作区。

## 开发

```bash
git clone https://github.com/AlexdeRuijter/holpy.git
cd holpy
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## 说明

Web IDE 与 veriT/SMT 证明重建模块已分别保存在 `archive/webapp` 和
`archive/smt` 分支，不属于发布包的一部分。英文 README 为主要说明。
