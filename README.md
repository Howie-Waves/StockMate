# StockMate (股搭子)

> 智能股票投资辅助 Agent 系统 - 基于多智能体协作的量化分析平台

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 项目简介

**StockMate (股搭子)** 是一个面向 A 股普通股民的智能投资辅助 Agent。系统基于 `smolagents` 框架构建，采用多智能体协作模式，结合传统量化数据和 LLM 对非结构化数据的处理能力，为用户提供专业的股票分析报告。

### 核心理念

> 从"拼手速"转向"拼理解"

- **零幻觉机制**: 所有结论基于真实数据，禁止编造
- **量化回测验证**: 用历史数据验证策略有效性
- **风控一票否决**: 风险超标时强制否决所有买入信号

---

## 技术架构

| 组件 | 技术 |
|------|------|
| Agent 框架 | `smolagents` (Hugging Face) |
| 数据源 | `akshare` (全量 A 股数据) |
| 回测引擎 | `vectorbt` (向量化回测) |
| 数据建模 | `pydantic` (类型安全) |
| 前端界面 | `streamlit` (美观 Web UI) |

---

## 智能体团队

```
┌─────────────────────────────────────────────────────┐
│                  Decision Agent                      │
│              (基金经理 - Orchestrator)               │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Perception│  │  Macro   │  │ Technical│         │
│  │   Agent  │  │  Agent   │  │  Agent   │         │
│  │(感知者)  │  │(宏观分析师)│ │(技术分析师)│        │
│  └──────────┘  └──────────┘  └──────────┘         │
│         │              │              │             │
│         └──────────────┼──────────────┘             │
│                        │                            │
│                 ┌──────┴──────┐                    │
│                 │  Risk Agent │                    │
│                 │  (风控官)   │                    │
│                 │ 一票否决权  │                    │
│                 └─────────────┘                    │
└─────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 环境要求

- **Python**: 3.11 或更高版本
- **操作系统**: Windows / macOS / Linux

### 2. 克隆项目

```bash
cd "D:\Howie Waves\StockMate"
```

### 3. 创建虚拟环境

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 配置环境变量

复制 `.env.template` 为 `.env` 并配置：

```bash
cp .env.template .env
```

编辑 `.env` 文件，填入您的配置：

```env
# LLM API 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini

# 或者使用国内服务
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# MODEL_NAME=deepseek-chat
```

> **注意**: 如果只使用本地分析模式，不需要配置 API Key。

---

## 运行方式

### 方式一: Web UI 界面 (推荐)

```bash
streamlit run app.py
```

然后在浏览器中打开 `http://localhost:8501`

### 方式二: 命令行模式

```bash
# 分析单只股票 (自动选择模式)
python main.py 600000

# 使用本地模式分析
python main.py 600000 --mode local

# 使用 LLM 模式分析
python main.py 600000 --mode llm

# 仅获取数据
python main.py 600000 --data-only

# 仅获取新闻
python main.py 600000 --news-only

# 运行回测
python main.py 600000 --backtest RSI

# 批量分析
python main.py --batch stocks.txt
```

---

## 项目结构

```
StockMate/
├── stockmate/              # 主包
│   ├── __init__.py
│   ├── models.py           # Pydantic 数据模型
│   ├── agents.py           # Agent 配置和逻辑
│   ├── tools/              # 工具集
│   │   ├── __init__.py
│   │   └── stock_tools.py  # 股票数据/新闻/回测工具
│   ├── config/             # 配置文件目录
│   ├── agents/             # Agent 定义目录
│   └── backtest/           # 回测逻辑目录
├── app.py                  # Streamlit Web UI
├── main.py                 # 命令行入口
├── requirements.txt        # 依赖列表
├── .env.template           # 环境变量模板
├── requirements.md         # 项目需求文档
└── README.md               # 本文件
```

---

## 使用示例

### Python 代码调用

```python
from stockmate.agents import analyze_stock_pipeline
from stockmate.models import StockAnalysisReport

# 使用本地管道分析
report = analyze_stock_pipeline("600000")

# 打印报告
print(report.model_dump_json())
```

### 命令行输出示例

```
╔══════════════════════════════════════════════════════════════╗
║                    StockMate (股搭子)                        ║
║               智能股票投资辅助 Agent 系统                      ║
║                  v0.1.0 - MVP 版本                           ║
╚══════════════════════════════════════════════════════════════╝

🔍 正在使用本地分析模式分析股票 600000...
⏳ 请稍候...

============================================================
📊 股票分析报告
============================================================

🏷️  股票代码: 600000
⏰ 分析时间: 2024-01-15 14:30:00

🟢 最终决策: **Buy**

📈 分析指标:
----------------------------------------
  情绪评分:     65.5 / 100
  技术信号:     Buy
  风控评估:     Approved
  波动率:       23.45%

📊 回测验证:
----------------------------------------
  历史胜率:     68.5%
  历史收益:     24.3%

💡 决策依据:
----------------------------------------
  市场情绪积极 (65.5/100)；技术面显示买入信号；回测显示历史胜率 68.5%，收益率 24.3%

============================================================
```

---

## 支持的策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **RSI** | 相对强弱指标，超卖/超买信号 | 震荡市场 |
| **MA** | 移动平均线交叉 | 趋势市场 |
| **Bollinger** | 布林带突破 | 波动率突破 |

---

## 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。

- ⚠️ 股票投资有风险，入市需谨慎
- 📊 历史回测结果不代表未来表现
- 🔔 请结合自身风险承受能力做出投资决策

---

## 开发计划

- [x] MVP 版本发布
- [ ] 支持更多技术指标
- [ ] 添加自定义策略功能
- [ ] 支持港股和美股
- [ ] 移动端适配

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License

---

**StockMate Team** © 2026
