"""
월별 투자 비교 페이지
"""
import streamlit as st
import pandas as pd
from streamlit_app.data_loader import (
    get_monthly_summary,
    get_recent_months_data,
    get_available_months,
    get_monthly_holdings_comparison
)
from streamlit_app.components.charts import create_waterfall_chart, create_line_chart
from streamlit_app.utils.formatters import get_previous_month


def render(selected_month: str):
    """월별 투자 비교 페이지 렌더링"""

    st.header(f"📅 월별 투자 비교 - {selected_month}")

    # 데이터 로딩
    with st.spinner("데이터 로딩 중..."):
        try:
            current_data = get_monthly_summary(selected_month)
        except Exception as e:
            st.error(f"❌ 데이터 로딩 실패: {e}")
            st.stop()

        previous_month = get_previous_month(selected_month)
        try:
            previous_data = get_monthly_summary(previous_month)
        except:
            previous_data = None
            st.warning(f"⚠️ 전월({previous_month}) 데이터가 없어 비교가 불가능합니다.")

    # 1. Metric Cards
    col1, col2, col3, col4 = st.columns(4)

    if previous_data:
        delta_value = current_data['total_value'] - previous_data['total_value']
        delta_invested = current_data['total_invested'] - previous_data['total_invested']
        delta_profit = current_data['total_profit'] - previous_data['total_profit']
        delta_rate = current_data['return_rate'] - previous_data['return_rate']
    else:
        delta_value = delta_invested = delta_profit = delta_rate = None

    with col1:
        st.metric(
            "💰 총 자산",
            f"{current_data['total_value']:,}원",
            delta=f"{delta_value:+,}원" if delta_value is not None else None
        )

    with col2:
        st.metric(
            "💵 총 원금",
            f"{current_data['total_invested']:,}원",
            delta=f"{delta_invested:+,}원" if delta_invested is not None else None
        )

    with col3:
        st.metric(
            "📈 총 수익",
            f"{current_data['total_profit']:+,}원",
            delta=f"{delta_profit:+,}원" if delta_profit is not None else None
        )

    with col4:
        st.metric(
            "📊 수익률",
            f"{current_data['return_rate']:+.1f}%",
            delta=f"{delta_rate:+.1f}%" if delta_rate is not None else None
        )

    st.divider()

    # 2. Waterfall Chart
    if previous_data:
        st.subheader("💧 자산 변동 내역")

        prev_value = previous_data['total_value']
        deposit = current_data['total_invested'] - previous_data['total_invested']
        profit = (current_data['total_value'] - current_data['total_invested']) - \
                 (previous_data['total_value'] - previous_data['total_invested'])
        curr_value = current_data['total_value']

        fig = create_waterfall_chart(
            categories=["전월 자산", "추가 입금", "평가 손익", "금월 자산"],
            values=[prev_value, deposit, profit, curr_value],
            title="💧 자산 변동 내역",
            height=500  # 높이 증가
        )
        st.plotly_chart(fig, width='stretch', key="waterfall_chart")

        st.divider()

    # 3. 월별 비교 테이블
    st.subheader("📊 월별 지표 비교")

    df = get_recent_months_data(selected_month, num_months=3)

    # 포맷팅
    df_display = df.copy()
    df_display['총 자산'] = df_display['총 자산'].apply(lambda x: f"{x:,}원")
    df_display['총 원금'] = df_display['총 원금'].apply(lambda x: f"{x:,}원")
    df_display['총 수익'] = df_display['총 수익'].apply(lambda x: f"{x:+,}원")
    df_display['수익률'] = df_display['수익률'].apply(lambda x: f"{x:+.1f}%")

    st.dataframe(df_display, width='stretch', hide_index=True)

    st.divider()

    # 4. 계좌+종목별 투자 내역 비교 (실시간 수익률 포함)
    st.subheader("📋 계좌별 종목 투자 내역 비교 (실시간 수익률)")

    with st.spinner("실시간 가격 조회 및 수익률 계산 중..."):
        holdings_df = get_monthly_holdings_comparison(selected_month)

    if not holdings_df.empty:
        # 탭으로 구분: 투자 내역 / 수익률 분석
        tab1, tab2 = st.tabs(["💰 투자 내역", "📊 수익률 분석"])

        with tab1:
            # 투자 내역 포맷팅
            invest_display = holdings_df[['계좌명', '종목명', '티커', '현재투자금액', '전월투자금액', '증감액', '증감률(%)']].copy()
            invest_display['현재투자금액'] = invest_display['현재투자금액'].apply(lambda x: f"{int(x):,}원")
            invest_display['전월투자금액'] = invest_display['전월투자금액'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")
            invest_display['증감액'] = invest_display['증감액'].apply(lambda x: f"{int(x):+,}원")

            # pd.notna 대신 직접 체크
            def format_change_rate(x):
                if x is None or (isinstance(x, float) and (x != x)):  # None or NaN
                    return "신규"
                return f"{x:+.1f}%"

            invest_display['증감률(%)'] = invest_display['증감률(%)'].apply(format_change_rate)

            st.dataframe(
                invest_display,
                width='stretch',
                hide_index=True,
                height=500
            )

            st.caption("💡 전월투자금액이 '-'인 경우는 전월에 없던 신규 종목입니다.")
            st.caption("💡 증감액은 전월 대비 투자금액 변화를 나타냅니다.")

        with tab2:
            # 수익률 분석 포맷팅
            profit_display = holdings_df[['계좌명', '종목명', '티커', '보유수량', '평균매입가', '현재가', '평가금액', '수익금액', '수익률(%)']].copy()

            # 수익/손실 포맷팅
            def format_profit_with_color(value):
                if value == 0 or value == "-":
                    return "-"
                else:
                    return f"{int(value):+,}원"

            def format_rate_with_color(value):
                if value == 0 or value == "-":
                    return "-"
                else:
                    return f"{value:+.2f}%"

            profit_display['보유수량'] = profit_display['보유수량'].apply(lambda x: f"{x:.4f}" if x > 0 else "-")
            profit_display['평균매입가'] = profit_display['평균매입가'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")
            profit_display['현재가'] = profit_display['현재가'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")
            profit_display['평가금액'] = profit_display['평가금액'].apply(lambda x: f"{int(x):,}원" if x > 0 else "-")

            # 원본 값 저장 후 포맷팅
            profit_display['수익금액'] = holdings_df['수익금액'].apply(format_profit_with_color)
            profit_display['수익률(%)'] = holdings_df['수익률(%)'].apply(format_rate_with_color)

            st.dataframe(
                profit_display,
                width='stretch',
                hide_index=True,
                height=500
            )

            st.caption("💡 현재가는 yfinance를 통해 실시간으로 조회된 가격입니다.")
            st.caption("💡 수익률 = (평가금액 - 총투자금액) / 총투자금액 × 100")
            st.caption("🔴 빨강: 상승 (수익) / 🔵 파랑: 하락 (손실)")
            st.caption("⚠️ 일부 종목은 현재가 조회가 불가능할 수 있습니다 (OTHER, 채권 등).")
    else:
        st.info("종목별 비교 데이터가 없습니다.")

    st.divider()

    # 5. 자산 추이 차트
    all_months = get_available_months()

    if len(all_months) >= 2:
        st.subheader("📈 자산 추이")

        # 모든 월의 데이터 수집
        trend_data = []
        for month in reversed(all_months):  # 오래된 것부터
            summary = get_monthly_summary(month)
            trend_data.append({
                'month': month,
                'value': summary['total_value']
            })

        import pandas as pd
        trend_df = pd.DataFrame(trend_data)

        fig = create_line_chart(
            trend_df,
            x_col='month',
            y_col='value',
            title="📈 월별 총 자산 추이"
        )
        st.plotly_chart(fig, width='stretch', key="asset_trend_chart")
    else:
        st.info("자산 추이 차트는 2개월 이상 데이터가 필요합니다.")
