"""
StockMate Agent 配置
基于 smolagents 的智能分析系统
"""

import os
from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, tool
from stockmate.tools.stock_tools import get_stock_info, get_stock_news, backtest_strategy
from stockmate.models import StockAnalysisReport
import json

# 加载环境变量
load_dotenv()

# 系统提示词 - 核心决策逻辑
STOCKMATE_SYSTEM_PROMPT = """
你现在是 StockMate (股搭子) - 一个专业的A股投资分析助手。你必须严格按照以下流程进行分析：

## 📋 分析工作流（必须严格遵守）

### 第一阶段：感知阶段
1. 调用 `get_stock_info` 获取股票的 OHLCV 数据和统计信息
2. 调用 `get_stock_news` 获取最新的新闻和公告
3. 记录当前价格、涨跌幅、波动率等关键数据

### 第二阶段：分析阶段
1. **宏观/新闻分析**：基于新闻内容，评估市场情绪
   - 统计正面/负面新闻数量
   - 评估新闻情感（0-100分，100为极度看涨）
   - 分析宏观环境和行业趋势

2. **技术分析**：
   - 分析价格趋势和成交量变化
   - 评估支撑位和压力位
   - 调用 `backtest_strategy` 验证技术策略的历史表现
   - 支持的策略类型: "RSI"（超卖/超买）、"MA"（均线交叉）、"Bollinger"（布林带）

### 第三阶段：风控守门阶段（强制性）
这是系统最重要的安全机制，具有一票否决权：

1. 计算风险指标：
   - 波动率（Volatility）：从 stock_info 中获取
   - 最大回撤（Max Drawdown）：从 stock_info 中获取

2. 风控判定逻辑：
   ```
   IF 波动率 > 50% OR 最大回撤 > 20%:
       risk_assessment = "Rejected"
       无论其他信号多么强烈，最终决策必须是 "Wait"
   ELSE:
       risk_assessment = "Approved"
   ```

### 第四阶段：报告阶段
你必须以 JSON 格式输出最终的 StockAnalysisReport。格式如下：

```json
{
  "ticker": "股票代码",
  "sentiment_score": 情绪评分(0-100),
  "technical_signal": "Buy/Sell/Hold",
  "risk_assessment": "Approved/Rejected",
  "var_value": 波动率数值,
  "final_decision": "Buy/Sell/Wait",
  "reasoning": "详细的决策逻辑链，必须引用数据来源",
  "backtest_win_rate": 回测胜率,
  "backtest_return": 回测收益率
}
```

## ⚠️ 关键约束

1. **零幻觉原则**：所有结论必须有数据支撑，禁止编造数据
2. **风控优先**：risk_assessment = "Rejected" 时，final_decision 必须是 "Wait"
3. **数据引用**：reasoning 中必须明确说明数据来源（如："根据回测显示..."、"新闻中提到..."）
4. **格式严格**：最终输出必须是合法的 JSON 格式

## 📊 决策参考标准

| 指标 | 强买入 | 买入 | 观望 | 卖出 |
|------|--------|------|------|------|
| 情绪分 | >70 | 60-70 | 40-60 | <40 |
| 回测胜率 | >60% | 55-60% | 50-55% | <50% |
| 风控状态 | Approved | Approved | - | - |

请开始分析，并在最后以 ```json ... ``` 的格式输出报告。
"""


def create_stockmate_agent(
    model_name: str = None, api_key: str = None, base_url: str = None
):
    """
    创建 StockMate 分析 Agent

    Args:
        model_name: 模型名称，默认从环境变量读取
        api_key: API密钥，默认从环境变量读取
        base_url: API地址，默认从环境变量读取

    Returns:
        配置好的 CodeAgent 实例
    """
    # 从环境变量获取配置
    model_name = model_name or os.getenv("MODEL_NAME", "gpt-4o-mini")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    if not api_key:
        raise ValueError(
            "未找到 OPENAI_API_KEY，请在 .env 文件中配置或传入 api_key 参数"
        )

    # 初始化模型
    model = LiteLLMModel(
        model_name=model_name,
        api_key=api_key,
        api_base=base_url,
    )

    # 创建 Agent，注册工具
    agent = CodeAgent(
        tools=[get_stock_info, get_stock_news, backtest_strategy],
        model=model,
        system_prompt=STOCKMATE_SYSTEM_PROMPT,
        max_iterations=15,
    )

    return agent


def parse_agent_response(response: str) -> StockAnalysisReport:
    """
    解析 Agent 响应，提取 StockAnalysisReport

    Args:
        response: Agent 的原始响应文本

    Returns:
        StockAnalysisReport 对象
    """
    try:
        # 尝试提取 JSON 部分
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            return StockAnalysisReport(**data)
        else:
            raise ValueError("响应中未找到 JSON 格式的报告")

    except Exception as e:
        # 如果解析失败，返回一个包含错误信息的报告
        return StockAnalysisReport(
            ticker="UNKNOWN",
            sentiment_score=50.0,
            technical_signal="Hold",
            risk_assessment="Rejected",
            var_value=0.0,
            final_decision="Wait",
            reasoning=f"解析 Agent 响应失败: {str(e)}。原始响应: {response[:500]}",
        )


def analyze_stock(symbol: str, agent: CodeAgent = None) -> StockAnalysisReport:
    """
    分析单只股票

    Args:
        symbol: 股票代码（如 "600000" 或 "000001"）
        agent: 可选的 Agent 实例，如果不提供则创建新的

    Returns:
        StockAnalysisReport 对象
    """
    # 如果没有传入 Agent，创建一个
    if agent is None:
        agent = create_stockmate_agent()

    # 标准化股票代码
    if "." in symbol:
        symbol = symbol.split(".")[0]
    symbol = symbol.strip().zfill(6)

    # 构建分析提示词
    prompt = f"""请分析股票 {symbol}，并按照系统提示词的要求进行分析。

请按以下步骤操作：
1. 使用 get_stock_info("{symbol}") 获取行情数据
2. 使用 get_stock_news("{symbol}") 获取最新新闻
3. 使用 backtest_strategy("{symbol}", "RSI") 进行 RSI 策略回测
4. 综合分析并以 JSON 格式输出 StockAnalysisReport

注意：请务必先调用工具获取实际数据，然后再进行分析。"""

    try:
        # 运行 Agent
        response = agent.run(prompt)

        # 解析响应
        report = parse_agent_response(str(response))
        report.ticker = symbol  # 确保 ticker 正确

        return report

    except Exception as e:
        # 返回错误报告
        return StockAnalysisReport(
            ticker=symbol,
            sentiment_score=50.0,
            technical_signal="Hold",
            risk_assessment="Rejected",
            var_value=0.0,
            final_decision="Wait",
            reasoning=f"分析过程中发生错误: {str(e)}",
        )


# 辅助 Agent 类 - 用于不同分析阶段


class PerceptionAgent:
    """感知阶段 Agent - 负责数据收集"""

    @staticmethod
    def collect(symbol: str) -> dict:
        """收集股票的行情和新闻数据"""
        from stockmate.tools.stock_tools import get_a_share_data, get_latest_news

        market_data = get_a_share_data(symbol)
        news_data = get_latest_news(symbol)

        return {
            "market_data": market_data,
            "news_data": news_data,
        }


class MacroAgent:
    """宏观分析 Agent - 负责情绪分析"""

    @staticmethod
    def analyze(news_data: dict) -> float:
        """
        分析新闻情绪

        Returns:
            情绪评分 (0-100)
        """
        if not news_data.get("success"):
            return 50.0  # 中性

        # 简单的关键词分析
        positive_keywords = ["增长", "利好", "突破", "上涨", "盈利", "业绩"]
        negative_keywords = ["下跌", "亏损", "风险", "警告", "下跌", "调整"]

        score = 50.0  # 基准分
        news_count = 0

        for news in news_data.get("news", []):
            title = news.get("title", "")
            content = news.get("content", "")
            text = title + content

            for keyword in positive_keywords:
                if keyword in text:
                    score += 3
            for keyword in negative_keywords:
                if keyword in text:
                    score -= 3

            news_count += 1

        # 限制在 0-100 范围内
        return max(0, min(100, score))


class TechnicalAgent:
    """技术分析 Agent - 负责技术指标和回测"""

    @staticmethod
    def analyze(symbol: str, market_data: dict) -> dict:
        """
        进行技术分析

        Returns:
            技术分析结果
        """
        from stockmate.tools.stock_tools import run_backtest

        # 运行回测
        backtest_result = run_backtest(symbol, "RSI")

        # 简单的技术判断
        signal = "Hold"
        if market_data.get("success"):
            change_pct = market_data.get("change_pct", 0)
            if change_pct > 3:
                signal = "Buy"
            elif change_pct < -3:
                signal = "Sell"

        return {
            "signal": signal,
            "backtest": backtest_result,
            "change_pct": market_data.get("change_pct", 0),
        }


class RiskAgent:
    """风控 Agent - 拥有一票否决权"""

    @staticmethod
    def evaluate(market_data: dict, max_volatility: float = 50, max_drawdown: float = 20) -> dict:
        """
        风控评估

        Args:
            market_data: 市场数据
            max_volatility: 最大可接受波动率
            max_drawdown: 最大可接受回撤

        Returns:
            风控评估结果
        """
        if not market_data.get("success"):
            return {
                "approved": False,
                "reason": "无法获取市场数据进行风控评估",
            }

        stats = market_data.get("statistics", {})
        volatility = stats.get("volatility", 0)
        drawdown = abs(stats.get("max_drawdown", 0))

        # 风控判定逻辑
        if volatility > max_volatility or drawdown > max_drawdown:
            return {
                "approved": False,
                "reason": f"风控否决：波动率 {volatility:.2f}% 或回撤 {drawdown:.2f}% 超过阈值",
                "volatility": volatility,
                "drawdown": drawdown,
            }

        return {
            "approved": True,
            "reason": f"风控通过：波动率 {volatility:.2f}%，回撤 {drawdown:.2f}% 在可接受范围内",
            "volatility": volatility,
            "drawdown": drawdown,
        }


class DecisionAgent:
    """决策 Agent - 综合所有信息做出最终决策"""

    @staticmethod
    def decide(
        symbol: str,
        sentiment_score: float,
        technical_signal: str,
        risk_approved: bool,
        volatility: float,
        backtest_result: dict = None,
    ) -> StockAnalysisReport:
        """
        综合决策

        Args:
            symbol: 股票代码
            sentiment_score: 情绪评分
            technical_signal: 技术信号
            risk_approved: 风控是否通过
            volatility: 波动率
            backtest_result: 回测结果

        Returns:
            最终的分析报告
        """
        # 风控一票否决
        if not risk_approved:
            return StockAnalysisReport(
                ticker=symbol,
                sentiment_score=sentiment_score,
                technical_signal=technical_signal,
                risk_assessment="Rejected",
                var_value=volatility,
                final_decision="Wait",
                reasoning=f"风控否决：波动率过高，建议等待风险释放后再考虑入场。虽然情绪评分 {sentiment_score:.1f}，技术信号为 {technical_signal}，但安全第一。",
                backtest_win_rate=backtest_result.get("win_rate") if backtest_result else None,
                backtest_return=backtest_result.get("total_return") if backtest_result else None,
            )

        # 综合决策逻辑
        decision = "Wait"
        reasoning_parts = []

        # 情绪分析
        if sentiment_score > 70:
            reasoning_parts.append(f"市场情绪积极 ({sentiment_score:.1f}/100)")
            decision = "Buy"
        elif sentiment_score < 40:
            reasoning_parts.append(f"市场情绪低迷 ({sentiment_score:.1f}/100)")
            decision = "Sell"
        else:
            reasoning_parts.append(f"市场情绪中性 ({sentiment_score:.1f}/100)")

        # 技术分析
        if technical_signal == "Buy":
            reasoning_parts.append(f"技术面显示买入信号")
            if decision != "Sell":
                decision = "Buy"
        elif technical_signal == "Sell":
            reasoning_parts.append(f"技术面显示卖出信号")
            decision = "Sell"

        # 回测验证
        if backtest_result and backtest_result.get("success"):
            win_rate = backtest_result.get("win_rate", 0)
            total_return = backtest_result.get("total_return", 0)
            reasoning_parts.append(
                f"回测显示历史胜率 {win_rate:.1f}%，收益率 {total_return:.1f}%"
            )
            if win_rate > 60 and decision != "Sell":
                decision = "Buy"

        return StockAnalysisReport(
            ticker=symbol,
            sentiment_score=sentiment_score,
            technical_signal=technical_signal,
            risk_assessment="Approved",
            var_value=volatility,
            final_decision=decision,
            reasoning="；".join(reasoning_parts),
            backtest_win_rate=backtest_result.get("win_rate") if backtest_result else None,
            backtest_return=backtest_result.get("total_return") if backtest_result else None,
        )


def analyze_stock_pipeline(symbol: str) -> StockAnalysisReport:
    """
    使用 Agent 管道分析股票（不依赖 LLM）

    这是一个快速版本，使用本地逻辑而非 LLM 进行分析。

    Args:
        symbol: 股票代码

    Returns:
        StockAnalysisReport 对象
    """
    # 标准化代码
    if "." in symbol:
        symbol = symbol.split(".")[0]
    symbol = symbol.strip().zfill(6)

    # 感知阶段：收集数据
    perception = PerceptionAgent.collect(symbol)

    # 宏观分析：情绪评分
    sentiment_score = MacroAgent.analyze(perception["news_data"])

    # 技术分析
    technical = TechnicalAgent.analyze(symbol, perception["market_data"])

    # 风控评估
    risk = RiskAgent.evaluate(perception["market_data"])

    # 最终决策
    report = DecisionAgent.decide(
        symbol=symbol,
        sentiment_score=sentiment_score,
        technical_signal=technical["signal"],
        risk_approved=risk["approved"],
        volatility=risk.get("volatility", 0),
        backtest_result=technical.get("backtest"),
    )

    return report


if __name__ == "__main__":
    # 测试代码
    print("=== 测试 Agent 管道 ===")
    report = analyze_stock_pipeline("600000")
    print(report.model_dump_json())
