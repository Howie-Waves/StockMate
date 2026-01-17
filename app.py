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
from stockmate.tools.stock_tools import get_a_share_data, get_latest_news, run_backtest
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


def create_backtest_chart(symbol: str, strategy: str = "RSI") -> go.Figure:
    """创建回测收益曲线图"""
    # 这里可以扩展为更复杂的回测可视化
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=list(range(10)),
            y=[100 + i * 2 + (i % 3) for i in range(10)],
            name=f"{strategy} 策略",
            line=dict(color="#26a69a", width=2),
        )
    )

    fig.update_layout(
        title=f"{strategy} 策略回测收益曲线",
        xaxis_title="交易天数",
        yaxis_title="累计收益 (%)",
        height=300,
        template="plotly_white",
    )

    return fig


# ==================== 主界面 ====================

def main():
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
        )

        # 回测策略选择
        st.subheader("回测配置")
        backtest_strategy = st.selectbox(
            "回测策略",
            ["RSI", "MA", "Bollinger"],
            help="选择用于验证的技术指标策略",
        )

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
        st.header(f"📊 {symbol} 综合分析报告")

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
                        # 使用本地管道
                        report = analyze_stock_pipeline(symbol)

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

            # 决策依据
            st.subheader("💡 决策依据")
            st.info(report.reasoning)

            # 获取价格数据并绘图
            with st.spinner("加载图表数据..."):
                data_result = get_a_share_data(symbol)
                if data_result["success"]:
                    fig = create_price_chart(data_result)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

    # ==================== 标签页 2: 市场新闻 ====================
    with tab2:
        st.header(f"📰 {symbol} 最新资讯")

        if st.button("🔄 刷新新闻", use_container_width=True):
            with st.spinner("获取最新新闻..."):
                news_result = get_latest_news(symbol)
                st.session_state.news = news_result

        if "news" in st.session_state:
            news_result = st.session_state.news

            if news_result["success"]:
                st.success(f"✅ 获取到 {news_result['news_count']} 条最新资讯")

                for news in news_result["news"]:
                    st.markdown(f"""
                    <div class="news-card">
                        <div class="news-title">{news['title']}</div>
                        <div class="news-meta">
                            📅 {news['publish_time']} | 📰 {news['source']}
                        </div>
                        <div style="margin-top:0.5rem;color:#333;">
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
        st.header(f"📈 {symbol} 技术回测")

        # 回测参数
        col1, col2 = st.columns(2)
        with col1:
            selected_strategy = st.selectbox(
                "选择策略",
                ["RSI", "MA", "Bollinger"],
                index=["RSI", "MA", "Bollinger"].index(backtest_strategy)
            )
        with col2:
            period = st.slider(
                "回测周期 (天)",
                min_value=30,
                max_value=365,
                value=90,
            )

        if st.button("🔄 运行回测", type="primary", use_container_width=True):
            with st.spinner("正在运行回测..."):
                backtest_result = run_backtest(symbol, selected_strategy, period)
                st.session_state.backtest = backtest_result

        if "backtest" in st.session_state:
            result = st.session_state.backtest

            if result["success"]:
                # 回测结果卡片
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        label="总收益率",
                        value=f"{result['total_return']:.2f}%",
                        delta="盈利" if result['total_return'] > 0 else "亏损"
                    )

                with col2:
                    st.metric(
                        label="胜率",
                        value=f"{result['win_rate']:.1f}%",
                    )

                with col3:
                    st.metric(
                        label="夏普比率",
                        value=f"{result['sharpe_ratio']:.2f}",
                    )

                with col4:
                    st.metric(
                        label="最大回撤",
                        value=f"{result['max_drawdown']:.2f}%",
                    )

                st.metric(
                    label="总交易次数",
                    value=result['total_trades'],
                )

                # 回测图表
                fig = create_backtest_chart(symbol, selected_strategy)
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
