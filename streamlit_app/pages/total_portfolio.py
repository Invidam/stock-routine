"""
전체 포트폴리오 페이지
"""
import streamlit as st
from streamlit_app.data_loader import (
    get_asset_type_summary,
    get_hierarchical_portfolio_data,
    search_total_holdings,
    get_total_sectors,
    get_total_top_holdings,
    get_total_lookthrough_holdings,
    get_monthly_summary
)
from streamlit_app.components.charts import (
    create_sunburst_chart,
    create_horizontal_bar_chart
)


def render(selected_month: str):
    """전체 포트폴리오 페이지 렌더링"""

    st.header(f"🏆 전체 포트폴리오 - {selected_month}")

    # 1. 투자 정보 요약
    render_investment_summary(selected_month)
    st.divider()

    # 2. 자산 유형별 요약
    render_asset_type_summary(selected_month)
    st.divider()

    # 2. Sunburst Chart
    render_sunburst_chart(selected_month)
    st.divider()

    # 3. 종목 검색
    render_stock_search(selected_month)
    st.divider()

    # 4. 통합 섹터 비중
    render_sector_chart(selected_month)
    st.divider()

    # 5. Top 20 Holdings
    render_top_holdings(selected_month)


def render_investment_summary(selected_month: str):
    """투자 정보 요약"""

    summary = get_monthly_summary(selected_month)

    st.subheader("💼 투자 정보")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💵 투자 원금",
            f"{summary['total_invested']:,}원"
        )

    with col2:
        st.metric(
            "💰 현재 평가액",
            f"{summary['total_value']:,}원"
        )

    with col3:
        st.metric(
            "📈 총 수익",
            f"{summary['total_profit']:+,}원"
        )

    with col4:
        st.metric(
            "📊 수익률",
            f"{summary['return_rate']:+.1f}%"
        )


def render_asset_type_summary(selected_month: str):
    """자산 유형별 요약"""

    summary = get_asset_type_summary(selected_month)
    total = sum(summary.values())

    if total == 0:
        st.warning("데이터가 없습니다.")
        return

    st.subheader("💰 자산 유형별 요약")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📈 주식형",
            f"{summary['STOCK']:,}원",
            delta=f"{summary['STOCK']/total*100:.1f}%"
        )

    with col2:
        st.metric(
            "💵 채권형",
            f"{summary['BOND']:,}원",
            delta=f"{summary['BOND']/total*100:.1f}%"
        )

    with col3:
        st.metric(
            "💰 현금형",
            f"{summary['CASH']:,}원",
            delta=f"{summary['CASH']/total*100:.1f}%"
        )


def render_sunburst_chart(selected_month: str):
    """Sunburst 차트"""

    st.subheader("🌞 자산 구성")

    with st.spinner("차트 생성 중..."):
        df = get_hierarchical_portfolio_data(selected_month)

    if df.empty:
        st.info("데이터가 없습니다.")
        return

    fig = create_sunburst_chart(df, title="🌞 계층적 자산 구성")
    st.plotly_chart(fig, width='stretch')

    st.caption("💡 차트를 클릭하면 세부 항목으로 드릴다운할 수 있습니다.")


def render_stock_search(selected_month: str):
    """종목 검색"""

    st.subheader("🔍 종목 검색")

    search_ticker = st.text_input(
        "종목 코드 입력",
        placeholder="예: AAPL, SPY, 005930.KS",
        help="직접 보유 + ETF 내 간접 보유를 모두 검색합니다"
    )

    if not search_ticker:
        st.info("종목 코드를 입력하면 직접 보유와 ETF를 통한 간접 보유를 모두 확인할 수 있습니다.")
        return

    with st.spinner(f"{search_ticker} 검색 중..."):
        result = search_total_holdings(selected_month, search_ticker.strip().upper())

    if not result:
        st.warning(f"'{search_ticker}' 종목을 찾을 수 없습니다.")
        return

    st.success(f"📊 검색 결과: {result['ticker']} ({result['name']})")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "💼 직접 보유",
            f"{result['direct_value']:,}원",
            help="직접 매수한 금액"
        )

    with col2:
        st.metric(
            "📦 ETF 통해",
            f"{result['etf_value']:,}원",
            help="ETF에 포함되어 간접 보유하는 금액"
        )

    # ETF별 상세 내역
    if result['etf_details']:
        st.caption("ETF별 상세 내역:")
        for etf_name, shares, value in result['etf_details']:
            st.caption(f"  • {etf_name}에서: {value:,}원")

    st.divider()

    # 총계
    st.metric(
        "✅ 총 보유",
        f"{result['total_value']:,}원",
        help="직접 보유 + ETF 통한 간접 보유"
    )


def render_sector_chart(selected_month: str):
    """섹터 차트"""

    st.subheader("📊 통합 섹터 비중")

    df = get_total_sectors(selected_month, top_n=10)

    if df.empty:
        st.info("섹터 데이터가 없습니다.")
        return

    fig = create_horizontal_bar_chart(
        df,
        x_col='amount',
        y_col='sector_name',
        title="📊 통합 섹터 비중 (Top 10)"
    )
    st.plotly_chart(fig, width='stretch', key="sector_bar_chart")


def render_top_holdings(selected_month: str):
    """Top Holdings (직접 보유 / ETF 투시 토글)"""

    lookthrough = st.toggle(
        "🔎 ETF 투시",
        value=False,
        key="top_holdings_lookthrough",
        help="ETF를 구성종목으로 풀어서 보여줍니다"
    )

    if lookthrough:
        st.subheader("🏅 통합 보유 종목 Top 50 (ETF 투시)")

        with st.spinner("ETF 투시 데이터 조회 중..."):
            df = get_total_lookthrough_holdings(selected_month, top_n=50)

        if df.empty:
            st.info("ETF 투시 데이터가 없습니다. 분석을 먼저 실행해주세요.")
            return

        df_display = df.copy()
        df_display.insert(0, '순위', range(1, len(df) + 1))
        df_display['평가금액'] = df_display['평가금액'].apply(lambda x: f"{int(x):,}원")
        df_display['비중(%)'] = df_display['비중(%)'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            df_display[['순위', '종목', '유형', '비중(%)', '평가금액', '출처 ETF']],
            width='stretch',
            hide_index=True,
            height=600
        )

        st.caption("💡 ETF를 구성종목으로 분해하여 실제 보유 종목 비중을 보여줍니다.")
        st.caption("💡 OTHER 항목은 yfinance에서 제공하지 않는 나머지 구성종목입니다.")

    else:
        st.subheader("🏅 통합 보유 종목 Top 20 (현재 평가액 기준)")

        with st.spinner("현재가 조회 중..."):
            df = get_total_top_holdings(selected_month, top_n=20)

        if df.empty:
            st.info("데이터가 없습니다.")
            return

        df_display = df.copy()
        df_display.insert(0, '순위', range(1, len(df) + 1))

        # 수익금액 계산
        df_display['수익금액_raw'] = df_display['평가금액'] - df_display['투자원금']

        df_display['투자원금'] = df_display['투자원금'].apply(lambda x: f"{int(x):,}원")
        df_display['평가금액'] = df_display['평가금액'].apply(lambda x: f"{int(x):,}원")
        df_display['수익금액'] = df_display['수익금액_raw'].apply(lambda x: f"{int(x):+,}원")
        df_display['비중'] = df_display['percent'].apply(lambda x: f"{x:.1f}%")
        df_display['수익률'] = df_display['return_rate'].apply(lambda x: f"{x:+.1f}%")

        st.dataframe(
            df_display[['순위', '종목', '유형', '투자원금', '평가금액', '수익금액', '비중', '수익률']],
            width='stretch',
            hide_index=True
        )

        st.caption("💡 평가금액은 현재 시장가 기준으로 계산됩니다. (실시간 조회)")
