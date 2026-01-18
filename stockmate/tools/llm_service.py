"""
StockMate LLM 服务模块
使用 DeepSeek API 生成智能的市场分析和解释
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建 OpenAI 客户端（使用 DeepSeek API）
_client = None

# 缓存生成的解释（避免重复调用）
_EXPLANATION_CACHE: Dict[str, str] = {}


def get_llm_client():
    """获取 LLM 客户端"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        if api_key:
            try:
                _client = OpenAI(api_key=api_key, base_url=base_url)
                return _client
            except Exception as e:
                print(f"创建 LLM 客户端失败: {e}")
                return None
        else:
            print("未配置 OPENAI_API_KEY 环境变量")
            return None
    return _client


def generate_llm_explanation(
    prompt: str,
    max_tokens: int = 150,
    cache_key: Optional[str] = None
) -> str:
    """
    使用 LLM 生成解释文本

    Args:
        prompt: 提示词
        max_tokens: 最大生成的 token 数（控制长度）
        cache_key: 缓存键（可选）

    Returns:
        生成的解释文本
    """
    # 检查缓存
    if cache_key and cache_key in _EXPLANATION_CACHE:
        return _EXPLANATION_CACHE[cache_key]

    # 获取客户端
    llm_client = get_llm_client()
    if llm_client is None:
        # 如果 LLM 不可用，返回默认文本
        return "暂无智能分析（请配置 API Key）"

    try:
        model_name = os.getenv("MODEL_NAME", "deepseek-chat")

        response = llm_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的股票分析师。请用简洁、专业的中文回答问题。控制字数在50字以内，不要使用markdown格式。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )

        explanation = response.choices[0].message.content.strip()

        # 缓存结果
        if cache_key:
            _EXPLANATION_CACHE[cache_key] = explanation

        return explanation

    except Exception as e:
        # 出错时返回简单解释
        return f"分析生成失败: {str(e)}"


def generate_market_trend_description(
    symbol: str,
    current_price: float,
    change_pct: float,
    max_tokens: int = 100
) -> str:
    """
    生成价格走势描述

    Args:
        symbol: 股票代码
        current_price: 当前价格
        change_pct: 涨跌幅
        max_tokens: 最大 token 数

    Returns:
        走势描述文本
    """
    trend = "上涨" if change_pct > 0 else "下跌" if change_pct < 0 else "持平"
    magnitude = "大幅" if abs(change_pct) > 3 else "小幅" if abs(change_pct) > 0 else ""

    prompt = f"""
    股票 {symbol} 当前价格为 {current_price:.2f} 元，
    今日{magnitude}{trend} {abs(change_pct):.2f}%。
    请用一句话描述这个价格走势的含义和可能的影响。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"trend_{symbol}_{current_price}_{change_pct}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_volatility_interpretation(
    var_value: float,
    volatility_level: str,
    max_tokens: int = 80
) -> str:
    """
    生成波动率解读

    Args:
        var_value: 波动率数值
        volatility_level: 波动率等级（低/中/高）
        max_tokens: 最大 token 数

    Returns:
        波动率解读文本
    """
    prompt = f"""
    当前股票的波动率为 {var_value:.2f}%，属于{volatility_level}水平。
    请用一句话解释这对投资者意味着什么。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"volatility_{var_value}_{volatility_level}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_sentiment_interpretation(
    sentiment_score: float,
    sentiment_level: str,
    max_tokens: int = 80
) -> str:
    """
    生成市场情绪解读

    Args:
        sentiment_score: 情绪评分
        sentiment_level: 情绪等级
        max_tokens: 最大 token 数

    Returns:
        情绪解读文本
    """
    prompt = f"""
    当前市场情绪评分为 {sentiment_score:.1f} 分（满分100分），整体情绪{sentiment_level}。
    请用一句话解释这对股价可能产生的影响。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"sentiment_{sentiment_score}_{sentiment_level}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_technical_signal_interpretation(
    technical_signal: str,
    max_tokens: int = 100
) -> str:
    """
    生成技术信号解读

    Args:
        technical_signal: 技术信号
        max_tokens: 最大 token 数

    Returns:
        技术信号解读文本
    """
    signal_map = {
        "黄金交叉": "短期均线上穿长期均线",
        "死亡交叉": "短期均线下穿长期均线",
        "超卖": "RSI指标显示超卖",
        "超买": "RSI指标显示超买",
        "看涨": "多个技术指标看涨",
        "看跌": "多个技术指标看跌",
        "中性": "技术指标没有明确方向"
    }

    signal_desc = signal_map.get(technical_signal, technical_signal)

    prompt = f"""
    技术分析显示 {signal_desc}（{technical_signal}）。
    请用一句话解释这个技术信号对投资者的参考价值。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"technical_{technical_signal}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_opportunity_assessment(
    sentiment_score: float,
    technical_signal: str,
    change_pct: float,
    max_tokens: int = 120
) -> str:
    """
    生成投资机会评估

    Args:
        sentiment_score: 情绪评分
        technical_signal: 技术信号
        change_pct: 价格涨跌幅
        max_tokens: 最大 token 数

    Returns:
        机会评估文本
    """
    prompt = f"""
    市场情绪评分 {sentiment_score:.1f} 分，
    技术信号为 {technical_signal}，
    股价今日{change_pct:+.2f}%。
    请用两句话评估当前是否适合入场，以及需要注意什么。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"opportunity_{sentiment_score}_{technical_signal}_{change_pct}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_risk_assessment(
    var_value: float,
    risk_assessment: str,
    volatility_level: str,
    max_tokens: int = 100
) -> str:
    """
    生成风险评估

    Args:
        var_value: 波动率
        risk_assessment: 风险评估结果
        volatility_level: 波动率等级
        max_tokens: 最大 token 数

    Returns:
        风险评估文本
    """
    approved = risk_assessment == "Approved"

    prompt = f"""
    当前波动率为 {var_value:.2f}%（{volatility_level}），
    风控系统{'已通过' if approved else '已否决'}此交易。
    请用一句话解释这对投资者的意义。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"risk_{var_value}_{risk_assessment}_{volatility_level}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_backtest_summary(
    win_rate: float,
    total_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    total_trades: int,
    strategy: str,
    max_tokens: int = 150
) -> str:
    """
    生成回测结果总结

    Args:
        win_rate: 胜率
        total_return: 总收益率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        total_trades: 总交易次数
        strategy: 策略名称
        max_tokens: 最大 token 数

    Returns:
        回测总结文本
    """
    prompt = f"""
    {strategy}策略回测结果：
    胜率 {win_rate:.1f}%，
    总收益率 {total_return:+.2f}%，
    夏普比率 {sharpe_ratio:.2f}，
    最大回撤 {max_drawdown:.2f}%，
    总交易 {total_trades} 次。
    请用三句话评价这个策略的表现和适用性。
    不要使用标点符号和markdown格式。
    """

    cache_key = f"backtest_{strategy}_{win_rate}_{total_return}_{sharpe_ratio}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_comprehensive_analysis(
    symbol: str,
    company_name: str,
    current_price: float,
    change_pct: float,
    sentiment_score: float,
    technical_signal: str,
    win_rate: Optional[float] = None,
    total_return: Optional[float] = None,
    max_tokens: int = 300
) -> str:
    """
    生成全面的股票分析报告

    Args:
        symbol: 股票代码
        company_name: 公司名称
        current_price: 当前价格
        change_pct: 涨跌幅
        sentiment_score: 情绪评分
        technical_signal: 技术信号
        win_rate: 回测胜率（可选）
        total_return: 回测收益率（可选）
        max_tokens: 最大 token 数

    Returns:
        综合分析报告
    """
    backtest_info = ""
    if win_rate is not None and total_return is not None:
        backtest_info = f"历史回测胜率 {win_rate:.1f}%，总收益率 {total_return:.1f}%。"

    prompt = f"""
    作为专业股票分析师，请对 {company_name}（{symbol}）进行全面分析：

    当前价格：{current_price:.2f} 元
    今日涨跌：{change_pct:+.2f}%
    市场情绪：{sentiment_score:.1f} 分
    技术信号：{technical_signal}
    {backtest_info}

    请从以下角度进行分析（控制在200字以内）：
    1. 短期走势判断
    2. 关键风险提示
    3. 投资建议（买入/持有/观望/卖出）

    直接输出分析结论，不要标题和格式标记。
    """

    cache_key = f"comprehensive_{symbol}_{current_price}_{sentiment_score}_{technical_signal}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_industry_analysis(
    symbol: str,
    sector: str,
    sentiment_score: float,
    max_tokens: int = 200
) -> str:
    """
    生成行业板块分析

    Args:
        symbol: 股票代码
        sector: 所属板块
        sentiment_score: 情绪评分
        max_tokens: 最大 token 数

    Returns:
        板块分析
    """
    prompt = f"""
    {symbol} 属于 {sector} 板块。
    当前市场情绪评分为 {sentiment_score:.1f} 分。

    请分析：
    1. 该板块的整体走势特征
    2. 当前情绪水平对板块的影响
    3. 投资该板块股票需要注意的关键因素

    控制在150字以内，直接输出分析内容。
    """

    cache_key = f"industry_{symbol}_{sector}_{sentiment_score}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_risk_warning(
    symbol: str,
    volatility: float,
    max_drawdown: float,
    position_size: float,
    max_tokens: int = 200
) -> str:
    """
    生成风险提示

    Args:
        symbol: 股票代码
        volatility: 波动率
        max_drawdown: 最大回撤
        position_size: 建议仓位比例
        max_tokens: 最大 token 数

    Returns:
        风险提示文本
    """
    risk_level = "高" if volatility > 5 else "中" if volatility > 3 else "低"

    prompt = f"""
    {symbol} 的风险分析：
    波动率：{volatility:.2f}%（{risk_level}风险）
    历史最大回撤：{max_drawdown:.2f}%
    建议仓位：{position_size*100:.1f}%

    请生成具体的风险提示，包括：
    1. 当前风险水平说明
    2. 仓位控制建议
    3. 止损止盈设置建议

    控制在150字以内，直接输出内容。
    """

    cache_key = f"risk_{symbol}_{volatility}_{max_drawdown}_{position_size}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_key_points_analysis(
    symbol: str,
    current_price: float,
    rsi: Optional[float] = None,
    ma_trend: Optional[str] = None,
    max_tokens: int = 250
) -> str:
    """
    生成关键点分析（要点列举）

    Args:
        symbol: 股票代码
        current_price: 当前价格
        rsi: RSI 指标（可选）
        ma_trend: 均线趋势（可选）
        max_tokens: 最大 token 数

    Returns:
        关键点分析（3-5个要点）
    """
    technical_info = f"RSI: {rsi:.1f}" if rsi else ""
    if ma_trend:
        technical_info += f" 趋势: {ma_trend}" if technical_info else f"趋势: {ma_trend}"

    prompt = f"""
    {symbol} 当前价格 {current_price:.2f} 元。
    {technical_info}

    请列出 3-5 个关键分析要点，每点用一句话概括，包括：
    - 价格关键位置（支撑/阻力）
    - 技术面重要信号
    - 短期走势判断
    - 操作建议

    格式要求：每行一个要点，用序号标示。
    不要使用 markdown 格式。
    """

    cache_key = f"keypoints_{symbol}_{current_price}_{rsi}_{ma_trend}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_market_outlook(
    symbol: str,
    sentiment_score: float,
    technical_signal: str,
    market_trend: str,
    max_tokens: int = 180
) -> str:
    """
    生成市场展望

    Args:
        symbol: 股票代码
        sentiment_score: 情绪评分
        technical_signal: 技术信号
        market_trend: 市场趋势
        max_tokens: 最大 token 数

    Returns:
        市场展望分析
    """
    prompt = f"""
    基于 {symbol} 的当前状况：
    市场情绪：{sentiment_score:.1f} 分
    技术信号：{technical_signal}
    整体趋势：{market_trend}

    请分析未来 1-3 个月的走势展望，包括：
    1. 上涨/下跌概率评估
    2. 关键观察点位
    3. 重要时间节点或事件

    控制在150字以内，直接输出分析。
    """

    cache_key = f"outlook_{symbol}_{sentiment_score}_{technical_signal}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def generate_trading_strategy(
    symbol: str,
    current_price: float,
    stop_loss: float,
    take_profit: float,
    risk_tolerance: str = "medium",
    max_tokens: int = 200
) -> str:
    """
    生成交易策略建议

    Args:
        symbol: 股票代码
        current_price: 当前价格
        stop_loss: 止损价
        take_profit: 止盈价
        risk_tolerance: 风险承受能力
        max_tokens: 最大 token 数

    Returns:
        交易策略建议
    """
    risk_map = {
        "low": "保守",
        "medium": "稳健",
        "high": "激进"
    }
    tolerance = risk_map.get(risk_tolerance, "稳健")

    prompt = f"""
    {symbol} 当前价格 {current_price:.2f} 元。
    止损价位：{stop_loss:.2f} 元
    止盈价位：{take_profit:.2f} 元
    风险偏好：{tolerance}

    请提供具体的交易策略，包括：
    1. 建仓方式（一次性/分批）
    2. 加仓/减仓时机
    3. 仓位管理建议
    4. 风险控制要点

    控制在180字以内，直接输出策略内容。
    """

    cache_key = f"strategy_{symbol}_{current_price}_{stop_loss}_{take_profit}_{risk_tolerance}"
    return generate_llm_explanation(prompt, max_tokens, cache_key)


def clear_cache():
    """清空解释缓存"""
    global _EXPLANATION_CACHE
    _EXPLANATION_CACHE.clear()
