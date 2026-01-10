"""
월별 투자 비교 페이지 (재설계)
- 두 달 선택 후 YAML 데이터 기반 변경사항 비교
"""
import streamlit as st
import pandas as pd
from streamlit_app.data_loader import (
    get_yaml_available_months,
    compare_months_yaml,
    load_yaml_data
)


def render(selected_month: str):
    """월별 투자 비교 페이지 렌더링"""

    st.header("📊 월별 투자 비교")

    # 사용 가능한 월 목록
    available_months = get_yaml_available_months()

    if len(available_months) < 2:
        st.warning("비교하려면 최소 2개월 이상의 데이터가 필요합니다.")
        if len(available_months) == 1:
            st.info(f"현재 {available_months[0]} 데이터만 있습니다.")
        return

    # 두 달 선택
    col1, col2 = st.columns(2)

    with col1:
        prev_month = st.selectbox(
            "A. 이전 월 선택",
            options=available_months,
            index=1 if len(available_months) > 1 else 0,
            key="prev_month_select"
        )

    with col2:
        curr_month = st.selectbox(
            "B. 현재 월 선택",
            options=available_months,
            index=0,
            key="curr_month_select"
        )

    # 같은 월 선택 시 경고
    if prev_month == curr_month:
        st.warning("다른 월을 선택해주세요.")
        return

    # 순서 체크 (이전 월이 현재 월보다 나중이면 스왑)
    if prev_month > curr_month:
        prev_month, curr_month = curr_month, prev_month
        st.info(f"비교 순서: {prev_month} → {curr_month}")

    st.divider()

    # 비교 실행
    comparison = compare_months_yaml(prev_month, curr_month)

    # 1. 요약 정보
    render_summary(comparison)
    st.divider()

    # 2. 추가된 종목
    render_added(comparison)

    # 3. 삭제된 종목
    render_removed(comparison)

    # 4. 변경된 종목
    render_changed(comparison)


def render_summary(comparison: dict):
    """요약 정보 표시"""

    summary = comparison['summary']
    prev_month = comparison['prev_month']
    curr_month = comparison['curr_month']

    st.subheader("📈 투자 요약")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            f"💰 {prev_month} 총액",
            f"{summary['prev_total']:,}원"
        )

    with col2:
        st.metric(
            f"💰 {curr_month} 총액",
            f"{summary['curr_total']:,}원"
        )

    with col3:
        diff = summary['curr_total'] - summary['prev_total']
        st.metric(
            "📊 변화",
            f"{diff:+,}원",
            delta=f"{diff/summary['prev_total']*100:+.1f}%" if summary['prev_total'] > 0 else None
        )

    # 상세 변화
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "➕ 추가",
            f"{summary['added_total']:,}원",
            delta=f"{len(comparison['added'])}건"
        )

    with col2:
        st.metric(
            "➖ 삭제",
            f"{summary['removed_total']:,}원",
            delta=f"{len(comparison['removed'])}건",
            delta_color="inverse"
        )

    with col3:
        st.metric(
            "🔄 변경",
            f"{summary['changed_total']:+,}원",
            delta=f"{len(comparison['changed'])}건"
        )


def render_added(comparison: dict):
    """추가된 종목 표시"""

    added = comparison['added']

    st.subheader(f"➕ 추가된 종목 ({len(added)}건)")

    if not added:
        st.info("추가된 종목이 없습니다.")
        return

    df = pd.DataFrame(added)
    df['금액'] = df['금액'].apply(lambda x: f"{x:,}원")

    st.dataframe(
        df[['계좌', '종목', '티커', '유형', '금액']],
        width='stretch',
        hide_index=True
    )

    st.divider()


def render_removed(comparison: dict):
    """삭제된 종목 표시"""

    removed = comparison['removed']

    st.subheader(f"➖ 삭제된 종목 ({len(removed)}건)")

    if not removed:
        st.info("삭제된 종목이 없습니다.")
        return

    df = pd.DataFrame(removed)
    df['금액'] = df['금액'].apply(lambda x: f"{x:,}원")

    st.dataframe(
        df[['계좌', '종목', '티커', '유형', '금액']],
        width='stretch',
        hide_index=True
    )

    st.divider()


def render_changed(comparison: dict):
    """변경된 종목 표시"""

    changed = comparison['changed']

    st.subheader(f"🔄 금액 변경 ({len(changed)}건)")

    if not changed:
        st.info("금액이 변경된 종목이 없습니다.")
        return

    df = pd.DataFrame(changed)
    df['이전금액'] = df['이전금액'].apply(lambda x: f"{x:,}원")
    df['현재금액'] = df['현재금액'].apply(lambda x: f"{x:,}원")
    df['변화'] = df['변화'].apply(lambda x: f"{x:+,}원")

    st.dataframe(
        df[['계좌', '종목', '티커', '유형', '이전금액', '현재금액', '변화']],
        width='stretch',
        hide_index=True
    )
