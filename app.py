"""
StockMate Web UI
基于 Streamlit 的美观用户界面
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockmate.models import StockAnalysisReport
from stockmate.tools.stock_tools import (
    get_a_share_data,
    get_latest_news,
    run_backtest,
    get_stock_name_with_code,
    generate_backtest_insights,
    explain_term,
    generate_human_insight,
    preload_stock_cache,
)
from stockmate.agents import analyze_stock_pipeline, create_stockmate_agent, parse_agent_response
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==================== 页面配置 ====================

st.set_page_config(
    page_title="StockMate (股搭子)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 自定义 CSS 样式 ====================

st.markdown("""
<style>
    /* 主样式 */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }

    .main-header p {
        margin: 0.5rem 0 0;
        opacity: 0.9;
    }

    /* 指标卡片 */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }

    /* 决策卡片 */
    .decision-buy {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        color: #1a5f3a;
    }

    .decision-sell {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        color: #7a2c2c;
    }

    .decision-wait {
        background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        color: #7a4a1a;
    }

    /* 风控状态 */
    .risk-approved {
        color: #28a745;
        font-weight: 600;
    }

    .risk-rejected {
        color: #dc3545;
        font-weight: 600;
    }

    /* 新闻卡片 */
    .news-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #667eea;
    }

    .news-title {
        font-weight: 600;
        margin-bottom: 0.3rem;
    }

    .news-meta {
        font-size: 0.85rem;
        color: #666;
    }

    /* 按钮样式 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* 隐藏滑块旁边的默认数字显示 */
    div[data-testid="stSlider"] > div[data-testid="stMarkdownContainer"] > div {
        display: none;
    }

    /* 止损滑块样式 - 绿色主题 */
    /* 滑块轨道 */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_stop_loss_slider"]::-webkit-slider-runnable-track {
        background: linear-gradient(to right, #4CAF50, #81C784) !important;
        height: 6px !important;
        border-radius: 3px !important;
    }

    /* 滑块拇指（拖动按钮） */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_stop_loss_slider"]::-webkit-slider-thumb {
        -webkit-appearance: none !important;
        appearance: none !important;
        width: 18px !important;
        height: 18px !important;
        background: #4CAF50 !important;
        border-radius: 50% !important;
        cursor: pointer !important;
        box-shadow: 0 2px 6px rgba(76, 175, 80, 0.4) !important;
    }

    /* Firefox 支持 */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_stop_loss_slider"]::-moz-range-track {
        background: linear-gradient(to right, #4CAF50, #81C784) !important;
        height: 6px !important;
        border-radius: 3px !important;
    }

    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_stop_loss_slider"]::-moz-range-thumb {
        width: 18px !important;
        height: 18px !important;
        background: #4CAF50 !important;
        border-radius: 50% !important;
        cursor: pointer !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(76, 175, 80, 0.4) !important;
    }

    /* 止盈滑块样式 - 红色主题 */
    /* 滑块轨道 */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_take_profit_slider"]::-webkit-slider-runnable-track {
        background: linear-gradient(to right, #F44336, #E57373) !important;
        height: 6px !important;
        border-radius: 3px !important;
    }

    /* 滑块拇指（拖动按钮） */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_take_profit_slider"]::-webkit-slider-thumb {
        -webkit-appearance: none !important;
        appearance: none !important;
        width: 18px !important;
        height: 18px !important;
        background: #F44336 !important;
        border-radius: 50% !important;
        cursor: pointer !important;
        box-shadow: 0 2px 6px rgba(244, 67, 54, 0.4) !important;
    }

    /* Firefox 支持 */
    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_take_profit_slider"]::-moz-range-track {
        background: linear-gradient(to right, #F44336, #E57373) !important;
        height: 6px !important;
        border-radius: 3px !important;
    }

    div[data-testid="stSlider"] div[role="slider"][aria-label*="kelly_take_profit_slider"]::-moz-range-thumb {
        width: 18px !important;
        height: 18px !important;
        background: #F44336 !important;
        border-radius: 50% !important;
        cursor: pointer !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(244, 67, 54, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 辅助函数 ====================

def normalize_symbol(symbol: str) -> str:
    """标准化股票代码"""
    if "." in symbol:
        symbol = symbol.split(".")[0]
    return symbol.strip().zfill(6)


def decision_emoji(decision: str) -> str:
    """获取决策对应的表情"""
    return {"Buy": "🟢", "Sell": "🔴", "Wait": "🟡"}.get(decision, "⚪")


def decision_class(decision: str) -> str:
    """获取决策对应的 CSS 类"""
    return {"Buy": "decision-buy", "Sell": "decision-sell", "Wait": "decision-wait"}.get(
        decision, ""
    )


def create_price_chart(data_result: dict) -> go.Figure:
    """创建价格走势图"""
    if not data_result.get("success"):
        return None

    # 这里需要重新获取数据以获取完整的价格序列
    symbol = data_result["ticker"]
    import akshare as ak
    from datetime import timedelta

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )

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

        # 创建图表
        fig = go.Figure()

        # K线图
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="K线",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )
        )

        # 移动平均线
        df["MA5"] = df["Close"].rolling(window=5).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["MA5"],
                name="MA5",
                line=dict(color="#2962ff", width=1),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["MA20"],
                name="MA20",
                line=dict(color="#ff6d00", width=1),
            )
        )

        fig.update_layout(
            title="价格走势图",
            xaxis_title="日期",
            yaxis_title="价格 (元)",
            height=400,
            hovermode="x unified",
            template="plotly_white",
            margin=dict(l=0, r=0, t=40, b=0),
        )

        return fig

    except Exception:
        return None


def create_backtest_chart(backtest_result: dict) -> go.Figure:
    """
    创建回测收益曲线图

    Args:
        backtest_result: 回测结果字典，包含 equity_curve 和 dates

    Returns:
        plotly Figure 对象
    """
    fig = go.Figure()

    # 检查是否有收益曲线数据
    if backtest_result.get("equity_curve") and backtest_result.get("dates"):
        equity_curve = backtest_result["equity_curve"]
        dates = backtest_result["dates"]
        strategy = backtest_result.get("strategy", "策略")

        # 添加收益曲线
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=equity_curve,
                name=f"{strategy} 策略收益",
                line=dict(color="#26a69a", width=2),
                fill="tozeroy",  # 填充到零轴
                fillcolor="rgba(38, 166, 154, 0.1)",
            )
        )

        # 添加零线（基准线）
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            annotation_text="盈亏平衡线"
        )

        fig.update_layout(
            title=f"{strategy} 策略回测收益曲线",
            xaxis_title="日期",
            yaxis_title="累计收益率 (%)",
            height=350,
            template="plotly_white",
            hovermode="x unified",
            showlegend=True,
        )

        # 设置 x 轴格式
        fig.update_xaxes(
            tickangle=-45,
            nticks=10  # 限制 x 轴刻度数量
        )

    else:
        # 如果没有数据，显示空图表提示
        fig.add_annotation(
            text="暂无收益曲线数据<br>请先运行回测",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )

        fig.update_layout(
            title="回测收益曲线",
            xaxis_title="日期",
            yaxis_title="累计收益率 (%)",
            height=300,
            template="plotly_white",
        )

    return fig


# ==================== 主界面 ====================

def main():
    # 预加载股票缓存（后台运行，避免第一次分析时的延迟）
    if 'cache_preloaded' not in st.session_state:
        preload_stock_cache()
        st.session_state.cache_preloaded = True

    # 页面标题
    st.markdown("""
    <div class="main-header">
        <h1>📈 StockMate (股搭子)</h1>
        <p>智能股票投资辅助 Agent 系统 - 基于多智能体协作的量化分析平台</p>
    </div>
    """, unsafe_allow_html=True)

    # 侧边栏
    with st.sidebar:
        st.title("⚙️ 配置面板")

        # 分析模式选择
        st.subheader("分析模式")
        mode = st.radio(
            "选择分析模式",
            ["本地快速分析", "LLM 智能分析"],
            help="本地模式更快但分析简单，LLM 模式更智能但需要 API Key",
        )

        # API 配置
        if mode == "LLM 智能分析":
            st.subheader("API 配置")
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="请输入您的 OpenAI API Key",
            )
            base_url = st.text_input(
                "API Base URL",
                value="https://api.openai.com/v1",
                help="如果使用第三方服务，请修改此地址",
            )
            model_name = st.text_input(
                "模型名称",
                value="gpt-4o-mini",
                help="使用的模型名称",
            )

        # 股票代码输入
        st.subheader("股票分析")
        symbol = st.text_input(
            "股票代码",
            placeholder="例如: 600000 或 000001",
            help="请输入6位股票代码",
            key="stock_code_input"  # 添加 key 以支持变化检测
        )

        # 检测股票代码变化，清空之前的分析结果
        if 'last_symbol' in st.session_state and st.session_state.last_symbol != symbol:
            # 股票代码已变化，清空之前的分析结果
            if 'report' in st.session_state:
                del st.session_state.report

        # 记录当前股票代码
        st.session_state.last_symbol = symbol

        # 回测策略选择
        st.subheader("回测配置")
        backtest_strategy = st.selectbox(
            "回测策略",
            ["RSI", "MA", "Bollinger"],
            help="选择用于验证的技术指标策略",
        )

        # 凯利公式仓位管理配置
        st.subheader("💰 凯利公式仓位管理")

        with st.expander("📊 仓位管理配置", expanded=True):
            planned_capital = st.number_input(
                "拟投入资金（元）",
                min_value=1000,
                max_value=10000000,
                value=100000,
                step=10000,
                help="您计划用于此交易的总资金"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<span style="color:#4CAF50;font-size:1rem;font-weight:bold;">🟢 止损比例</span>', unsafe_allow_html=True)
                stop_loss_pct = st.slider(
                    "",
                    min_value=1.0,
                    max_value=20.0,
                    value=5.0,
                    step=0.5,
                    key="kelly_stop_loss_slider",
                    help="当价格下跌到此比例时止损",
                    label_visibility="collapsed"
                )
                # 显示绿色的当前值
                st.markdown(
                    f'<div style="text-align:center;color:#4CAF50;font-weight:bold;font-size:1.2rem;margin-top:-0.5rem;">{stop_loss_pct}%</div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown('<span style="color:#F44336;font-size:1rem;font-weight:bold;">🔴 止盈比例</span>', unsafe_allow_html=True)
                take_profit_pct = st.slider(
                    "",
                    min_value=1.0,
                    max_value=50.0,
                    value=15.0,
                    step=0.5,
                    key="kelly_take_profit_slider",
                    help="当价格上涨到此比例时止盈",
                    label_visibility="collapsed"
                )
                # 显示红色的当前值
                st.markdown(
                    f'<div style="text-align:center;color:#F44336;font-weight:bold;font-size:1.2rem;margin-top:-0.5rem;">{take_profit_pct}%</div>',
                    unsafe_allow_html=True
                )

            # 显示计算的盈亏比
            actual_win_loss_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 0
            st.info(f"📈 当前盈亏比（赔率 b）: {actual_win_loss_ratio:.2f}")

            st.markdown("""
            <div style="font-size:0.85rem;color:#666;margin-top:0.5rem;">
            💡 <b>凯利公式说明</b>：系统将根据回测胜率和此处的盈亏比计算最优仓位。
            负期望值时系统将强制否决交易。
            </div>
            """, unsafe_allow_html=True)

        # 常用股票快捷按钮
        st.subheader("快捷操作")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("浦发银行"):
                symbol = "600000"
        with col2:
            if st.button("平安银行"):
                symbol = "000001"

        st.info("💡 提示: 本地模式无需 API 即可使用，LLM 模式需要配置 API Key")

    # 主内容区
    if not symbol:
        st.info("👈 请在左侧输入股票代码开始分析")
        return

    symbol = normalize_symbol(symbol)

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📊 综合分析", "📰 市场新闻", "📈 技术回测", "ℹ️ 关于"])

    # ==================== 标签页 1: 综合分析 ====================
    with tab1:
        # 获取股票名称并显示友好的标题
        stock_display_name = get_stock_name_with_code(symbol)
        st.header(f"📊 {stock_display_name} 投资分析报告")

        # 决策信号说明卡片
        st.markdown("""
        <style>
        .signal-guide-container {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        .signal-guide-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .signal-cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 15px;
        }
        .signal-card {
            background: white;
            border-radius: 10px;
            padding: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .signal-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        .signal-icon {
            font-size: 1.8rem;
            margin-bottom: 5px;
        }
        .signal-name {
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 3px;
        }
        .signal-desc {
            font-size: 0.75rem;
            color: #666;
        }
        .risk-alert {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 8px;
            padding: 12px 15px;
            margin-top: 12px;
            font-size: 0.85rem;
        }
        .risk-alert-title {
            font-weight: 600;
            color: #856404;
            margin-bottom: 5px;
        }
        .risk-alert-text {
            color: #856404;
            line-height: 1.5;
        }
        .approval-status {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 10px;
            padding-top: 15px;
            border-top: 1px solid rgba(0,0,0,0.1);
        }
        .approval-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
        }
        @media (max-width: 768px) {
            .signal-cards {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        </style>

        <div class="signal-guide-container">
            <div class="signal-guide-title">
                📖 决策信号快速参考
            </div>
            <div class="signal-cards">
                <div class="signal-card">
                    <div class="signal-icon">🟢</div>
                    <div class="signal-name" style="color: #4CAF50;">Buy</div>
                    <div class="signal-desc">买入信号<br>可考虑买入</div>
                </div>
                <div class="signal-card">
                    <div class="signal-icon">🔴</div>
                    <div class="signal-name" style="color: #F44336;">Sell</div>
                    <div class="signal-desc">卖出信号<br>可考虑卖出</div>
                </div>
                <div class="signal-card">
                    <div class="signal-icon">🟡</div>
                    <div class="signal-name" style="color: #FF9800;">Wait</div>
                    <div class="signal-desc">观望信号<br>暂时不操作</div>
                </div>
                <div class="signal-card">
                    <div class="signal-icon">⚪</div>
                    <div class="signal-name" style="color: #9E9E9E;">Hold</div>
                    <div class="signal-desc">持有信号<br>保持仓位不动</div>
                </div>
            </div>
            <div class="approval-status">
                <div class="approval-item">
                    <span style="font-size: 1.2rem;">✅</span>
                    <span><strong>通过</strong> - 风控评估通过，可交易</span>
                </div>
                <div class="approval-item">
                    <span style="font-size: 1.2rem;">❌</span>
                    <span><strong>否决</strong> - 风险过高，强制否决交易</span>
                </div>
            </div>
            <div class="risk-alert">
                <div class="risk-alert-title">⚠️ 风控一票否决权</div>
                <div class="risk-alert-text">
                    风控官拥有最高否决权。当波动率过高或凯利公式计算为负期望值时，即使其他信号强烈，最终决策也将被强制为 <strong>Wait</strong>。
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 分析按钮
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            with st.spinner("正在进行多智能体分析，请稍候..."):
                try:
                    if mode == "LLM 智能分析" and api_key:
                        # 使用 LLM Agent
                        agent = create_stockmate_agent(
                            model_name=model_name,
                            api_key=api_key,
                            base_url=base_url,
                        )
                        prompt = f"""请分析股票 {symbol}。

请按以下步骤操作：
1. 使用 get_stock_info("{symbol}") 获取行情数据
2. 使用 get_stock_news("{symbol}") 获取最新新闻
3. 使用 backtest_strategy("{symbol}", "{backtest_strategy}") 进行回测
4. 综合分析并以 JSON 格式输出 StockAnalysisReport"""
                        response = agent.run(prompt)
                        report = parse_agent_response(str(response))
                        report.ticker = symbol
                    else:
                        # 使用本地管道，传递凯利公式参数
                        kelly_params = {
                            "planned_capital": planned_capital,
                            "stop_loss_pct": stop_loss_pct,
                            "take_profit_pct": take_profit_pct,
                        }
                        report = analyze_stock_pipeline(symbol, kelly_params=kelly_params)

                    # 保存到 session state
                    st.session_state.report = report

                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
                    return

        # 显示分析结果
        if "report" in st.session_state:
            report = st.session_state.report

            # 最终决策卡片
            decision_class_name = decision_class(report.final_decision)
            st.markdown(f"""
            <div class="{decision_class_name}">
                <h2 style="margin:0;">{decision_emoji(report.final_decision)} {report.final_decision.upper()}</h2>
                <p style="margin:0.5rem 0 0;font-size:1.1rem;">基于多智能体综合分析</p>
            </div>
            """, unsafe_allow_html=True)

            # 核心指标
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="情绪评分",
                    value=f"{report.sentiment_score:.1f}",
                    delta="看涨" if report.sentiment_score > 60 else "看跌" if report.sentiment_score < 40 else "中性"
                )

            with col2:
                st.metric(
                    label="技术信号",
                    value=report.technical_signal,
                )

            with col3:
                risk_class = "risk-approved" if report.risk_assessment == "Approved" else "risk-rejected"
                st.markdown(f"""
                <div style="text-align:center;">
                    <div class="metric-label">风控评估</div>
                    <div class="{risk_class}" style="font-size:1.5rem;">
                        {'✅ 通过' if report.risk_assessment == 'Approved' else '❌ 否决'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                st.metric(
                    label="波动率",
                    value=f"{report.var_value:.2f}%",
                )

            # 回测结果
            if report.backtest_win_rate is not None:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        label="历史胜率",
                        value=f"{report.backtest_win_rate:.1f}%",
                    )
                with col2:
                    st.metric(
                        label="历史收益",
                        value=f"{report.backtest_return:.1f}%",
                    )

            # 凯利公式仓位建议 - 始终显示
            st.subheader("💰 凯利公式仓位建议")

            if report.kelly_result is not None:
                kelly = report.kelly_result

                # 创建凯利公式结果卡片
                if kelly.is_positive_ev:
                    # 正期望值 - 显示建议
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                                border-radius:10px;padding:1.5rem;margin-bottom:1rem;">
                        <h3 style="margin:0;color:#1a5f3a;">✅ 正期望值交易</h3>
                        <p style="margin:0.5rem 0 0;color:#1a5f3a;">
                            凯利公式建议可以开仓，但请注意风险控制
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 核心指标
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            label="建议仓位比例",
                            value=f"{kelly.kelly_fraction:.1%}",
                            delta="凯利公式"
                        )

                    with col2:
                        st.metric(
                            label="建议投入金额",
                            value=f"¥{kelly.recommended_amount:,.0f}",
                            delta=f"占计划资金 {kelly.kelly_fraction:.1%}"
                        )

                    with col3:
                        st.metric(
                            label="半凯利（保守）",
                            value=f"¥{kelly.half_kelly_amount:,.0f}",
                            delta="推荐使用"
                        )

                    # 期望值和风险提示
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            label="期望值 (EV)",
                            value=f"{kelly.expected_value:.4f}",
                            delta="正期望值 ✅"
                        )

                    with col2:
                        st.info(f"📊 输入参数：胜率 {kelly.win_probability:.1f}% | 盈亏比 {kelly.win_loss_ratio:.2f}")

                    # 风险提示
                    st.warning(kelly.risk_warning)

                    # 专业提示
                    st.markdown("""
                    <div style="background:#f0f7ff;border-left:4px solid #2196F3;padding:1rem;margin-top:1rem;">
                        <h4 style="margin:0 0 0.5rem;color:#1976D2;">💡 专业提示</h4>
                        <ul style="margin:0;padding-left:1.5rem;color:#333;">
                            <li><b>半凯利公式</b>：许多专业投资者使用半凯利以降低回撤风险</li>
                            <li><b>分散投资</b>：不要将所有资金投入单一标的</li>
                            <li><b>动态调整</b>：根据市场变化及时调整仓位</li>
                            <li><b>止损纪律</b>：严格执行预设的止损策略</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 负期望值 - 显示否决警告
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                                border-radius:10px;padding:2rem;text-align:center;">
                        <h2 style="margin:0;color:#7a2c2c;">⚠️ 凯利公式否决交易</h2>
                        <p style="margin:1rem 0 0;font-size:1.1rem;color:#7a2c2c;">
                            {kelly.risk_warning}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            label="期望值 (EV)",
                            value=f"{kelly.expected_value:.4f}",
                            delta="负期望值 ❌"
                        )
                    with col2:
                        st.metric(
                            label="获胜概率",
                            value=f"{kelly.win_probability:.1f}%",
                        )

                    st.error("""
                    **不建议进行此交易**

                    凯利公式显示此交易具有负期望值，长期坚持负期望值交易必然导致亏损。
                    请等待更好的入场机会，或调整止盈止损比例以提高盈亏比。
                    """)
            else:
                # 凯利结果为空时显示说明
                if report.backtest_win_rate is not None:
                    # 有回测数据但计算失败
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg, #f6d365 0%, #fda085 100%);
                                border-radius:10px;padding:2rem;text-align:center;">
                        <h2 style="margin:0;color:#7a2c2c;">⚠️ 无法计算凯利仓位建议</h2>
                        <p style="margin:1rem 0 0;font-size:1.1rem;color:#7a2c2c;">
                            当前风险收益比不足以为凯利公式提供可靠建议。<br>
                            <b>建议仓位：0%（不建议开仓）</b>
                        </p>
                        <p style="margin:0.5rem 0 0;color:#7a2c2c;font-size:0.9rem;">
                            原因：历史胜率 ({report.backtest_win_rate:.1f}%) 可能不足以支撑正期望值交易。
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 无回测数据
                    st.info("""
                    **💡 凯利公式仓位计算**

                    要获取凯利公式的最优仓位建议，请确保：
                    1. 系统已成功获取历史回测数据
                    2. 在左侧配置了凯利公式参数（拟投入资金、止损比例、止盈比例）

                    <small>凯利公式根据历史胜率和您设置的盈亏比，计算 mathematically 最优的投资仓位比例。</small>
                    """)

            # 人类洞察引擎 - 生成投资建议
            st.subheader("🧠 投资洞察分析")

            # 获取股票数据用于洞察分析
            data_result = get_a_share_data(symbol)

            if data_result["success"]:
                # 计算技术指标
                from stockmate.tools.stock_tools import calculate_technical_indicators
                import akshare as ak
                from datetime import timedelta

                # 获取历史数据用于计算指标
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

                df = None
                try:
                    df_temp = ak.stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq",
                    )
                    column_mapping = {
                        "日期": "date",
                        "开盘": "Open",
                        "最高": "High",
                        "最低": "Low",
                        "收盘": "Close",
                        "成交量": "Volume",
                    }
                    df = df_temp.rename(columns=column_mapping)
                except Exception as e:
                    st.warning(f"获取历史数据失败: {e}")

                # 计算技术指标
                indicators = calculate_technical_indicators(
                    df=df,
                    current_price=data_result.get("current_price", 0)
                )

                # 添加凯利公式指标
                if report.kelly_result:
                    indicators["kelly_fraction"] = report.kelly_result.kelly_fraction
                    indicators["kelly_positive_ev"] = report.kelly_result.is_positive_ev
                else:
                    indicators["kelly_fraction"] = 0
                    indicators["kelly_positive_ev"] = False

                # 生成人类洞察
                human_insight = generate_human_insight(
                    stock_data=data_result,
                    sentiment_score=report.sentiment_score,
                    technical_signal=report.technical_signal,
                    var_value=report.var_value,
                    risk_assessment=report.risk_assessment,
                    indicators=indicators
                )

                # Observation 层级 - 市场观察
                st.markdown("### 📊 市场观察 (OBSERVATION)")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"""
                    <div style="background:#f0f4ff;border-left:4px solid #2196F3;padding:1rem;border-radius:8px;">
                        <div style="font-size:0.75rem;color:#666;margin-bottom:0.5rem;">价格走势</div>
                        <div style="font-size:0.9rem;color:#333;line-height:1.4;">
                            {human_insight['observation_trend']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background:#fff3e0;border-left:4px solid #FF9800;padding:1rem;border-radius:8px;">
                        <div style="font-size:0.75rem;color:#666;margin-bottom:0.5rem;">波动性</div>
                        <div style="font-size:0.9rem;color:#333;line-height:1.4;">
                            {human_insight['observation_volatility']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div style="background:#e8f5e9;border-left:4px solid #4CAF50;padding:1rem;border-radius:8px;">
                        <div style="font-size:0.75rem;color:#666;margin-bottom:0.5rem;">市场情绪</div>
                        <div style="font-size:0.9rem;color:#333;line-height:1.4;">
                            {human_insight['observation_sentiment']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")

                # Interpretation 层级 - 深度解读
                st.markdown("### 🔍 深度解读 (INTERPRETATION)")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"""
                    <div style="background:#fff9c4;border-left:4px solid #FBC02D;padding:1.2rem;border-radius:8px;margin-bottom:1rem;">
                        <div style="font-weight:600;color:#F57F17;margin-bottom:0.5rem;">💰 投资机会</div>
                        <div style="font-size:0.95rem;color:#333;line-height:1.6;">
                            {human_insight['interpretation_opportunity']}
                        </div>
                    </div>

                    <div style="background:#ffebee;border-left:4px solid #EF5350;padding:1.2rem;border-radius:8px;">
                        <div style="font-weight:600;color:#C62828;margin-bottom:0.5rem;">⚠️ 风险评估</div>
                        <div style="font-size:0.95rem;color:#333;line-height:1.6;">
                            {human_insight['interpretation_risk']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background:#e1f5fe;border-left:4px solid #039BE5;padding:1.2rem;border-radius:8px;">
                        <div style="font-weight:600;color:#0277BD;margin-bottom:0.5rem;">📈 技术信号</div>
                        <div style="font-size:0.95rem;color:#333;line-height:1.6;">
                            {human_insight['interpretation_technical']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")

                # Verdict 层级 - 最终建议
                st.markdown("### 📊 综合分析结论")

                # 解析并美化综合决策结论文本
                verdict_raw = human_insight['verdict_summary']

                # 基于中文关键词判断信号类型和颜色
                # 积极信号：看多、建仓、反弹、积极
                # 谨慎信号：谨慎、超买、轻仓
                # 消极/观望信号：防御、观望、否决、避免、等待
                positive_keywords = ["积极看多", "建仓布局", "潜在反弹", "强烈看多"]
                cautious_keywords = ["谨慎", "超买", "轻仓布局"]
                negative_keywords = ["防御姿态", "观望等待", "风控否决", "负期望值", "避免交易", "信号混合"]

                verdict_raw_lower = verdict_raw.lower()
                if any(kw in verdict_raw for kw in positive_keywords):
                    # 积极/看多 - 使用绿色系但更柔和
                    verdict_color = "#2E7D32"  # 深绿色
                    verdict_emoji = "📈"
                elif any(kw in verdict_raw for kw in cautious_keywords):
                    # 谨慎 - 使用橙色系
                    verdict_color = "#F57C00"  # 深橙色
                    verdict_emoji = "⚖️"
                else:
                    # 观望/中性 - 使用蓝色系（更中性、专业）
                    verdict_color = "#1976D2"  # 深蓝色
                    verdict_emoji = "📊"

                # 提取结论标题（冒号后的部分）
                verdict_signal = "综合分析"
                verdict_desc = verdict_raw

                # 解析新格式的结论文本 "综合决策结论: XXX - XXX"
                if "综合决策结论:" in verdict_raw:
                    parts = verdict_raw.split("综合决策结论:", 1)[1].split("\n\n", 1)
                    if len(parts) >= 1:
                        signal_part = parts[0].strip()
                        verdict_signal = signal_part
                    if len(parts) >= 2:
                        verdict_desc = parts[1].strip()

                # 处理描述文本中的换行
                import html as html_lib
                verdict_desc_html = verdict_desc.replace('\n\n', '<br><br>').replace('\n', '<br>')

                # 处理具体操作步骤 - 不使用 html.escape，直接渲染文本
                actionable_raw = human_insight['verdict_actionable']
                # 移除开头的 "[ 操作建议 ]\n\n"
                if actionable_raw.startswith("[ 操作建议 ]\n\n"):
                    actionable_raw = actionable_raw.replace("[ 操作建议 ]\n\n", "", 1)

                # 分割每个步骤并格式化
                steps_list = actionable_raw.strip().split('\n')
                actionable_items = []
                for step in steps_list:
                    step = step.strip()
                    if step:
                        # 移除开头的 •
                        if step.startswith('•'):
                            step = step[1:].strip()
                        actionable_items.append(step)

                # 生成HTML，使用format避免转义问题
                actionable_html = ""
                for step in actionable_items:
                    actionable_html += (
                        f'<div style="display:flex;align-items:start;margin-top:0.8rem;">'
                        f'<span style="color:{verdict_color};font-size:1.2rem;margin-right:0.6rem;margin-top:0.1rem;">•</span>'
                        f'<span style="flex:1;color:#333;line-height:1.7;">{step}</span>'
                        f'</div>'
                    )

                # 综合决策结论部分 - 优化为更专业、中性的设计
                verdict_html = f"""
                <div style="background:linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
                          border-left:4px solid {verdict_color};
                          padding:1.8rem;border-radius:12px;margin-bottom:1.5rem;
                          box-shadow:0 2px 12px rgba(0,0,0,0.06);">
                    <div style="display:flex;align-items:center;margin-bottom:1rem;">
                        <span style="font-size:2rem;margin-right:0.7rem;">{verdict_emoji}</span>
                        <div>
                            <div style="font-weight:700;color:#1a1a1a;font-size:1.25rem;letter-spacing:0.3px;">
                                综合分析结论
                            </div>
                            <div style="font-size:0.8rem;color:#666;margin-top:0.15rem;">
                                多因子加权评分模型
                            </div>
                        </div>
                    </div>
                    <div style="background:white;padding:1.3rem;border-radius:10px;
                               border:1px solid #e0e0e0;
                               box-shadow:0 1px 4px rgba(0,0,0,0.03);">
                        <div style="display:inline-block;background:{verdict_color};color:white;
                                   font-weight:600;padding:0.35rem 0.9rem;border-radius:6px;
                                   font-size:0.85rem;margin-bottom:0.9rem;letter-spacing:0.5px;">
                            {verdict_signal}
                        </div>
                        <div style="font-size:1rem;color:#2c3e50;line-height:1.8;font-weight:400;">
                            {verdict_desc_html}
                        </div>
                    </div>
                </div>
                """

                # 具体操作步骤部分 - 更简洁的设计
                actionable_section_html = f"""
                <div style="background:#ffffff;border-radius:12px;padding:1.5rem;
                          box-shadow:0 2px 8px rgba(0,0,0,0.04);
                          border:1px solid #e8e8e8;">
                    <div style="display:flex;align-items:center;margin-bottom:1rem;
                               padding-bottom:0.7rem;border-bottom:1px solid #eee;">
                        <span style="font-size:1.5rem;margin-right:0.5rem;">📝</span>
                        <div>
                            <div style="font-weight:600;color:#333;font-size:1.1rem;">
                                操作建议
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.95rem;color:#444;line-height:1.7;">
                        {actionable_html}
                    </div>
                </div>
                """

                st.markdown(verdict_html + actionable_section_html, unsafe_allow_html=True)

            # AI 深度分析部分
            st.markdown("---")
            st.subheader("🤖 AI 深度分析")

            # 获取数据用于 AI 分析
            if data_result["success"]:
                with st.spinner("正在生成 AI 深度分析..."):
                    try:
                        from stockmate.tools.llm_service import (
                            generate_comprehensive_analysis,
                            generate_risk_warning,
                            generate_key_points_analysis,
                            generate_market_outlook,
                            generate_trading_strategy
                        )

                        # 准备数据
                        company_name = get_stock_name_with_code(symbol)
                        current_price = data_result.get("current_price", 0)
                        change_pct = data_result.get("change_pct", 0)
                        sentiment_score = report.sentiment_score
                        technical_signal = report.technical_signal
                        volatility = report.var_value

                        # 计算技术指标
                        import akshare as ak
                        from datetime import timedelta
                        end_date = datetime.now().strftime("%Y%m%d")
                        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

                        rsi_value = None
                        ma_trend = None
                        try:
                            df_temp = ak.stock_zh_a_hist(
                                symbol=symbol,
                                period="daily",
                                start_date=start_date,
                                end_date=end_date,
                                adjust="qfq",
                            )
                            column_mapping = {
                                "日期": "date",
                                "开盘": "Open",
                                "最高": "High",
                                "最低": "Low",
                                "收盘": "Close",
                                "成交量": "Volume",
                            }
                            df_temp = df_temp.rename(columns=column_mapping)

                            # 计算 RSI
                            delta = df_temp["Close"].diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                            rs = gain / loss
                            rsi = 100 - (100 / (1 + rs))
                            rsi_value = float(rsi.iloc[-1]) if len(rsi) > 0 else None

                            # 计算 MA 趋势
                            df_temp["MA5"] = df_temp["Close"].rolling(window=5).mean()
                            df_temp["MA20"] = df_temp["Close"].rolling(window=20).mean()
                            ma5 = df_temp["MA5"].iloc[-1]
                            ma20 = df_temp["MA20"].iloc[-1]
                            if ma5 > ma20:
                                ma_trend = "多头排列（MA5 > MA20）"
                            elif ma5 < ma20:
                                ma_trend = "空头排列（MA5 < MA20）"
                            else:
                                ma_trend = "中性"
                        except:
                            pass

                        # 1. 全面分析
                        with st.expander("📊 全面分析报告", expanded=True):
                            comprehensive = generate_comprehensive_analysis(
                                symbol=symbol,
                                company_name=company_name,
                                current_price=current_price,
                                change_pct=change_pct,
                                sentiment_score=sentiment_score,
                                technical_signal=technical_signal,
                                win_rate=report.backtest_win_rate,
                                total_return=report.backtest_return
                            )
                            if "暂无智能分析" not in comprehensive and "分析生成失败" not in comprehensive:
                                st.markdown(f"""
                                <div style="background:linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                                          padding:1.5rem;border-radius:12px;border-left:4px solid #2196F3;">
                                    <div style="color:#1565C0;font-weight:600;margin-bottom:0.5rem;">🎯 综合评估</div>
                                    <div style="color:#333;line-height:1.8;">{comprehensive}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 2. 关键分析要点
                        with st.expander("🔑 关键分析要点"):
                            keypoints = generate_key_points_analysis(
                                symbol=symbol,
                                current_price=current_price,
                                rsi=rsi_value,
                                ma_trend=ma_trend
                            )
                            if "暂无智能分析" not in keypoints and "分析生成失败" not in keypoints:
                                st.markdown(f"""
                                <div style="background:#f8f9fa;padding:1.2rem;border-radius:10px;">
                                    <div style="color:#495057;line-height:2;white-space:pre-wrap;">{keypoints}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 3. 风险提示
                        with st.expander("⚠️ 风险评估与控制"):
                            position_size = report.kelly_result.kelly_fraction if report.kelly_result else 0
                            max_dd = volatility * 1.5  # 估算最大回撤
                            risk_warning = generate_risk_warning(
                                symbol=symbol,
                                volatility=volatility,
                                max_drawdown=max_dd,
                                position_size=position_size
                            )
                            if "暂无智能分析" not in risk_warning and "分析生成失败" not in risk_warning:
                                st.markdown(f"""
                                <div style="background:#fff3cd;padding:1.2rem;border-radius:10px;border-left:4px solid #ffc107;">
                                    <div style="color:#856404;line-height:1.8;">{risk_warning}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 4. 市场展望
                        with st.expander("🔮 市场展望（1-3个月）"):
                            market_trend = "上涨" if change_pct > 0 else "下跌" if change_pct < 0 else "震荡"
                            outlook = generate_market_outlook(
                                symbol=symbol,
                                sentiment_score=sentiment_score,
                                technical_signal=technical_signal,
                                market_trend=market_trend
                            )
                            if "暂无智能分析" not in outlook and "分析生成失败" not in outlook:
                                st.markdown(f"""
                                <div style="background:#e1f5fe;padding:1.2rem;border-radius:10px;border-left:4px solid #03a9f4;">
                                    <div style="color:#01579b;line-height:1.8;">{outlook}</div>
                                </div>
                                """, unsafe_allow_html=True)

                        # 5. 交易策略建议
                        if planned_capital and stop_loss_pct and take_profit_pct:
                            with st.expander("💡 交易策略建议"):
                                stop_loss_price = current_price * (1 - stop_loss_pct / 100)
                                take_profit_price = current_price * (1 + take_profit_pct / 100)
                                strategy = generate_trading_strategy(
                                    symbol=symbol,
                                    current_price=current_price,
                                    stop_loss=stop_loss_price,
                                    take_profit=take_profit_price,
                                    risk_tolerance="medium"
                                )
                                if "暂无智能分析" not in strategy and "分析生成失败" not in strategy:
                                    st.markdown(f"""
                                    <div style="background:#f1f8e9;padding:1.2rem;border-radius:10px;border-left:4px solid #689f38;">
                                        <div style="color:#33691e;line-height:1.8;">{strategy}</div>
                                    </div>
                                    """, unsafe_allow_html=True)

                    except Exception as e:
                        st.warning(f"AI 分析生成失败: {str(e)}")

            # 原始决策依据（折叠）
            with st.expander("🔧 查看原始决策依据（技术性）"):
                st.info(report.reasoning)

            # 获取价格数据并绘图
            st.subheader("📈 价格走势图")
            with st.spinner("加载图表数据..."):
                if data_result["success"]:
                    fig = create_price_chart(data_result)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

    # ==================== 标签页 2: 市场新闻 ====================
    with tab2:
        st.header(f"📰 {stock_display_name} 最新资讯")

        if st.button("🔄 刷新新闻", use_container_width=True):
            with st.spinner("获取最新新闻..."):
                news_result = get_latest_news(symbol)
                st.session_state.news = news_result

        if "news" in st.session_state:
            news_result = st.session_state.news

            if news_result["success"]:
                st.success(f"✅ 获取到 {news_result['news_count']} 条最新资讯")

                for i, news in enumerate(news_result["news"], 1):
                    # 如果有URL，显示为可点击链接
                    if news.get('url'):
                        st.markdown(f"""
                        <div class="news-card">
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
                                <span style="background:#2196F3;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:0.9rem;">{i}</span>
                                <div class="news-title">
                                    <a href="{news['url']}" target="_blank" style="color:#1976D2;text-decoration:none;font-weight:600;">
                                        {news['title']} 🔗
                                    </a>
                                </div>
                            </div>
                            <div class="news-meta" style="margin-left:38px;">
                                📅 {news['publish_time']} | 📰 {news['source']}
                            </div>
                            <div style="margin-left:38px;margin-top:0.5rem;color:#555;font-size:0.9rem;line-height:1.5;">
                                {news['content'][:150]}...
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # 没有URL，显示普通文本
                        st.markdown(f"""
                        <div class="news-card">
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
                                <span style="background:#9E9E9E;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:0.9rem;">{i}</span>
                                <div class="news-title" style="color:#333;font-weight:600;">
                                    {news['title']}
                                </div>
                            </div>
                            <div class="news-meta" style="margin-left:38px;">
                                📅 {news['publish_time']} | 📰 {news['source']}
                            </div>
                            <div style="margin-left:38px;margin-top:0.5rem;color:#555;font-size:0.9rem;line-height:1.5;">
                                {news['content'][:150]}...
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error(f"❌ {news_result['error']}")
        else:
            st.info("点击上方按钮获取最新资讯")

    # ==================== 标签页 3: 技术回测 ====================
    with tab3:
        st.header(f"📈 {stock_display_name} 技术回测")

        # 回测参数
        col1, col2 = st.columns(2)
        with col1:
            selected_strategy = st.selectbox(
                "选择策略",
                ["RSI", "MA", "Bollinger"],
                index=["RSI", "MA", "Bollinger"].index(backtest_strategy),
                help="RSI: 超买超卖指标 | MA: 移动平均线交叉 | Bollinger: 价格波动通道"
            )
        with col2:
            period = st.slider(
                "回测周期 (天)",
                min_value=30,
                max_value=365,
                value=90,
                help="使用多少天的历史数据进行回测"
            )

        if st.button("🔄 运行回测", type="primary", use_container_width=True):
            with st.spinner("正在运行回测..."):
                backtest_result = run_backtest(symbol, selected_strategy, period)
                st.session_state.backtest = backtest_result

        if "backtest" in st.session_state:
            result = st.session_state.backtest

            if result["success"]:
                # 生成 NLG 洞察分析
                insights = generate_backtest_insights(result)
                colors = insights["color_codes"]

                # 整体评级卡片
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            border-radius:15px;padding:1.5rem;margin-bottom:1.5rem;text-align:center;">
                    <h2 style="margin:0;color:white;">{insights['overall_summary']}</h2>
                </div>
                """, unsafe_allow_html=True)

                # 回测结果卡片（带颜色编码）
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    delta_label = "📈 盈利" if result['total_return'] > 0 else "📉 亏损"
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;text-align:center;
                                border-left:5px solid {colors['return']};box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-size:0.85rem;color:#666;margin-bottom:0.5rem;">总收益率</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{colors['return']};">
                            {result['total_return']:.2f}%
                        </div>
                        <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">{delta_label}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;text-align:center;
                                border-left:5px solid {colors['winrate']};box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-size:0.85rem;color:#666;margin-bottom:0.5rem;">胜率</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{colors['winrate']};">
                            {result['win_rate']:.1f}%
                        </div>
                        <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">赚钱概率</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;text-align:center;
                                border-left:5px solid {colors['sharpe']};box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-size:0.85rem;color:#666;margin-bottom:0.5rem;">夏普比率</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{colors['sharpe']};">
                            {result['sharpe_ratio']:.2f}
                        </div>
                        <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">性价比评分</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:1rem;text-align:center;
                                border-left:5px solid {colors['drawdown']};box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-size:0.85rem;color:#666;margin-bottom:0.5rem;">最大回撤</div>
                        <div style="font-size:1.8rem;font-weight:700;color:{colors['drawdown']};">
                            {result['max_drawdown']:.2f}%
                        </div>
                        <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">史上最大亏损</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:1rem;text-align:center;
                            box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-top:0.5rem;">
                    <div style="font-size:0.85rem;color:#666;">总交易次数</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#333;">{result['total_trades']}</div>
                </div>
                """, unsafe_allow_html=True)

                # NLG 洞察分析
                st.subheader("📊 回测深度分析")

                st.markdown(f"""
                <div style="background:#f8f9fa;border-radius:10px;padding:1.2rem;margin-bottom:1rem;">
                    {insights['return_analysis']}
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#f8f9fa;border-radius:10px;padding:1.2rem;margin-bottom:1rem;">
                    {insights['risk_analysis']}
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div style="background:#f8f9fa;border-radius:10px;padding:1.2rem;">
                        {insights['sharpe_analysis']}
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div style="background:#f8f9fa;border-radius:10px;padding:1.2rem;">
                        {insights['winrate_analysis']}
                    </div>
                    """, unsafe_allow_html=True)

                # 回测图表
                st.subheader("📈 收益曲线图")
                fig = create_backtest_chart(result)
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.error(f"❌ {result['error']}")

    # ==================== 标签页 4: 关于 ====================
    with tab4:
        st.header("ℹ️ 关于 StockMate")

        st.markdown("""
        ### 🎯 项目简介

        **StockMate (股搭子)** 是一个基于多智能体协作的智能股票投资辅助系统。

        ### 🏗️ 技术架构

        - **Agent 框架**: smolagents (Hugging Face)
        - **数据源**: AkShare (A股实时数据)
        - **回测引擎**: VectorBT
        - **数据建模**: Pydantic

        ### 🤖 智能体团队

        1. **Perception Agent** - 感知者，负责数据收集
        2. **Macro Agent** - 宏观分析师，负责新闻情绪分析
        3. **Technical Agent** - 技术分析师，负责技术指标和回测
        4. **Risk Agent** - 风控官，拥有一票否决权
        5. **Decision Agent** - 基金经理，综合决策

        ### 📊 核心功能

        - 📈 实时行情数据获取
        - 📰 新闻情绪分析
        - 🔬 技术指标回测 (RSI, MA, Bollinger)
        - ⚠️ 风险评估与一票否决
        - 🤖 LLM 智能决策支持

        ### ⚠️ 免责声明

        本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。

        ---

        **版本**: v0.1.0 (MVP)
        **开发**: StockMate Team
        """)


if __name__ == "__main__":
    main()
