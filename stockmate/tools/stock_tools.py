"""
StockMate 核心工具集
提供数据获取、新闻抓取和回测功能
"""

import pandas as pd
import numpy as np
import akshare as ak
import vectorbt as vbt
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# ==================== Stock Name Mapping Cache ====================
_STOCK_NAME_CACHE: Dict[str, str] = {}


# 全局变量缓存所有A股数据（避免重复获取大量数据）
_SPOT_DF_CACHE = None


def preload_stock_cache():
    """
    预加载股票名称缓存（后台运行）

    这个函数可以在应用启动时调用，在后台预加载股票数据，
    避免第一次分析时的延迟。
    """
    global _SPOT_DF_CACHE

    def _load_cache():
        try:
            if _SPOT_DF_CACHE is None:
                import threading
                def load_in_background():
                    try:
                        _SPOT_DF_CACHE = ak.stock_zh_a_spot_em()
                    except:
                        pass

                # 在后台线程中加载
                thread = threading.Thread(target=load_in_background, daemon=True)
                thread.start()
        except:
            pass

    return _load_cache()


def get_stock_name(symbol: str) -> str:
    """
    获取股票名称

    Args:
        symbol: 股票代码 (6位数字)

    Returns:
        股票名称，如果获取失败则返回股票代码
    """
    global _STOCK_NAME_CACHE, _SPOT_DF_CACHE

    try:
        symbol = _normalize_symbol(symbol)

        # 检查缓存
        if symbol in _STOCK_NAME_CACHE:
            return _STOCK_NAME_CACHE[symbol]

        # 方法1: 使用 stock_individual_info_em（最快，针对单个股票）
        try:
            # 判断市场（上海/深圳）
            if symbol.startswith('6'):
                market = 'sh'
            else:
                market = 'sz'

            stock_info = ak.stock_individual_info_em(symbol=f"{symbol}{market}")

            if not stock_info.empty:
                # 遍历所有行查找股票名称
                for idx in range(min(10, len(stock_info))):  # 只检查前10行
                    try:
                        field = str(stock_info.iloc[idx, 0])
                        value = str(stock_info.iloc[idx, 1])

                        # 匹配包含"简称"、"名称"等关键词的字段
                        if any(keyword in field for keyword in ['简称', '名称', '股票名称']):
                            name = value.replace('　', '').strip()
                            # 移除可能的 .SH / .SZ 后缀
                            name = name.replace('.SH', '').replace('.SZ', '').replace('.sh', '').replace('.sz', '')
                            if name and name != 'nan' and len(name) >= 2:
                                _STOCK_NAME_CACHE[symbol] = name
                                return name
                    except:
                        continue
        except:
            pass

        # 方法2: 尝试使用 stock_info_a_code_name API（快速）
        try:
            name_df = ak.stock_info_a_code_name(symbol=symbol)
            if not name_df.empty and 'name' in name_df.columns:
                name = str(name_df.iloc[0]['name'])
                name = name.replace('　', '').strip()
                if name and name != 'nan' and len(name) >= 2:
                    _STOCK_NAME_CACHE[symbol] = name
                    return name
        except:
            pass

        # 方法3: 最后才使用 stock_zh_a_spot_em（最慢，作为备用）
        try:
            # 使用全局缓存避免重复获取全部A股数据
            if _SPOT_DF_CACHE is None:
                _SPOT_DF_CACHE = ak.stock_zh_a_spot_em()

            if not _SPOT_DF_CACHE.empty:
                # 查找匹配的股票代码
                match = _SPOT_DF_CACHE[_SPOT_DF_CACHE['代码'] == symbol]
                if not match.empty:
                    name = str(match.iloc[0]['名称'])
                    name = name.replace('　', '').strip()
                    if name and name != 'nan' and len(name) >= 2:
                        _STOCK_NAME_CACHE[symbol] = name
                        return name
        except:
            pass

        return symbol
    except Exception:
        return symbol


def get_stock_name_with_code(symbol: str) -> str:
    """
    获取带股票代码的股票名称

    Args:
        symbol: 股票代码

    Returns:
        格式化的股票名称，如 "平安银行 (000001)"
    """
    symbol = _normalize_symbol(symbol)
    name = get_stock_name(symbol)

    if name == symbol:
        return f"股票 ({symbol})"
    return f"{name} ({symbol})"

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

        # 获取股票名称
        stock_name = get_stock_name(symbol)

        return {
            "success": True,
            "ticker": symbol,
            "name": stock_name,
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
        包含新闻列表的字典，包含可点击的URL链接

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
            # 构建新闻URL（东方财富网的新闻通常可以通过新闻标题搜索）
            # 或者直接从数据中提取链接（如果有的话）
            news_url = row.get("新闻链接", "")
            if not news_url or pd.isna(news_url):
                # 如果没有直接链接，构建搜索URL
                import urllib.parse
                title = row.get("新闻标题", "")
                encoded_title = urllib.parse.quote(title)
                news_url = f"http://so.eastmoney.com/news/s?keyword={encoded_title}"

            news_item = {
                "title": row.get("新闻标题", "未知标题"),
                "content": row.get("新闻内容", "")[:200],  # 截取前200字符
                "publish_time": row.get("发布时间", ""),
                "source": row.get("文章来源", "东方财富网"),
                "url": news_url,
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
                    "url": "",  # 备用接口可能没有URL
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
    fast_mode: bool = True,
    df: pd.DataFrame = None,
) -> Dict[str, Any]:
    """
    使用 vectorbt 运行回测

    Args:
        symbol: 股票代码
        strategy_type: 策略类型 ("RSI", "MA", "Bollinger")
        period: 回测周期（天）
        initial_cash: 初始资金
        fast_mode: 快速模式（使用较少数据，默认 True）
        df: 可选的已有数据框（避免重复获取数据）

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

        # 快速模式：只使用最近 90 天数据
        actual_period = 90 if fast_mode else period

        # 如果没有提供数据框，则获取数据
        if df is None:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=actual_period)).strftime("%Y%m%d")

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

        # 确保 DataFrame 是正确的格式（避免未来数据泄露）
        df = df.sort_index()

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
        # 将价格数据转换为 Pandas Series 并确保是正确的格式
        close_series = df["Close"].astype(float)

        pf = vbt.Portfolio.from_signals(
            close_series,
            entries,
            exits,
            init_cash=initial_cash,
            fees=0.001,  # 手续费 0.1%
            slippage=0.001,  # 滑点 0.1%
            freq='d'  # 明确指定频率为日频（'d' 代表 daily）
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

        # 计算收益曲线数据
        # 获取投资组合的价值
        portfolio_value = pf.value()
        # 转换为累计收益率（相对于初始资金）
        equity_curve = ((portfolio_value - initial_cash) / initial_cash * 100).tolist()

        # 获取日期索引
        dates = portfolio_value.index.strftime("%Y-%m-%d").tolist()

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
            "equity_curve": equity_curve,  # 新增：收益曲线数据
            "dates": dates,  # 新增：日期数据
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
    # 改进：使用连续触发，而不是边缘触发，以增加交易机会
    # 入场：RSI 从高位跌破 40（弱势区域）
    # 出场：RSI 突破 60（强势区域）

    # 计算信号变化
    rsi_prev = rsi.shift(1)

    # 入场信号：RSI 从上方跌破 40
    entries = (rsi < 40) & (rsi_prev >= 40)

    # 出场信号：RSI 从下方突破 60
    exits = (rsi > 60) & (rsi_prev <= 60)

    # 或者是超卖超买信号
    entries_oversold = (rsi < oversold) & (rsi_prev >= oversold)
    exits_overbought = (rsi > overbought) & (rsi_prev <= overbought)

    # 合并信号
    entries = entries | entries_oversold
    exits = exits | exits_overbought

    return entries, exits


def _generate_ma_signals(df: pd.DataFrame, fast: int = 5, slow: int = 20):
    """生成均线交叉策略信号"""
    # 计算均线
    ma_fast = df["Close"].rolling(window=fast).mean()
    ma_slow = df["Close"].rolling(window=slow).mean()

    # 生成信号: 快线上穿慢线买入，快线下穿慢线卖出
    # 改进：使用金叉死叉的确认
    ma_fast_prev = ma_fast.shift(1)
    ma_slow_prev = ma_slow.shift(1)

    # 金叉：快线从下方穿越慢线
    entries = (ma_fast > ma_slow) & (ma_fast_prev <= ma_slow_prev)

    # 死叉：快线从上方穿越慢线
    exits = (ma_fast < ma_slow) & (ma_fast_prev >= ma_slow_prev)

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

    # 前一天的价格
    close_prev = df["Close"].shift(1)
    upper_prev = upper_band.shift(1)
    lower_prev = lower_band.shift(1)

    # 生成信号: 价格触及下轨买入，触及上轨卖出
    # 改进：价格从轨道外部回到内部时触发

    # 入场：价格从下轨下方回到下轨上方
    entries_from_below = (df["Close"] > lower_band) & (close_prev <= lower_prev)

    # 出场：价格从上轨上方回到上轨下方
    exits_from_above = (df["Close"] < upper_band) & (close_prev >= upper_prev)

    # 也可以是直接触达轨道
    entries_touch = (df["Close"] <= lower_band) & (close_prev > lower_prev)
    exits_touch = (df["Close"] >= upper_band) & (close_prev < upper_prev)

    # 合并信号
    entries = entries_from_below | entries_touch
    exits = exits_from_above | exits_touch

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


def calculate_kelly_position(
    win_probability: float,
    planned_capital: float,
    stop_loss_pct: float = 5.0,
    take_profit_pct: float = 15.0,
    win_loss_ratio: float = None,
) -> str:
    """
    计算凯利公式仓位（供 Agent 调用）

    Args:
        win_probability: 获胜概率 (%)
        planned_capital: 计划投入资金（元）
        stop_loss_pct: 止损比例 (%)
        take_profit_pct: 止盈比例 (%)
        win_loss_ratio: 盈亏比（可选，如果不提供则根据止盈止损计算）

    Returns:
        格式化的凯利公式建议文本
    """
    from stockmate.tools.kelly_criterion import KellyCalculator

    if win_loss_ratio is None:
        win_loss_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 2.0

    result = KellyCalculator.calculate(
        win_probability=win_probability,
        win_loss_ratio=win_loss_ratio,
        planned_capital=planned_capital,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
    )

    return f"""
🎯 凯利公式仓位建议：

📊 输入参数：
  - 获胜概率: {win_probability}%
  - 盈亏比（赔率）: {win_loss_ratio:.2f}
  - 计划投入: {planned_capital:,.2f} 元
  - 止损比例: {stop_loss_pct}%
  - 止盈比例: {take_profit_pct}%

💰 计算结果：
  - 凯利公式建议仓位: {result['kelly_fraction']:.2%}
  - 建议投入金额: {result['recommended_amount']:,.2f} 元
  - 半凯利（保守）: {result['half_kelly_amount']:,.2f} 元
  - 期望值: {result['expected_value']:.4f}
  - 正期望值: {'是 ✅' if result['is_positive_ev'] else '否 ❌'}

⚠️ 风险提示:
  {result['risk_warning']}

💡 专业提示：
  {'建议使用半凯利公式以降低回撤风险，提高资金曲线的平滑度。' if result['kelly_fraction'] > 0.1 else '当前建议仓位较为保守，可以考虑适当增加仓位。'}
"""


# ==================== 工具 4: NLG 回测洞察分析 ====================


def generate_backtest_insights(backtest_result: Dict[str, Any], use_llm: bool = True) -> Dict[str, str]:
    """
    为回测结果生成自然语言洞察分析

    Args:
        backtest_result: 回测结果字典
        use_llm: 是否使用 LLM 生成智能解释（默认 True）

    Returns:
        包含各项指标分析的字典，包括：
        - overall_summary: 整体评价
        - return_analysis: 收益分析
        - risk_analysis: 风险分析
        - sharpe_analysis: 夏普比率分析
        - win_rate_analysis: 胜率分析
        - color_codes: 颜色编码建议
    """
    if not backtest_result.get("success"):
        return {
            "overall_summary": "回测执行失败，无法生成分析",
            "return_analysis": "",
            "risk_analysis": "",
            "sharpe_analysis": "",
            "winrate_analysis": "",
            "color_codes": {},
        }

    win_rate = backtest_result.get("win_rate", 0)
    total_return = backtest_result.get("total_return", 0)
    sharpe_ratio = backtest_result.get("sharpe_ratio", 0)
    max_drawdown = backtest_result.get("max_drawdown", 0)
    total_trades = backtest_result.get("total_trades", 0)
    strategy = backtest_result.get("strategy", "未知")

    # 颜色编码
    color_codes = {
        "return": "#4CAF50" if total_return > 0 else "#F44336",
        "sharpe": "#4CAF50" if sharpe_ratio > 1 else "#FF9800" if sharpe_ratio > 0 else "#F44336",
        "drawdown": "#4CAF50" if max_drawdown < 10 else "#FF9800" if max_drawdown < 20 else "#F44336",
        "winrate": "#4CAF50" if win_rate > 55 else "#FF9800" if win_rate > 45 else "#F44336",
    }

    # 尝试使用 LLM 生成整体总结
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_backtest_summary
            llm_summary = generate_backtest_summary(
                win_rate, total_return, sharpe_ratio,
                max_drawdown, total_trades, strategy
            )
            if llm_summary and "暂无智能分析" not in llm_summary and "分析生成失败" not in llm_summary:
                overall_summary = f"综合评级：{llm_summary}"
            else:
                overall_summary = _generate_overall_rating(total_return, sharpe_ratio, max_drawdown, win_rate, strategy)
        except Exception:
            overall_summary = _generate_overall_rating(total_return, sharpe_ratio, max_drawdown, win_rate, strategy)
    else:
        overall_summary = _generate_overall_rating(total_return, sharpe_ratio, max_drawdown, win_rate, strategy)

    # 收益分析 - 移除 Markdown 语法
    if total_return > 20:
        return_analysis = f"表现优秀 ：该策略在回测期间实现了 {total_return:.1f}% 的总收益，表现显著优于市场平均水平。"
    elif total_return > 10:
        return_analysis = f"表现良好 ：该策略在回测期间实现了 {total_return:.1f}% 的总收益，收益可观。"
    elif total_return > 0:
        return_analysis = f"小幅盈利 ：该策略在回测期间实现了 {total_return:.1f}% 的总收益，收益较为温和。"
    elif total_return > -10:
        return_analysis = f"小幅亏损 ：该策略在回测期间出现了 {total_return:.1f}% 的亏损，建议谨慎使用。"
    else:
        return_analysis = f"表现不佳 ：该策略在回测期间出现了 {total_return:.1f}% 的较大亏损，不建议使用。"

    # 风险分析（最大回撤）- 移除 Markdown 语法
    if max_drawdown < 10:
        risk_analysis = f"风险控制优秀 ：最大回撤仅为 {max_drawdown:.1f}%，说明该策略在风险控制方面表现优异，资金曲线平滑。"
    elif max_drawdown < 20:
        risk_analysis = f"风险适中 ：最大回撤为 {max_drawdown:.1f}%，属于可接受范围，但建议关注市场波动风险。"
    elif max_drawdown < 35:
        risk_analysis = f"风险较高 ：最大回撤达到 {max_drawdown:.1f}%，说明该策略历史上出现过较大的亏损，请确保您能承受这样的波动。"
    else:
        risk_analysis = f"风险极高 ：最大回撤达到 {max_drawdown:.1f}%！这意味着该策略历史上曾出现过非常严重的亏损，强烈不建议普通投资者使用。"

    # 夏普比率分析 - 移除 Markdown 语法
    if sharpe_ratio > 2:
        sharpe_analysis = f"风险调整后收益极佳 ：夏普比率为 {sharpe_ratio:.2f}，远超市场基准，说明每承担一单位风险都能获得优秀的回报。"
    elif sharpe_ratio > 1:
        sharpe_analysis = f"风险调整后收益良好 ：夏普比率为 {sharpe_ratio:.2f}，高于市场基准，说明该策略的风险回报比较合理。"
    elif sharpe_ratio > 0:
        sharpe_analysis = f"风险调整后收益一般 ：夏普比率为 {sharpe_ratio:.2f}，低于理想水平，建议结合其他指标综合评估。"
    else:
        sharpe_analysis = f"风险调整后收益不佳 ：夏普比率为 {sharpe_ratio:.2f}，说明承担的风险未能得到相应回报，不建议使用。"

    # 胜率分析 - 移除 Markdown 语法
    if win_rate > 60:
        winrate_analysis = f"胜率极高 ：{win_rate:.1f}% 的胜率说明该策略在大多数交易中都能盈利，是一个非常积极的信号。"
    elif win_rate > 50:
        winrate_analysis = f"胜率良好 ：{win_rate:.1f}% 的胜率说明该策略有超过半数的交易是盈利的，表现尚可。"
    elif win_rate > 40:
        winrate_analysis = f"胜率一般 ：{win_rate:.1f}% 的胜率意味着该策略的盈利交易不到一半，需要依靠单笔盈利来弥补亏损。"
    else:
        winrate_analysis = f"胜率较低 ：{win_rate:.1f}% 的胜率说明大多数交易都是亏损的，除非盈亏比很高，否则不建议使用。"

    return {
        "overall_summary": overall_summary,
        "return_analysis": return_analysis,
        "risk_analysis": risk_analysis,
        "sharpe_analysis": sharpe_analysis,
        "winrate_analysis": winrate_analysis,
        "color_codes": color_codes,
    }


def _generate_overall_rating(total_return: float, sharpe_ratio: float, max_drawdown: float, win_rate: float, strategy: str) -> str:
    """生成本地逻辑的整体评级（降级方案）"""
    score = 0
    if total_return > 0: score += 1
    if sharpe_ratio > 1: score += 1
    if max_drawdown < 20: score += 1
    if win_rate > 50: score += 1

    if score == 4:
        return f"综合评级：优秀 。该 {strategy} 策略在回测期间表现全面出色，各项指标均达到理想水平，可以考虑实盘使用。"
    elif score >= 3:
        return f"综合评级：良好 。该 {strategy} 策略整体表现良好，大部分指标达到预期，可以谨慎使用。"
    elif score >= 2:
        return f"综合评级：一般 。该 {strategy} 策略表现平平，建议仅作为参考，不建议大资金使用。"
    else:
        return f"综合评级：不佳 。该 {strategy} 策略多项指标不达标，不建议使用。"


# ==================== 工具 5: 技术术语通俗化翻译 ====================


PLAIN_LANGUAGE_GLOSSARY = {
    "RSI": {
        "term": "RSI指标",
        "explanation": "衡量股票涨跌动能的指标，0-100之间。低于30表示可能超卖（价格跌太多），高于70表示可能超买（涨太多）。",
        "plain_text": "市场情绪温度计"
    },
    "MACD": {
        "term": "MACD指标",
        "explanation": "判断股价趋势变化的指标，金叉（线上穿）可能上涨，死叉（线下穿）可能下跌。",
        "plain_text": "趋势转向信号"
    },
    "MA": {
        "term": "移动平均线",
        "explanation": "一段时间内股价的平均值线，帮助平滑价格波动，判断趋势方向。",
        "plain_text": "平均成本线"
    },
    "Bollinger": {
        "term": "布林带",
        "explanation": "由三条线组成，中间是平均线，上下两条线形成价格通道。价格触及下轨可能超卖，触及上轨可能超买。",
        "plain_text": "价格波动通道"
    },
    "Sharpe Ratio": {
        "term": "夏普比率",
        "explanation": "衡量每承担一单位风险能获得多少回报。数值越高越好，大于1表示风险调整后收益良好。",
        "plain_text": "性价比评分"
    },
    "Max Drawdown": {
        "term": "最大回撤",
        "explanation": "从历史最高点到最低点的最大跌幅，用来评估最坏情况下会亏损多少。",
        "plain_text": "史上最大亏损"
    },
    "Win Rate": {
        "term": "胜率",
        "explanation": "盈利交易次数占总交易次数的百分比，反映策略赚钱的成功概率。",
        "plain_text": "赚钱概率"
    },
    "Volatility": {
        "term": "波动率",
        "explanation": "衡量价格变动剧烈程度的指标，波动率越高表示价格起伏越大，风险越高。",
        "plain_text": "价格起伏程度"
    },
    "Kelly Criterion": {
        "term": "凯利公式",
        "explanation": "根据胜率和盈亏比计算最优投资比例的数学公式，帮助确定每次交易应该投入多少资金最合理。",
        "plain_text": "最优仓位计算器"
    },
    "Expected Value": {
        "term": "期望值",
        "explanation": "长期来看，每笔交易平均能赚或赔多少，正值表示长期盈利，负值表示长期亏损。",
        "plain_text": "长期平均盈亏"
    },
    "Win/Loss Ratio": {
        "term": "盈亏比",
        "explanation": "平均盈利金额与平均亏损金额的比值，比如盈亏比2:1表示赚一次的钱可以抵消赔两次。",
        "plain_text": "赚赔比例"
    },
}


def explain_term(term: str, use_plain_language: bool = True) -> str:
    """
    将技术术语翻译为通俗语言

    Args:
        term: 技术术语
        use_plain_language: 是否使用超简化语言

    Returns:
        通俗化解释
    """
    # 标准化输入
    term_key = term.upper().replace(" ", "")

    # 查找术语
    for key, value in PLAIN_LANGUAGE_GLOSSARY.items():
        if term_key in key.upper() or key.upper() in term_key:
            if use_plain_language:
                return f"{value['plain_text']}：{value['explanation']}"
            return f"{value['term']}：{value['explanation']}"

    # 如果找不到，返回原术语
    return term


def get_term_tooltip(term: str) -> str:
    """
    获取技术术语的工具提示文本
    """
    return explain_term(term, use_plain_language=False)


# ==================== 工具 6: Human Insight Engine ====================


def calculate_technical_indicators(
    df: Optional[pd.DataFrame],
    current_price: float
) -> Dict[str, Any]:
    """
    计算技术指标供 Verdict 生成使用

    Args:
        df: 包含 OHLC 数据的 DataFrame
        current_price: 当前价格

    Returns:
        包含技术指标的字典:
        - rsi: RSI 值
        - ma20: 20日均线值
        - price_vs_ma20: 价格与 MA20 的百分比差
        - current_price: 当前价格
    """
    indicators = {
        "rsi": 50,  # 默认中性
        "ma20": 0,
        "price_vs_ma20": 0,
        "current_price": current_price
    }

    if df is None or len(df) < 20:
        return indicators

    try:
        # 计算 MA20
        ma20 = df["Close"].rolling(window=20).mean().iloc[-1]
        indicators["ma20"] = float(ma20)

        # 计算价格与 MA20 的百分比差
        if ma20 > 0:
            price_vs_ma20 = ((current_price - ma20) / ma20) * 100
            indicators["price_vs_ma20"] = float(price_vs_ma20)

        # 计算 RSI
        if len(df) >= 14:
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]
            if not pd.isna(rsi_value):
                indicators["rsi"] = float(rsi_value)

    except Exception as e:
        logger.warning(f"计算技术指标时出错: {e}")

    return indicators


def generate_human_insight(
    stock_data: Dict[str, Any],
    sentiment_score: float,
    technical_signal: str,
    var_value: float,
    risk_assessment: str,
    indicators: Optional[Dict[str, Any]] = None,
    use_llm: bool = True
) -> Dict[str, str]:
    """
    人类洞察引擎 - 将技术数据转换为人类可读的投资建议

    采用 Observation -> Interpretation -> Verdict 框架：
    1. OBSERVATION (观察): 描述当前市场状态和数据事实
    2. INTERPRETATION (解读): 解释这些数据对投资者的意义
    3. VERDICT (结论): 给出清晰的操作建议

    Args:
        stock_data: 股票数据字典
        sentiment_score: 情绪评分 (0-100)
        technical_signal: 技术信号
        var_value: 波动率
        risk_assessment: 风险评估
        indicators: 技术指标字典 (可选), 包含 RSI, MA20, price_vs_ma20, kelly_fraction 等
        use_llm: 是否使用 LLM 生成智能解释（默认 True）

    Returns:
        包含三个层级洞察的字典
    """
    # ==================== OBSERVATION 层级：市场现状描述 ====================

    current_price = stock_data.get("current_price", 0)
    change_pct = stock_data.get("change_pct", 0)
    symbol = stock_data.get("ticker", "")
    volatility_level = "低" if var_value < 2 else "中等" if var_value < 4 else "高"
    sentiment_level = "看涨" if sentiment_score > 60 else "看跌" if sentiment_score < 40 else "中性"

    observation_trend = _describe_trend(change_pct, current_price, symbol, use_llm)
    observation_volatility = _describe_volatility(volatility_level, var_value, use_llm)
    observation_sentiment = _describe_sentiment(sentiment_level, sentiment_score, use_llm)

    # ==================== INTERPRETATION 层级：投资机会与风险 ====================

    interpretation_opportunity = _interpret_opportunity(
        sentiment_score, technical_signal, change_pct, use_llm
    )
    interpretation_risk = _interpret_risk(
        var_value, risk_assessment, volatility_level, use_llm
    )
    interpretation_technical = _interpret_technical_signal(technical_signal, use_llm)

    # ==================== VERDICT 层级：最终建议 ====================

    verdict_summary = _generate_verdict(
        sentiment_score,
        technical_signal,
        risk_assessment,
        var_value,
        indicators
    )
    verdict_actionable = _generate_actionable_steps(
        sentiment_score,
        technical_signal,
        risk_assessment
    )

    return {
        "observation_trend": observation_trend,
        "observation_volatility": observation_volatility,
        "observation_sentiment": observation_sentiment,
        "interpretation_opportunity": interpretation_opportunity,
        "interpretation_risk": interpretation_risk,
        "interpretation_technical": interpretation_technical,
        "verdict_summary": verdict_summary,
        "verdict_actionable": verdict_actionable,
    }


def _describe_trend(change_pct: float, current_price: float, symbol: str = "", use_llm: bool = True) -> str:
    """描述价格趋势 - Observation 层级"""
    if use_llm and symbol:
        try:
            from stockmate.tools.llm_service import generate_market_trend_description
            llm_result = generate_market_trend_description(symbol, current_price, change_pct)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 价格走势观察 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    if change_pct > 2:
        return f"[ 价格走势观察 ] 当前股价为 {current_price:.2f} 元，今日上涨 {change_pct:.2f}%，呈现明显的上升趋势。"
    elif change_pct > 0:
        return f"[ 价格走势观察 ] 当前股价为 {current_price:.2f} 元，今日小幅上涨 {change_pct:.2f}%，走势平稳偏强。"
    elif change_pct > -2:
        return f"[ 价格走势观察 ] 当前股价为 {current_price:.2f} 元，今日小幅下跌 {change_pct:.2f}%，走势疲软。"
    else:
        return f"[ 价格走势观察 ] 当前股价为 {current_price:.2f} 元，今日大幅下跌 {change_pct:.2f}%，呈现明显的下跌趋势。"


def _describe_volatility(volatility_level: str, var_value: float, use_llm: bool = True) -> str:
    """描述波动率 - Observation 层级"""
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_volatility_interpretation
            llm_result = generate_volatility_interpretation(var_value, volatility_level)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 波动性观察 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    if volatility_level == "低":
        return f"[ 波动性观察 ] 当前市场波动率为 {var_value:.2f}%，属于低波动环境，价格相对稳定。"
    elif volatility_level == "中等":
        return f"[ 波动性观察 ] 当前市场波动率为 {var_value:.2f}%，属于中等波动，价格有一定起伏。"
    else:
        return f"[ 波动性观察 ] 当前市场波动率为 {var_value:.2f}%，属于高波动环境，价格波动剧烈，风险较高。"


def _describe_sentiment(sentiment_level: str, score: float, use_llm: bool = True) -> str:
    """描述市场情绪 - Observation 层级"""
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_sentiment_interpretation
            llm_result = generate_sentiment_interpretation(score, sentiment_level)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 市场情绪观察 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    if sentiment_level == "看涨":
        return f"[ 市场情绪观察 ] 市场情绪得分为 {score:.1f} 分，整体情绪偏向乐观，投资者信心较强。"
    elif sentiment_level == "看跌":
        return f"[ 市场情绪观察 ] 市场情绪得分为 {score:.1f} 分，整体情绪偏向悲观，投资者较为谨慎。"
    else:
        return f"[ 市场情绪观察 ] 市场情绪得分为 {score:.1f} 分，市场情绪中性，多空双方力量相对平衡。"


def _interpret_opportunity(
    sentiment_score: float,
    technical_signal: str,
    change_pct: float,
    use_llm: bool = True
) -> str:
    """解读投资机会 - Interpretation 层级"""
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_opportunity_assessment
            llm_result = generate_opportunity_assessment(sentiment_score, technical_signal, change_pct)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 机会解读 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    if sentiment_score > 60 and change_pct > 0:
        return "[ 机会解读 ] 市场情绪乐观且价格呈上涨趋势，这可能是一个较好的入场时机。积极的市场情绪往往推动价格继续上行。"
    elif sentiment_score > 60 and change_pct <= 0:
        return "[ 机会解读 ] 虽然当前价格下跌，但市场情绪依然乐观，这可能是暂时的回调，存在反弹机会。建议密切关注价格企稳信号。"
    elif sentiment_score < 40 and change_pct < 0:
        return "[ 机会解读 ] 市场情绪悲观且价格下跌，当前不是良好的入场时机。建议等待市场情绪改善或出现明确的反转信号。"
    else:
        return "[ 机会解读 ] 当前市场信号混合，投资机会不够明确。建议采取观望策略，等待更清晰的信号出现。"


def _interpret_risk(
    var_value: float,
    risk_assessment: str,
    volatility_level: str,
    use_llm: bool = True
) -> str:
    """解读风险 - Interpretation 层级"""
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_risk_assessment
            llm_result = generate_risk_assessment(var_value, risk_assessment, volatility_level)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 风险解读 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    if risk_assessment == "Approved":
        if volatility_level == "低":
            return "[ 风险解读 ] 当前风险水平可控，波动率较低，适合稳健型投资者参与。"
        else:
            return "[ 风险解读 ] 风控评估通过，但需要注意市场波动。建议控制仓位，做好止损准备。"
    else:
        if volatility_level == "高":
            return "[ 风险解读 ] 风控系统强烈警告！当前市场波动过高，存在较大亏损风险。不建议普通投资者参与。"
        else:
            return "[ 风险解读 ] 风控系统未通过评估，表明当前交易存在潜在风险。建议重新评估或放弃交易。"


def _interpret_technical_signal(technical_signal: str, use_llm: bool = True) -> str:
    """解读技术信号 - Interpretation 层级（去除技术术语）"""
    if use_llm:
        try:
            from stockmate.tools.llm_service import generate_technical_signal_interpretation
            llm_result = generate_technical_signal_interpretation(technical_signal)
            if llm_result and "暂无智能分析" not in llm_result and "分析生成失败" not in llm_result:
                return f"[ 技术信号解读 ] {llm_result}"
        except Exception:
            pass  # 降级到本地逻辑

    # 本地逻辑降级
    signal_interpretations = {
        "黄金交叉": "[ 技术信号解读 ] 短期平均价格线已经上穿长期平均价格线，这是一个经典的上涨信号，表明买入力量正在增强。",
        "死亡交叉": "[ 技术信号解读 ] 短期平均价格线已经下穿长期平均价格线，这是一个下跌信号，表明卖出压力较大，建议谨慎。",
        "超卖": "[ 技术信号解读 ] 当前价格可能跌得过快过深，存在反弹的可能。这通常被视为潜在的买入机会区域。",
        "超买": "[ 技术信号解读 ] 当前价格可能涨得过快过高，存在回调的风险。这通常被视为需要谨慎的风险区域。",
        "看涨": "[ 技术信号解读 ] 技术指标显示价格上涨的概率较高，多个指标都指向乐观的方向。",
        "看跌": "[ 技术信号解读 ] 技术指标显示价格下跌的概率较高，建议保持谨慎或考虑减仓。",
        "中性": "[ 技术信号解读 ] 技术指标没有给出明确的方向，市场处于横盘整理状态，建议等待更清晰的信号。",
    }

    return signal_interpretations.get(
        technical_signal,
        f"[ 技术信号解读 ] 技术指标显示当前状态为 {technical_signal}，建议结合其他指标综合判断。"
    )


def _generate_verdict(
    sentiment_score: float,
    technical_signal: str,
    risk_assessment: str,
    var_value: float,
    indicators: Optional[Dict[str, Any]] = None
) -> str:
    """
    生成动态数据驱动的最终结论 - Verdict 层级

    使用加权评分系统评估多个技术指标，根据不同市场场景生成定制化建议。

    评估维度：
    - Trend: 价格 vs MA20 (Bullish/Bearish)
    - Momentum: RSI (Overbought/Oversold/Neutral)
    - Risk: 风控评估状态
    - Position: Kelly Formula 建议仓位比例
    - Sentiment: 市场情绪评分
    """
    # 初始化指标字典（如果未提供）
    if indicators is None:
        indicators = {}

    # 提取关键指标（提供默认值以确保向后兼容）
    rsi = indicators.get("rsi", 50)  # 默认中性
    price_vs_ma20 = indicators.get("price_vs_ma20", 0)  # 默认平值
    kelly_fraction = indicators.get("kelly_fraction", 0)  # 默认无仓位建议
    kelly_positive_ev = indicators.get("kelly_positive_ev", False)
    current_price = indicators.get("current_price", 0)
    ma20 = indicators.get("ma20", 0)

    # ========== 信号聚合 ==========

    # 1. 趋势信号 (Trend Signal)
    if price_vs_ma20 > 0:
        trend_signal = "BULLISH"  # 价格在 MA20 之上
        trend_score = 1
    elif price_vs_ma20 < 0:
        trend_signal = "BEARISH"  # 价格在 MA20 之下
        trend_score = -1
    else:
        trend_signal = "NEUTRAL"
        trend_score = 0

    # 2. 动量信号 (Momentum Signal - RSI)
    if rsi >= 80:
        momentum_signal = "OVERBOUGHT"  # 超买
        momentum_score = -2  # 强烈负面
    elif rsi >= 70:
        momentum_signal = "STRETCHED"  # 偏高
        momentum_score = -1
    elif rsi <= 20:
        momentum_signal = "OVERSOLD"  # 超卖
        momentum_score = 2  # 强烈正面
    elif rsi <= 30:
        momentum_signal = "DIP"  # 偏低
        momentum_score = 1
    else:
        momentum_signal = "NEUTRAL"  # 中性
        momentum_score = 0

    # 3. 风险信号 (Risk Signal)
    if risk_assessment == "Approved":
        risk_signal = "APPROVED"
        risk_score = 1
    else:
        risk_signal = "REJECTED"
        risk_score = -3  # 风控否决权重最高

    # 4. 仓位信号 (Position Signal - Kelly Formula)
    if kelly_positive_ev and kelly_fraction > 0.50:
        position_signal = "HIGH POSITION"
        position_score = 2
    elif kelly_positive_ev and kelly_fraction > 0.30:
        position_signal = "MODERATE POSITION"
        position_score = 1
    elif kelly_positive_ev and kelly_fraction > 0:
        position_signal = "LIGHT POSITION"
        position_score = 0.5
    elif kelly_fraction == 0:
        position_signal = "NO POSITION"
        position_score = 0
    else:  # Negative EV
        position_signal = "NEGATIVE EV"
        position_score = -2

    # 5. 情绪信号 (Sentiment Signal)
    if sentiment_score >= 70:
        sentiment_signal = "VERY BULLISH"
        sentiment_score_val = 1
    elif sentiment_score >= 60:
        sentiment_signal = "BULLISH"
        sentiment_score_val = 0.5
    elif sentiment_score <= 30:
        sentiment_signal = "VERY BEARISH"
        sentiment_score_val = -1
    elif sentiment_score <= 40:
        sentiment_signal = "BEARISH"
        sentiment_score_val = -0.5
    else:
        sentiment_signal = "NEUTRAL"
        sentiment_score_val = 0

    # ========== 加权评分计算 ==========
    total_score = (
        (trend_score * 2.0) +      # 趋势权重: 2.0
        (momentum_score * 1.5) +   # 动量权重: 1.5
        (risk_score * 3.0) +       # 风险权重: 3.0（最高）
        (position_score * 2.0) +   # 仓位权重: 2.0
        (sentiment_score_val * 1.0) # 情绪权重: 1.0
    )

    # ========== 场景生成 (Scenario-Based Logic) ==========

    # 场景 A: 强烈买入信号
    # 趋势向上 AND Kelly > 30% AND RSI 中性/偏低 AND 风控通过
    if (trend_signal == "BULLISH" and
        kelly_positive_ev and
        kelly_fraction > 0.30 and
        rsi < 70 and
        risk_assessment == "Approved"):

        price_str = f"{current_price:.2f}元" if current_price else "暂无"
        ma20_str = f"{ma20:.2f}元" if ma20 else "暂无"
        verdict = (
            "综合决策结论: 积极看多 - 建仓布局\n\n"
            "数据分析显示健康的上升趋势，风险水平可控。"
            f"当前价格 {price_str} 位于 MA20 ({ma20_str}) 之上，"
            f"表明多头动能强劲。RSI 指标为 {rsi:.1f}，仍处于上升空间。"
            f"凯利公式建议仓位比例为 {kelly_fraction*100:.1f}%。\n\n"
            "操作建议: 可考虑分批建仓。注意关注阻力位，控制仓位风险。"
        )

    # 场景 B: 警告/超买
    # 趋势向上 BUT RSI > 70 (超买)
    elif (trend_signal == "BULLISH" and rsi >= 70):

        if rsi >= 80:
            verdict = (
                "综合决策结论: 极度谨慎 - 严重超买\n\n"
                f"虽然趋势向上(价格位于 MA20 之上)，但 RSI 达到 {rsi:.1f}，"
                "显示极度超买状态。短期内大幅回调的可能性极高。切勿追高买入。\n\n"
                "操作建议: 观望等待。若持有仓位可考虑适当减仓。等待回调至支撑位再考虑入场。"
            )
        else:
            verdict = (
                "综合决策结论: 谨慎建议 - 超买区域\n\n"
                f"趋势向上但 RSI 达到 {rsi:.1f}，显示股票已进入超买区域。"
                "短期可能出现回调。上涨空间可能有限。\n\n"
                "操作建议: 不要追高。等待回调或盘整后再考虑入场。"
            )

    # 场景 C: 看跌/防御
    # 价格 < MA20 AND 动量为负 AND/OR 情绪悲观
    elif (trend_signal == "BEARISH" and
          (momentum_score < 0 or sentiment_score_val < 0)):

        momentum_desc = "动量疲弱" if rsi < 30 else "买盘力量不足"
        verdict = (
            "综合决策结论: 防御姿态 - 避免新建仓位\n\n"
            "股票处于确认的下降趋势(价格位于 MA20 之下)。"
            f"RSI 为 {rsi:.1f}，显示{momentum_desc}。"
            "技术信号疲弱。需等待企稳信号。\n\n"
            "操作建议: 等待趋势反转确认。不要盲目抄底接飞刀。"
        )

    # 场景 D: 超卖反弹机会
    # RSI <= 30 (超卖) AND 风控通过
    elif (rsi <= 30 and risk_assessment == "Approved"):

        verdict = (
            "综合决策结论: 潜在反弹 - 超卖机会\n\n"
            f"RSI 为 {rsi:.1f}，显示超卖状态，暗示可能出现反弹。"
            "这可能是风险承受能力较强投资者的逆向布局机会。\n\n"
            "操作建议: 可考虑轻仓布局，严格设置止损。等待反转确认信号。"
        )

    # 场景 E: 风控否决(最高优先级)
    elif risk_assessment != "Approved":

        verdict = (
            "综合决策结论: 风控否决 - 观望等待\n\n"
            f"风控系统已否决此交易。波动率 {var_value:.2f}% 超过可接受阈值。"
            "保护本金是当前优先事项。\n\n"
            "操作建议: 不要入场。等待波动率下降且风控评估改善后再考虑。"
        )

    # 场景 F: 凯利公式负期望值
    elif not kelly_positive_ev and kelly_fraction == 0:

        verdict = (
            "综合决策结论: 负期望值 - 避免交易\n\n"
            "凯利公式显示为负期望值。从统计学角度，"
            "长期坚持负期望值交易必然导致亏损。不建议任何仓位。\n\n"
            "操作建议: 避免此交易。调整止盈止损参数以提高盈亏比，或等待更好的入场时机。"
        )

    # 场景 G: 混合信号 - 观望
    elif abs(total_score) < 2.0:

        trend_desc = {"BULLISH": "多头", "BEARISH": "空头", "NEUTRAL": "中性"}.get(trend_signal, trend_signal)
        momentum_desc_map = {
            "OVERBOUGHT": "超买", "OVERSOLD": "超卖", "NEUTRAL": "中性",
            "STRETCHED": "偏高", "DIP": "偏低"
        }
        momentum_desc = momentum_desc_map.get(momentum_signal, momentum_signal)
        sentiment_desc = {"VERY BULLISH": "极度看多", "BULLISH": "看多",
                         "VERY BEARISH": "极度看空", "BEARISH": "看空",
                         "NEUTRAL": "中性"}.get(sentiment_signal, sentiment_signal)

        verdict = (
            "综合决策结论: 信号混合 - 观望等待\n\n"
            f"当前指标显示信号冲突: 趋势为{trend_desc}，"
            f"RSI {rsi:.1f} 处于{momentum_desc}状态，"
            f"市场情绪{sentiment_desc}。"
            "没有明确的方向性优势。\n\n"
            "操作建议: 等待更清晰的信号。不要在市场信号不明确时强制交易。"
        )

    # 场景 H: 中性偏正 - 谨慎持有
    elif total_score >= 2.0 and total_score < 5.0:

        verdict = (
            "综合决策结论: 谨慎乐观 - 轻仓布局\n\n"
            f"多项指标偏正面: 综合评分 {total_score:.1f} 显示温和上涨潜力。"
            "但信号强度不足以支持激进建仓。\n\n"
            "操作建议: 可考虑轻仓试探，严格风险管理。保持仓位规模可控。"
        )

    # 场景 I: 强烈看多 - 积极买入
    elif total_score >= 5.0:

        verdict = (
            "综合决策结论: 强烈看多 - 多重确认\n\n"
            f"强烈的看多信号，综合评分达 {total_score:.1f}。"
            "多项指标确认上涨潜力，风险可控。\n\n"
            "操作建议: 可积极建仓。遵循系统化入场计划。严格执行风险管理。"
        )

    # 默认场景 - 观望
    else:

        verdict = (
            "综合决策结论: 观望等待 - 数据不足\n\n"
            "当前市场条件未提供明确的交易机会。"
            "缺乏方向性判断的充分确认。\n\n"
            "操作建议: 等待更好的交易机会。耐心保存资金，把握最佳入场时机。"
        )

    return verdict


def _generate_actionable_steps(
    sentiment_score: float,
    technical_signal: str,
    risk_assessment: str
) -> str:
    """生成可操作建议 - Verdict 层级"""
    steps = "[ 操作建议 ]\n\n"

    if risk_assessment != "Approved":
        steps += (
            "• 暂时不要开仓，等待风控系统通过评估\n"
            "• 关注市场波动率变化，等待风险释放\n"
            "• 考虑调整止盈止损比例以改善风险收益比\n"
        )
        return steps

    if sentiment_score > 60 and technical_signal in ["黄金交叉", "看涨"]:
        steps += (
            "• 可以考虑分批买入，避免一次性重仓\n"
            "• 设置严格的止损位，建议控制在 5-8% 以内\n"
            "• 密切关注成交量变化，确认上涨有量能配合\n"
            "• 预设止盈目标，建议分批止盈锁定利润\n"
        )
    elif sentiment_score < 40:
        steps += (
            "• 保持观望，不要急于抄底\n"
            "• 如果持有仓位，考虑适当减仓保护利润\n"
            "• 等待市场情绪改善或出现明确的反转信号\n"
        )
    else:
        steps += (
            "• 保持耐心，等待更明确的技术信号\n"
            "• 控制仓位，不要过度交易\n"
            "• 严格执行既定的交易纪律\n"
        )

    return steps


if __name__ == "__main__":
    # 测试工具
    print("=== 测试 get_a_share_data ===")
    print(get_a_share_data("600000"))

    print("\n=== 测试 get_latest_news ===")
    print(get_latest_news("600000"))

    print("\n=== 测试 run_backtest ===")
    print(run_backtest("600000", "RSI"))

    print("\n=== 测试 calculate_kelly_position ===")
    print(calculate_kelly_position(68, 100000, 5, 15))
