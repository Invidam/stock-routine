"""
Streamlit 세션 상태 관리
"""
import streamlit as st


def init_session_state():
    """
    세션 상태 초기화
    """
    # 선택한 월 (기본: 최신 월)
    if 'selected_month' not in st.session_state:
        # 최신 월은 data_loader에서 가져옴
        st.session_state.selected_month = None

    # 선택한 페이지
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "월별 투자 비교"

    # 현재 페이지 (app.py에서 사용)
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "월별 투자 비교"

    # ETF 투시 활성화 상태 (계좌별)
    if 'etf_lookthrough' not in st.session_state:
        st.session_state.etf_lookthrough = {}


def get_selected_month() -> str:
    """현재 선택된 월 반환"""
    return st.session_state.get('selected_month', '2025-12')


def set_selected_month(year_month: str):
    """선택된 월 설정"""
    st.session_state.selected_month = year_month


def get_selected_page() -> str:
    """현재 선택된 페이지 반환"""
    return st.session_state.get('selected_page', "월별 투자 비교")


def set_selected_page(page: str):
    """선택된 페이지 설정"""
    st.session_state.selected_page = page


def is_etf_lookthrough_enabled(account_id: int) -> bool:
    """특정 계좌의 ETF 투시 활성화 여부"""
    return st.session_state.etf_lookthrough.get(account_id, False)


def toggle_etf_lookthrough(account_id: int):
    """ETF 투시 토글"""
    current = is_etf_lookthrough_enabled(account_id)
    st.session_state.etf_lookthrough[account_id] = not current
