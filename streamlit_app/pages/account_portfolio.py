"""
계좌별 포트폴리오 페이지
"""
import streamlit as st
from streamlit_app.data_loader import (
    get_accounts,
    get_account_holdings,
    get_account_sectors,
    get_etf_lookthrough
)
from streamlit_app.components.charts import create_pie_chart


def render(selected_month: str):
    """계좌별 포트폴리오 페이지 렌더링"""

    st.header(f"🏦 계좌별 포트폴리오 - {selected_month}")

    # 계좌 목록 조회
    with st.spinner("계좌 데이터 로딩 중..."):
        accounts = get_accounts(selected_month)

    if not accounts:
        st.warning(f"⚠️ {selected_month}에는 계좌 데이터가 없습니다.")
        st.stop()

    # 세션 스테이트 초기화 (expander 상태 유지)
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}

    # 각 계좌별 Expander
    for idx, account in enumerate(accounts):
        header = f"📌 {account['name']} - {account['type']} | {account['broker']} | 총 {account['total_value']:,}원"

        # 세션 스테이트에서 expander 상태 가져오기 (기본값: 첫 번째만 펼침)
        expander_key = f"expander_{account['id']}"
        if expander_key not in st.session_state.expander_states:
            st.session_state.expander_states[expander_key] = (idx == 0)

        with st.expander(header, expanded=st.session_state.expander_states[expander_key]):
            render_account_details(selected_month, account)


def render_account_details(selected_month: str, account: dict):
    """계좌 상세 정보 렌더링"""

    tab1, tab2 = st.tabs(["보유 종목", "ETF 투시 분석"])

    with tab1:
        render_holdings_tab(selected_month, account)

    with tab2:
        render_etf_lookthrough_tab(selected_month, account)


def render_holdings_tab(selected_month: str, account: dict):
    """보유 종목 탭 (실시간 평가액)"""

    df = get_account_holdings(selected_month, account['id'])

    if df.empty:
        st.info("보유 종목이 없습니다.")
        return

    st.subheader("📊 보유 종목 리스트 (실시간 평가액)")

    # 요약 Metrics
    total_invested = df['투자원금'].sum()
    total_value = df['평가금액'].sum()
    total_profit = df['수익금액'].sum()
    return_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 투자 원금", f"{int(total_invested):,}원")
    with col2:
        st.metric("💰 현재 평가액", f"{int(total_value):,}원")
    with col3:
        st.metric("📈 총 수익", f"{int(total_profit):+,}원")
    with col4:
        st.metric("📊 수익률", f"{return_rate:+.1f}%")

    st.divider()

    # 포맷팅 후 표시
    df_display = df.copy()

    # STOCK/BOND와 CASH 구분
    df_stock_bond = df_display[df_display['자산유형'].isin(['STOCK', 'BOND'])].copy()
    df_cash = df_display[df_display['자산유형'] == 'CASH'].copy()

    if not df_stock_bond.empty:
        st.markdown("**💹 주식/채권 종목**")
        df_stock_bond['보유수량'] = df_stock_bond['보유수량'].apply(lambda x: f"{x:.4f}주" if x > 0 else "-")
        df_stock_bond['평균매입가'] = df_stock_bond['평균매입가'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")
        df_stock_bond['투자원금'] = df_stock_bond['투자원금'].apply(lambda x: f"{int(x):,}원")
        df_stock_bond['현재가'] = df_stock_bond['현재가'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")
        df_stock_bond['평가금액'] = df_stock_bond['평가금액'].apply(lambda x: f"{int(x):,}원")
        df_stock_bond['수익금액'] = df_stock_bond['수익금액'].apply(lambda x: f"{int(x):+,}원")
        df_stock_bond['수익률(%)'] = df_stock_bond['수익률(%)'].apply(lambda x: f"{x:+.2f}%")
        df_stock_bond['비중'] = df_stock_bond['ratio'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            df_stock_bond[['종목명', '티커', '보유수량', '평균매입가', '투자원금', '현재가', '평가금액', '수익금액', '수익률(%)', '비중']],
            width='stretch',
            hide_index=True,
            height=400
        )

    if not df_cash.empty:
        st.markdown("**💵 현금성 자산**")
        df_cash['투자원금'] = df_cash['투자원금'].apply(lambda x: f"{int(x):,}원")
        df_cash['평가금액'] = df_cash['평가금액'].apply(lambda x: f"{int(x):,}원")
        df_cash['수익금액'] = df_cash['수익금액'].apply(lambda x: f"{int(x):+,}원")
        df_cash['수익률(%)'] = df_cash['수익률(%)'].apply(lambda x: f"{x:+.2f}%")
        df_cash['비중'] = df_cash['ratio'].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            df_cash[['종목명', '투자원금', '평가금액', '수익금액', '수익률(%)', '비중']],
            use_container_width=True,
            hide_index=True
        )

    st.caption("💡 현재가는 yfinance를 통해 실시간으로 조회됩니다.")
    st.caption("💡 수익률 = (평가금액 - 투자원금) / 투자원금 × 100")

    st.divider()

    # 섹터 비중 차트
    st.subheader("📊 섹터 비중")

    df_sectors = get_account_sectors(selected_month, account['id'])

    if not df_sectors.empty:
        # Pie Chart용 데이터 준비
        chart_df = df_sectors.copy()
        chart_df = chart_df.rename(columns={'sector_name': 'labels', 'amount': 'values'})

        fig = create_pie_chart(
            chart_df,
            labels_col='labels',
            values_col='values',
            title="섹터별 자산 분포"
        )
        st.plotly_chart(fig, use_container_width=True, key=f"sector_pie_{account['id']}")
    else:
        st.info("섹터 데이터가 없습니다.")


def render_etf_lookthrough_tab(selected_month: str, account: dict):
    """ETF 투시 탭"""

    # 투시는 항상 활성화
    # 이전에는 토글로 제어했지만, 사용자 피드백에 따라 항상 활성화로 변경

    with st.spinner("ETF 분석 중..."):
        df = get_etf_lookthrough(selected_month, account['id'], top_n=999)  # 모든 종목 가져오기

    if df.empty:
        st.warning("이 계좌에는 ETF 데이터가 없습니다.")
        return

    st.subheader("🔎 ETF 내부 구성 종목")

    # 종목 통합/분리 토글
    aggregate_holdings = st.toggle(
        "🔀 동일 종목 통합 (출처 ETF별로 분리된 항목을 하나로 통합)",
        value=True,
        key=f"aggregate_etf_{account['id']}",
        help="같은 종목명을 가진 항목들을 하나로 합쳐서 표시합니다"
    )

    # OTHER을 맨 아래로 정렬
    df_sorted = df.copy()
    df_sorted['is_other'] = df_sorted['종목'].apply(lambda x: 1 if 'OTHER' in str(x).upper() else 0)

    if aggregate_holdings:
        # 종목명으로 그룹화하여 통합
        df_aggregated = df_sorted.groupby(['종목', 'is_other']).agg({
            'my_amount': 'sum',
            'ratio': 'sum',
            '출처 ETF': lambda x: ', '.join(sorted(set(x)))
        }).reset_index()
        df_sorted = df_aggregated.sort_values(['is_other', 'my_amount'], ascending=[True, False])
    else:
        # 분리된 상태 유지
        df_sorted = df_sorted.sort_values(['is_other', 'my_amount'], ascending=[True, False])

    df_display = df_sorted.copy()
    df_display['비중(%)'] = df_display['ratio'].apply(lambda x: f"{x:.1f}%")  # 계좌별 비중
    df_display['내 보유 금액'] = df_display['my_amount'].apply(lambda x: f"{int(x):,}원")

    st.dataframe(
        df_display[['종목', '비중(%)', '내 보유 금액', '출처 ETF']],
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.caption("💡 비중(%)은 이 계좌 내에서의 비중입니다.")
    st.caption("💡 OTHER 항목은 가장 아래에 표시됩니다.")
    if aggregate_holdings:
        st.caption("💡 동일 종목이 통합되어 출처 ETF가 여러 개 표시될 수 있습니다.")

    st.divider()

    # ETF 구성 종목 파이 차트 (OTHER 제외, 상위 10개)
    st.subheader("📊 ETF 구성 비중 (Top 10)")

    chart_df = df_sorted[df_sorted['is_other'] == 0].head(10).copy()
    chart_df = chart_df.rename(columns={'종목': 'labels', 'my_amount': 'values'})

    if not chart_df.empty:
        fig = create_pie_chart(
            chart_df,
            labels_col='labels',
            values_col='values',
            title="ETF 내부 종목별 비중 (Top 10)"
        )
        st.plotly_chart(fig, use_container_width=True, key=f"etf_pie_{account['id']}")
    else:
        st.info("차트에 표시할 데이터가 없습니다.")
