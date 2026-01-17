"""
StockMate 主入口文件
用于命令行运行股票分析
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stockmate.agents import create_stockmate_agent, analyze_stock_pipeline
from stockmate.models import StockAnalysisReport
from stockmate.tools.stock_tools import (
    get_a_share_data,
    get_latest_news,
    run_backtest,
)

# 加载环境变量
load_dotenv()


def print_banner():
    """打印程序横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    StockMate (股搭子)                        ║
║               智能股票投资辅助 Agent 系统                      ║
║                  v0.1.0 - MVP 版本                           ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_report(report: StockAnalysisReport):
    """打印分析报告"""
    print("\n" + "=" * 60)
    print("📊 股票分析报告")
    print("=" * 60)

    print(f"\n🏷️  股票代码: {report.ticker}")
    print(f"⏰ 分析时间: {report.analysis_timestamp}")

    # 决策卡片
    decision_emoji = {
        "Buy": "🟢",
        "Sell": "🔴",
        "Wait": "🟡",
    }
    emoji = decision_emoji.get(report.final_decision, "⚪")
    print(f"\n{emoji} 最终决策: **{report.final_decision}**")

    # 详细指标
    print("\n📈 分析指标:")
    print("-" * 40)
    print(f"  情绪评分:     {report.sentiment_score:.1f} / 100")
    print(f"  技术信号:     {report.technical_signal}")
    print(f"  风控评估:     {report.risk_assessment}")
    print(f"  波动率:       {report.var_value:.2f}%")

    # 回测结果
    if report.backtest_win_rate is not None:
        print(f"\n📊 回测验证:")
        print("-" * 40)
        print(f"  历史胜率:     {report.backtest_win_rate:.1f}%")
        print(f"  历史收益:     {report.backtest_return:.1f}%")

    # 决策依据
    print(f"\n💡 决策依据:")
    print("-" * 40)
    print(f"  {report.reasoning}")

    print("\n" + "=" * 60)


def analyze_with_llm(symbol: str):
    """使用 LLM Agent 进行分析"""
    print(f"\n🔍 正在使用 LLM Agent 分析股票 {symbol}...")
    print("⏳ 请稍候，这可能需要一些时间...\n")

    try:
        from stockmate.agents import create_stockmate_agent, parse_agent_response

        agent = create_stockmate_agent()

        prompt = f"""请分析股票 {symbol}，并按照系统提示词的要求进行分析。

请按以下步骤操作：
1. 使用 get_stock_info("{symbol}") 获取行情数据
2. 使用 get_stock_news("{symbol}") 获取最新新闻
3. 使用 backtest_strategy("{symbol}", "RSI") 进行 RSI 策略回测
4. 综合分析并以 JSON 格式输出 StockAnalysisReport

注意：请务必先调用工具获取实际数据，然后再进行分析。"""

        response = agent.run(prompt)
        report = parse_agent_response(str(response))
        report.ticker = symbol

        return report

    except Exception as e:
        print(f"❌ LLM 分析失败: {str(e)}")
        print("🔄 切换到本地分析模式...\n")
        return analyze_with_pipeline(symbol)


def analyze_with_pipeline(symbol: str):
    """使用本地管道进行分析（不依赖 LLM）"""
    print(f"\n🔍 正在使用本地分析模式分析股票 {symbol}...")
    print("⏳ 请稍候...\n")

    return analyze_stock_pipeline(symbol)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="StockMate - 智能股票投资辅助 Agent 系统"
    )
    parser.add_argument("symbol", nargs="?", help="股票代码，如 600000 或 000001")
    parser.add_argument(
        "--mode",
        choices=["llm", "local", "auto"],
        default="auto",
        help="分析模式：llm(使用大模型)、local(本地分析)、auto(自动选择)",
    )
    parser.add_argument(
        "--data-only", action="store_true", help="仅获取数据，不进行分析"
    )
    parser.add_argument(
        "--news-only", action="store_true", help="仅获取新闻，不进行分析"
    )
    parser.add_argument(
        "--backtest",
        choices=["RSI", "MA", "Bollinger"],
        help="运行回测，指定策略类型",
    )
    parser.add_argument("--batch", help="批量分析，指定股票代码文件（每行一个代码）")

    args = parser.parse_args()

    print_banner()

    # 检查 API 配置
    if args.mode == "llm" or (args.mode == "auto" and os.getenv("OPENAI_API_KEY")):
        has_api = True
    else:
        has_api = False

    # 批量分析模式
    if args.batch:
        if not os.path.exists(args.batch):
            print(f"❌ 文件不存在: {args.batch}")
            return

        with open(args.batch, "r", encoding="utf-8") as f:
            symbols = [line.strip() for line in f if line.strip()]

        print(f"\n📋 批量分析 {len(symbols)} 只股票...\n")

        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 分析 {symbol}...")
            try:
                if has_api and args.mode in ["llm", "auto"]:
                    report = analyze_with_llm(symbol)
                else:
                    report = analyze_with_pipeline(symbol)
                print_report(report)
            except Exception as e:
                print(f"❌ 分析 {symbol} 失败: {str(e)}")

        return

    # 单个股票分析
    if not args.symbol:
        print("\n使用方法:")
        print("  python main.py <股票代码> [选项]")
        print("\n示例:")
        print("  python main.py 600000              # 分析浦发银行")
        print("  python main.py 000001 --mode local # 使用本地模式分析平安银行")
        print("  python main.py 600000 --backtest RSI # 运行 RSI 回测")
        print("  python main.py --batch stocks.txt  # 批量分析")
        print("\n选项:")
        print("  --mode {llm,local,auto}  分析模式")
        print("  --data-only              仅获取数据")
        print("  --news-only              仅获取新闻")
        print("  --backtest {RSI,MA,Bollinger}  运行回测")
        print("  --batch <文件>           批量分析")
        return

    symbol = args.symbol

    # 仅获取数据
    if args.data_only:
        print(f"\n📊 获取股票 {symbol} 数据...")
        data = get_a_share_data(symbol)
        if data["success"]:
            print("\n✅ 数据获取成功:")
            print(f"  当前价格: {data['current_price']} 元")
            print(f"  涨跌幅:   {data['change_pct']}%")
            print(f"  波动率:   {data['statistics']['volatility']}%")
            print(f"  数据范围: {data['date_range']}")
        else:
            print(f"❌ {data['error']}")
        return

    # 仅获取新闻
    if args.news_only:
        print(f"\n📰 获取股票 {symbol} 新闻...")
        news = get_latest_news(symbol)
        if news["success"]:
            print(f"\n✅ 获取到 {news['news_count']} 条新闻:\n")
            for i, item in enumerate(news["news"], 1):
                print(f"{i}. {item['title']}")
                print(f"   时间: {item['publish_time']}")
                print(f"   摘要: {item['content']}\n")
        else:
            print(f"❌ {news['error']}")
        return

    # 运行回测
    if args.backtest:
        print(f"\n📈 运行 {args.backtest} 策略回测...")
        result = run_backtest(symbol, args.backtest)
        if result["success"]:
            print("\n✅ 回测完成:")
            print(f"  策略:     {result['strategy']}")
            print(f"  胜率:     {result['win_rate']}%")
            print(f"  收益率:   {result['total_return']}%")
            print(f"  夏普比率: {result['sharpe_ratio']}")
            print(f"  最大回撤: {result['max_drawdown']}%")
            print(f"  交易次数: {result['total_trades']}")
        else:
            print(f"❌ {result['error']}")
        return

    # 完整分析
    try:
        if has_api and args.mode in ["llm", "auto"]:
            report = analyze_with_llm(symbol)
        else:
            report = analyze_with_pipeline(symbol)

        print_report(report)

    except Exception as e:
        print(f"\n❌ 分析失败: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
