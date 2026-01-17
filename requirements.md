# Role & Objective
你现在是世界顶级的 AI 量化架构师（Quant Architect），精通 Python 金融生态（尤其是 AkShare）和 Hugging Face 的 `smolagents` 框架。

你的任务是协助我开发 **"StockMate (股搭子)"** 的 MVP 版本。这是一个面向 A 股普通股民的智能投资辅助 Agent。

# Project Philosophy
1. **核心理念**：从“拼手速”转向“拼理解”。利用 LLM 处理非结构化数据（新闻、情绪），结合传统量化数据（价格、指标）。 
2.  **架构模式**：基于 **CrewAI** 框架的多智能体协作（Multi-Agent Collaboration）。 
3. **核心约束**：必须具备“零幻觉”机制（RAG/数据引用）和“量化回测”验证（Backtesting）。
4. **开发阶段**：目前为 MVP（最小可行性产品）Demo 阶段，但代码结构必须为未来扩展（Scaling）预留接口。
5. **结构化思维**：拒绝模糊的文本输出。系统内部必须通过 Pydantic 对象传递信息，确保决策的严谨性。

1. **历史为鉴**：必须包含回测机制，用历史数据验证策略有效性。

   

# Tech Stack Specifications (Strict)
- **Language**: Python 3.11.14
- **Agent Framework**: `smolagents` (Hugging Face) 
- **Data Source**: `akshare` (全量数据源)。
- **Data Modeling**: `Pydantic` (用于定义最终输出报告和中间数据结构)。
- **Backtesting**: `vectorbt` (用于快速向量化回测)。
- **LLM**: 通过 `smolagents.LiteLLMModel` 或 `OpenAIServerModel` 调用。

# Architecture Design 
基于 `smolagents` 框架，本系统采用 **Managed Agents (多智能体协作)** 与 **Tools (工具调用)** 相结合的模式。请严格遵循以下架构定义和职能划分：

### 1. 核心数据协议 (Data Protocol)
所有 Agent 间的最终交互必须收敛于统一的数据结构。请定义如下 `Pydantic` 模型作为最终输出标准：
*   **`StockAnalysisReport`**:
    *   `ticker` (str): 股票代码
    *   `sentiment_score` (float): 0-100，宏观/新闻情感分
    *   `technical_signal` (str): Buy / Sell / Hold
    *   `risk_assessment` (str): Approved / Rejected (基于风控一票否决)
    *   `var_value` (float): 在险价值或波动率数值
    *   `final_decision` (str): 最终操作建议
    *   `reasoning` (str): 决策逻辑链摘要

### 2. 工具集定义 (Tool Specifications)
请实现以下 Python 工具供 Agent 调用：
*   **`MarketDataTool`**:
    *   **接口**: 封装 `akshare` 获取个股历史行情。
    *   **强制约束**: AkShare 返回的中文列名**必须**在工具内部重命名为英文 (`Open`, `High`, `Low`, `Close`, `Volume`)，以确保后续兼容 `vectorbt`。
*   **`NewsTool`**:
    *   **接口**: 使用 `ak.stock_news_em` (或同类) 获取个股实时新闻与公告。
*   **`BacktestTool`**:
    *   **引擎**: `vectorbt`。
    *   **功能**: 接收动态策略参数（如 `"RSI < 30"`），在历史数据上进行快速回测，返回胜率 (`Win Rate`) 和收益率 (`Return`)。

### 3. 智能体职能 (The AI Virtual Team)
系统由以下 5 个原子化 Agent 组成，由 **Decision Agent** 统一编排：

1.  **Perception Agent (感知者)**
    *   **职责**: 信息搜集。调用 `MarketDataTool` 和 `NewsTool` 获取原始数据（OHLCV + 新闻文本），作为下游 Agent 的输入上下文。
2.  **Macro Agent (宏观分析师)**
    *   **职责**: 趋势定性。基于新闻上下文分析宏观环境（牛/熊/震荡），输出情感评分。
3.  **Technical Agent (技术分析师)**
    *   **职责**: 量化分析。
    *   计算技术指标 (MACD, Bollinger, RSI)。
    *   调用 `BacktestTool` 验证当前信号的历史有效性，输出技术面建议 (Buy/Sell)。
4.  **Risk Agent (风控官)**
    *   **核心机制**: **拥有“一票否决权” (Veto Power)**。这是逻辑强制层，非单纯 LLM 聊天。
    *   **逻辑**: 计算波动率和最大回撤。若风险指标超标，强制返回 `Rejected`。此时无论其他 Agent 信号多么强烈，最终决策只能是 "Wait"。
5.  **Decision Agent (基金经理 - Orchestrator)**
    *   **职责**: 汇总与裁决。
    *   按序调用上述 Agent。
    *   综合 Macro (情绪)、Technical (信号+回测)、Risk (合规) 的结果。
    *   **输出**: 填充并返回 `StockAnalysisReport` 对象。**严禁编造数据**，必须引用子 Agent 的返回结果。

# Execution Plan (Step-by-Step)

**Objective**: Implement the stockmate_smol system using smolagents. The system operates as a single logic-driven entity with strict functional phases (Perception -> Analysis -> Risk -> Decision).

## Step 1: Project Setup
创建以下目录结构： 

- `stockmate/`  
  - `config/`
  - `tools/` (存放自定义工具)  
  - `agents/` (存放 agent 定义)  
  - `backtest/` (存放 vectorbt 回测逻辑)
- `.env`(模板) 
- `main.py` 
- `requirements.txt`

## Step 2: Dependencies (`requirements.txt`)
包含: `smolagents`, `akshare`, `pandas`, `numpy`, `vectorbt`, `pydantic`, `python-dotenv`等

## Step 3: Data Structures (`models.py`)
定义 Pydantic 模型 StockAnalysisReport 作为智能体最终输出的严格标准。所有决策逻辑必须收敛于此结构：

- **字段定义**：
  - ticker (str): 股票代码。
  - sentiment_score (float): 0-100 的评分，代表市场/新闻情绪。
  - technical_signal (str): 枚举值 "Buy", "Sell", "Hold"。
  - risk_assessment (str): 枚举值 "Approved" 或 "Rejected"。**关键**：这是风控的核心字段。
  - var_value (float): 在险价值 (VaR) 或波动率数值。
  - final_decision (str): 枚举值 "Buy", "Sell", "Wait"。
  - reasoning (str): 决策逻辑链的文字摘要。

## Step 4: Core Tools Implementation (`tools/`)
编写 `stock_tools.py`，使用 `@tool` 装饰器定义以下三个核心函数：

**A. get_a_share_data(symbol: str)**

- **数据源**：akshare (日线历史数据)。
- **强制约束**：AkShare 返回的 DataFrame 列名为中文，**必须**在工具内部将其重命名为标准英文，以兼容 vectorbt。
  - 映射关系：{'开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'}。
- **输出**：DataFrame 的 JSON 描述或轻量级摘要。

**B. get_latest_news(symbol: str)**

- **数据源**：akshare.stock_news_em (或同类接口)。
- **输出**：最近 10 条新闻的标题和内容摘要。

**C. run_backtest(symbol: str, strategy_type: str)**

- **引擎**：vectorbt。
- **逻辑**：调用工具 A 获取数据，应用指定策略逻辑（如 "RSI" 或 "均线策略"），并在历史数据上运行回测。
- **输出**：包含胜率 (win_rate) 和总收益率 (total_return) 的字典。

## Step 5: Agent Configuration (`agents.py`)
初始化一个主 CodeAgent。

- **系统提示词 (System Prompt) 规范**：
  在 System Prompt 中植入“多重人格”逻辑。智能体必须严格遵守以下内部工作流：
  1. **感知阶段 (Perception)**：调用工具获取行情数据和新闻资讯。
  2. **分析阶段 (Analysis)**：分析新闻情感；调用回测工具验证技术指标。
  3. **风控守门阶段 (Risk Gatekeeper - 强制性)**：基于数据计算波动率或回测。**约束**：如果风险指标过高，强制将 risk_assessment 设为 "Rejected"。此判定具有一票否决权，覆盖所有 "Buy" 信号。
  4. **报告阶段 (Reporting)**：构造并返回严格符合 StockAnalysisReport 格式的 JSON 对象。

## Step 6: Main Entry (`main.py`)
- 加载环境变量。
- 初始化 Agent。
- 编写一个 helper function `analyze_stock(symbol)`。（**关键点**：由于 AkShare 的代码通常是 "600000" 这种格式，不管是 ".SH" 还是纯数字，需要处理好代码格式兼容性。）
- 执行测试运行，并打印最终的 Pydantic 结果对象。

# Coding Guidelines & Constraints
1.  **AkShare Stability**: AkShare 的接口偶尔会变动，请使用最经典、最稳定的接口（如 `stock_zh_a_hist` 用于行情）。
2.  **VectorBT Integration**: VectorBT 极其依赖标准的 Index (Datetime) 和 Columns (Open, High, Low, Close)。务必在 Tool 内部做好数据清洗，不要把脏数据抛给 Agent。
3.  **No Strings Attached**: 最终输出不要只给一堆文本，尝试让 Agent 的最后一步是填充 Pydantic 模型并打印 `model_dump_json()`。
4.  **Error Handling**: 如果 AkShare 请求超时或失败，Tool 应该返回清晰的错误信息，而不是让程序崩溃。
5.  **Modular**: 代码必须高内聚低耦合。 
6.  **Error Handling**: 网络请求（yfinance/search）必须有 try-except。
7.  **Comments**: 关键逻辑（特别是风控和回测部分）必须有中文注释。
8.  **Type Hinting**: 所有函数必须包含 Python 类型提示。
9.  **No Hallucination**: 在 System Prompt 中注入指令，要求 Agent 在输出结论时，必须附带数据来源（Source Citation）。



现在，请开始执行。首先创建项目结构和 `requirements.txt`，然后依次生成代码文件。