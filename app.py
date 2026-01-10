"""
포트폴리오 대시보드 메인 앱
"""
import streamlit as st
import streamlit_hotkeys as hotkeys
from streamlit.components.v1 import html

from streamlit_app.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from streamlit_app.data_loader import get_available_months, get_latest_month
from streamlit_app.pages import monthly_comparison, account_portfolio, total_portfolio
from streamlit_app.utils.state import init_session_state


# 페이지 설정
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
init_session_state()

# 페이지 매핑
PAGE_MAP = {
    "monthly": "월별 투자 비교",
    "account": "계좌별 포트폴리오",
    "total": "전체 포트폴리오"
}

# --- 사이드바 ---
with st.sidebar:
    st.title("📊 Navigation")

    # 커스텀 탭 버튼
    for page_key, page_name in PAGE_MAP.items():
        is_active = (st.session_state.current_page == page_name)
        if st.button(page_name, key=f"nav_{page_key}", width='stretch', type="primary" if is_active else "secondary"):
            st.session_state.current_page = page_name
            st.query_params["page"] = page_key
            st.rerun()

    st.divider()

    # 단축키 등록 및 안내
    st.caption("⌨️ 단축키")

    # 단축키 바인딩 정의 (개선된 월 선택 기능 포함)
    hotkey_bindings = [
        hotkeys.hk("page_monthly", "1", prevent_default=True),
        hotkeys.hk("page_account", "2", prevent_default=True),
        hotkeys.hk("page_total", "3", prevent_default=True),
        hotkeys.hk("month_prev", "ArrowLeft", prevent_default=True),
        hotkeys.hk("month_next", "ArrowRight", prevent_default=True),
        hotkeys.hk("month_all", "f", prevent_default=True),
    ]
    # 단축키 컴포넌트 활성화
    hotkeys.activate(hotkey_bindings)

    # 단축키 안내 문구 표시
    st.caption("`1`, `2`, `3`: 페이지 이동")
    st.caption("`←`: 이전 월 선택")
    st.caption("`→`: 다음 월 선택")
    st.caption("`F`: '전체 기간' 선택")

    st.divider()

    st.caption("💰 포트폴리오 대시보드")
    st.caption("v1.6.0") # version up

# --- 단축키 입력 처리 ---
# 페이지 이동 처리
if hotkeys.pressed("page_monthly"):
    st.session_state.current_page = PAGE_MAP["monthly"]
    st.query_params["page"] = "monthly"
    st.rerun()
elif hotkeys.pressed("page_account"):
    st.session_state.current_page = PAGE_MAP["account"]
    st.query_params["page"] = "account"
    st.rerun()
elif hotkeys.pressed("page_total"):
    st.session_state.current_page = PAGE_MAP["total"]
    st.query_params["page"] = "total"
    st.rerun()

# 월 선택 처리
months = get_available_months()
months_with_all = ["전체 기간"] + months

try:
    current_index = months_with_all.index(st.session_state.selected_month)
except ValueError:
    current_index = 0  # 현재 선택된 월을 찾지 못하면 기본값으로 설정

if hotkeys.pressed("month_prev"):
    new_index = max(0, current_index - 1)
    st.session_state.selected_month = months_with_all[new_index]
    st.rerun()
elif hotkeys.pressed("month_next"):
    new_index = min(len(months_with_all) - 1, current_index + 1)
    st.session_state.selected_month = months_with_all[new_index]
    st.rerun()
elif hotkeys.pressed("month_all"):
    st.session_state.selected_month = months_with_all[0]
    st.rerun()

# --- 페이지 렌더링 ---

# URL 쿼리 파라미터로 페이지 상태 동기화
query_params = st.query_params
page_param = query_params.get("page", "monthly")
if page_param in PAGE_MAP:
    st.session_state.current_page = PAGE_MAP.get(page_param, "월별 투자 비교")

# 커스텀 CSS
custom_css = """
<style>
.nav-tab.active {
    color: #ff4b4b;
    border-bottom: 3px solid #ff4b4b;
    font-weight: bold;
}
html { scroll-behavior: smooth; }
</style>
"""
html(custom_css, height=0)


# 메인 헤더
st.title("💰 포트폴리오 대시보드")

# 월 선택 드롭다운
if not months:
    st.error("❌ 데이터베이스에 월별 데이터가 없습니다.")
    st.info("먼저 `import_monthly_data.py`를 실행하여 데이터를 임포트하세요.")
    st.stop()

# 초기 선택 월 설정
if st.session_state.selected_month is None or st.session_state.selected_month not in months_with_all:
    st.session_state.selected_month = months_with_all[0]

# 월 선택
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    selected_month = st.selectbox(
        "📅 분석 월 선택",
        months_with_all,
        index=months_with_all.index(st.session_state.selected_month),
        help="분석할 월을 선택하세요. '전체 기간'을 선택하면 모든 월의 데이터를 통합하여 표시합니다."
    )
    st.session_state.selected_month = selected_month

st.divider()

# 메인 콘텐츠 (페이지별 라우팅)
try:
    if st.session_state.current_page == "월별 투자 비교":
        monthly_comparison.render(selected_month)
    elif st.session_state.current_page == "계좌별 포트폴리오":
        account_portfolio.render(selected_month)
    else:
        total_portfolio.render(selected_month)
except Exception as e:
    st.error(f"❌ 페이지 렌더링 중 오류 발생: {e}")
    st.exception(e)