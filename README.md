# Webnovel Writer

[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

## 项目简介

`Webnovel Writer` 是面向长篇网文创作的运行时与数据管线，目标是降低 AI 写作中的“遗忘”和“一致性漂移”，支持长周期连载生产。

当前仓库提供的是上游运行时核心能力（`scripts/`、`dashboard/`、`data_modules/`），可被不同宿主或桥接层复用。

## 文档导航

- 架构与模块：`docs/architecture.md`
- 命令说明：`docs/commands.md`
- RAG 与配置：`docs/rag-and-config.md`
- 题材模板：`docs/genres.md`
- 运维与恢复：`docs/operations.md`
- 文档总览：`docs/README.md`

## 快速开始

### 1) 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2) 初始化小说项目

```bash
python .\webnovel-writer\scripts\webnovel.py init -- "<project_dir>" "<title>" "<genre>"
```

示例：

```bash
python .\webnovel-writer\scripts\webnovel.py init -- "E:\code\20260301\webnovel_demo" "示例小说" "修仙"
```

### 3) 常用命令

```bash
python .\webnovel-writer\scripts\webnovel.py where --project-root "E:\code\20260301\webnovel_demo"
python .\webnovel-writer\scripts\webnovel.py extract-context --project-root "E:\code\20260301\webnovel_demo" --chapter 1 --format text
python .\webnovel-writer\scripts\webnovel.py status --project-root "E:\code\20260301\webnovel_demo" -- --focus all
python .\webnovel-writer\scripts\webnovel.py workflow --project-root "E:\code\20260301\webnovel_demo" -- detect
```

### 4) 启动可视化面板（可选）

```bash
python -m dashboard.server --project-root "E:\code\20260301\webnovel_demo" --host 127.0.0.1 --port 8765 --no-browser
```

## 版本更新

| 版本 | 说明 |
|------|------|
| **v5.5.0（当前）** | 增加只读可视化 Dashboard 与实时刷新能力，支持插件目录启动与预构建前端分发。 |
| **v5.4.4** | 引入官方 Plugin Marketplace 安装机制，统一修复 Skills/Agents/References 的 CLI 调用链路。 |
| **v5.4.3** | 增强智能 RAG 上下文辅助（`auto/graph_hybrid` 回退 BM25）。 |
| **v5.3** | 引入追读力系统（Hook/Cool-point/微兑现/债务追踪）。 |

## 开源协议

本项目使用 `GPL v3` 协议，详见 `LICENSE`。

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=lingfengQAQ/webnovel-writer&type=Date)](https://star-history.com/#lingfengQAQ/webnovel-writer&Date)

## 致谢

本项目采用多工具协同开发流程（包含 Gemini CLI、Codex 等）。

灵感来源：[Linux.do 帖子](https://linux.do/t/topic/1397944/49)

## 贡献

欢迎提交 Issue 和 PR：

```bash
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
```
