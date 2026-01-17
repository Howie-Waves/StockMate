"""
StockMate 核心工具集
提供数据获取、新闻抓取和回测功能
"""

import pandas as pd
import numpy as np
import akshare as ak
import vectorbt as vbt
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# ==================== 工具 1: 市场数据获取 ====================


def get_a_share_data(symbol: str, period: int = 365) -> Dict[str, Any]:
    """
    获取A股历史行情数据

    Args:
        symbol: 股票代码，支持格式: "600000", "000001.SZ", "600000.SH"
        period: 获取数据天数，默认365天

    Returns:
        包含OHLCV数据和统计信息的字典

    Example:
        >>> get_a_share_data("600000")
        {
            "ticker": "600000",
            "data": {...},
            "current_price": 10.75,
            "change_pct": 2.35,
            "statistics": {...}
        }
    """
    try:
        # 标准化股票代码格式
        symbol = _normalize_symbol(symbol)

        # 计算日期范围
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=period)).strftime("%Y%m%d")

        # 调用 AkShare 获取数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",  # 前复权
        )

        if df.empty:
            return {
                "success": False,
                "error": f"未获取到股票 {symbol} 的数据，请检查代码是否正确",
            }

        # === 强制重命名中文列名为英文（兼容 vectorbt）===
        column_mapping = {
            "日期": "date",
            "开盘": "Open",
            "最高": "High",
            "最低": "Low",
            "收盘": "Close",
            "成交量": "Volume",
            "成交额": "Amount",
            "涨跌幅": "ChangePct",
            "涨跌额": "ChangeAmount",
            "换手率": "Turnover",
        }

        df = df.rename(columns=column_mapping)

        # 设置日期索引并排序
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()

        # 确保必需列存在
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {
                "success": False,
                "error": f"数据缺少必需列: {missing_cols}",
            }

        # 计算基本统计
        current_price = float(df["Close"].iloc[-1])
        prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price) * 100

        # 计算波动率（年化）
        returns = df["Close"].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252) * 100)

        # 计算最大回撤
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = ((cumulative - rolling_max) / rolling_max * 100).min()

        statistics = {
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "volatility": round(volatility, 2),
            "max_drawdown": round(drawdown, 2),
            "period_high": round(float(df["High"].max()), 2),
            "period_low": round(float(df["Low"].min()), 2),
            "avg_volume": round(float(df["Volume"].mean()), 0),
        }

        return {
            "success": True,
            "ticker": symbol,
            "data_count": len(df),
            "date_range": f"{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}",
            "current_price": statistics["current_price"],
            "change_pct": statistics["change_pct"],
            "statistics": statistics,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"获取数据时发生错误: {str(e)}",
        }


# ==================== 工具 2: 新闻获取 ====================


def get_latest_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """
    获取个股最新新闻和公告

    Args:
        symbol: 股票代码
        limit: 返回新闻数量，默认10条

    Returns:
        包含新闻列表的字典

    Example:
        >>> get_latest_news("600000")
        {
            "success": True,
            "news_count": 10,
            "news": [...]
        }
    """
    try:
        symbol = _normalize_symbol(symbol)

        # 获取新闻数据
        news_df = ak.stock_news_em(symbol=symbol)

        if news_df.empty:
            return {
                "success": False,
                "error": f"未获取到股票 {symbol} 的新闻数据",
            }

        # 处理新闻数据
        news_list = []
        for idx, row in news_df.head(limit).iterrows():
            news_item = {
                "title": row.get("新闻标题", "未知标题"),
                "content": row.get("新闻内容", "")[:200],  # 截取前200字符
                "publish_time": row.get("发布时间", ""),
                "source": row.get("文章来源", "东方财富网"),
            }
            news_list.append(news_item)

        return {
            "success": True,
            "ticker": symbol,
            "news_count": len(news_list),
            "news": news_list,
        }

    except Exception as e:
        # 如果 ak.stock_news_em 失败，尝试备用接口
        try:
            # 备用: 获取个股新闻的另一个接口
            news_df = ak.stock_news_detail(symbol=symbol)

            if news_df.empty:
                return {
                    "success": False,
                    "error": f"未获取到股票 {symbol} 的新闻数据",
                }

            news_list = []
            for idx, row in news_df.head(limit).iterrows():
                news_item = {
                    "title": row.get("title", "未知标题"),
                    "content": row.get("content", "")[:200],
                    "publish_time": row.get("time", ""),
                    "source": "财经新闻",
                }
                news_list.append(news_item)

            return {
                "success": True,
                "ticker": symbol,
                "news_count": len(news_list),
                "news": news_list,
            }

        except Exception as e2:
            return {
                "success": False,
                "error": f"获取新闻失败: {str(e2)}",
            }


# ==================== 工具 3: 回测引擎 ====================


def run_backtest(
    symbol: str,
    strategy_type: str = "RSI",
    period: int = 365,
    initial_cash: float = 100000,
) -> Dict[str, Any]:
    """
    使用 vectorbt 运行回测

    Args:
        symbol: 股票代码
        strategy_type: 策略类型 ("RSI", "MA", "Bollinger")
        period: 回测周期（天）
        initial_cash: 初始资金

    Returns:
        回测结果字典

    Example:
        >>> run_backtest("600000", "RSI")
        {
            "success": True,
            "strategy": "RSI",
            "win_rate": 68.5,
            "total_return": 24.3,
            ...
        }
    """
    try:
        symbol = _normalize_symbol(symbol)

        # 获取历史数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=period)).strftime("%Y%m%d")

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )

        if df.empty or len(df) < 50:
            return {
                "success": False,
                "error": "数据不足，无法进行回测（至少需要50天数据）",
            }

        # 重命名列
        column_mapping = {
            "日期": "date",
            "开盘": "Open",
            "最高": "High",
            "最低": "Low",
            "收盘": "Close",
            "成交量": "Volume",
        }
        df = df.rename(columns=column_mapping)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()

        # 根据策略类型生成信号
        if strategy_type == "RSI":
            entries, exits = _generate_rsi_signals(df)
        elif strategy_type == "MA":
            entries, exits = _generate_ma_signals(df)
        elif strategy_type == "Bollinger":
            entries, exits = _generate_bollinger_signals(df)
        else:
            return {
                "success": False,
                "error": f"不支持的策略类型: {strategy_type}",
            }

        # 运行回测
        pf = vbt.Portfolio.from_signals(
            df["Close"],
            entries,
            exits,
            init_cash=initial_cash,
            fees=0.001,  # 手续费 0.1%
            slippage=0.001,  # 滑点 0.1%
        )

        # 计算回测指标
        total_return = float(pf.total_return() * 100)
        sharpe_ratio = float(pf.sharpe_ratio())
        max_drawdown = float(pf.max_drawdown() * 100)
        total_trades = int(pf.trades.count())

        # 计算胜率
        trades = pf.trades.records_readable
        if len(trades) > 0:
            winning_trades = len(trades[trades["Return"] > 0])
            win_rate = (winning_trades / len(trades)) * 100
        else:
            win_rate = 0

        return {
            "success": True,
            "strategy": strategy_type,
            "ticker": symbol,
            "backtest_period": f"{period} 天",
            "win_rate": round(win_rate, 2),
            "total_return": round(total_return, 2),
            "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio == sharpe_ratio else 0,
            "max_drawdown": round(max_drawdown, 2),
            "total_trades": total_trades,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"回测执行失败: {str(e)}",
        }


# ==================== 辅助函数 ====================


def _normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码格式

    处理各种输入格式:
    - "600000" -> "600000" (上海保持纯数字)
    - "000001" -> "000001" (深圳保持纯数字)
    - "600000.SH" -> "600000"
    - "000001.SZ" -> "000001"
    """
    # 移除后缀
    if "." in symbol:
        symbol = symbol.split(".")[0]

    # 确保是6位数字
    symbol = symbol.strip().zfill(6)

    return symbol


def _generate_rsi_signals(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70):
    """生成 RSI 策略信号"""
    # 计算 RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # 生成信号: RSI < 30 买入，RSI > 70 卖出
    entries = rsi < oversold
    exits = rsi > overbought

    return entries, exits


def _generate_ma_signals(df: pd.DataFrame, fast: int = 5, slow: int = 20):
    """生成均线交叉策略信号"""
    # 计算均线
    ma_fast = df["Close"].rolling(window=fast).mean()
    ma_slow = df["Close"].rolling(window=slow).mean()

    # 生成信号: 快线上穿慢线买入，快线下穿慢线卖出
    entries = ma_fast > ma_slow
    exits = ma_fast < ma_slow

    # 过滤连续信号
    entries = entries & (~entries.shift(1).fillna(False))
    exits = exits & (~exits.shift(1).fillna(False))

    return entries, exits


def _generate_bollinger_signals(
    df: pd.DataFrame, period: int = 20, std_dev: int = 2
):
    """生成布林带策略信号"""
    # 计算布林带
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)

    # 生成信号: 价格触及下轨买入，触及上轨卖出
    entries = df["Close"] <= lower_band
    exits = df["Close"] >= upper_band

    return entries, exits


# ==================== 工具导出 ====================

# 导出给 smolagents 使用的工具函数
def get_stock_info(symbol: str) -> str:
    """获取股票基本信息（供 Agent 调用）"""
    result = get_a_share_data(symbol)
    if result["success"]:
        return f"""
股票 {result['ticker']} 基本信息:
- 当前价格: {result['current_price']} 元
- 涨跌幅: {result['change_pct']}%
- 波动率: {result['statistics']['volatility']}%
- 最大回撤: {result['statistics']['max_drawdown']}%
- 期间最高: {result['statistics']['period_high']} 元
- 期间最低: {result['statistics']['period_low']} 元
- 数据日期: {result['date_range']}
"""
    return f"获取股票信息失败: {result['error']}"


def get_stock_news(symbol: str) -> str:
    """获取股票新闻（供 Agent 调用）"""
    result = get_latest_news(symbol)
    if result["success"]:
        news_summary = f"股票 {result['ticker']} 最新 {result['news_count']} 条新闻:\n\n"
        for i, news in enumerate(result["news"], 1):
            news_summary += f"{i}. {news['title']}\n   发布时间: {news['publish_time']}\n   摘要: {news['content']}\n\n"
        return news_summary
    return f"获取新闻失败: {result['error']}"


def backtest_strategy(symbol: str, strategy: str = "RSI") -> str:
    """执行回测（供 Agent 调用）"""
    result = run_backtest(symbol, strategy)
    if result["success"]:
        return f"""
股票 {result['ticker']} {result['strategy']} 策略回测结果:
- 回测周期: {result['backtest_period']}
- 胜率: {result['win_rate']}%
- 总收益率: {result['total_return']}%
- 夏普比率: {result['sharpe_ratio']}
- 最大回撤: {result['max_drawdown']}%
- 总交易次数: {result['total_trades']}
"""
    return f"回测失败: {result['error']}"


if __name__ == "__main__":
    # 测试工具
    print("=== 测试 get_a_share_data ===")
    print(get_a_share_data("600000"))

    print("\n=== 测试 get_latest_news ===")
    print(get_latest_news("600000"))

    print("\n=== 测试 run_backtest ===")
    print(run_backtest("600000", "RSI"))
