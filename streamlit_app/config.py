"""
Streamlit 대시보드 설정
"""

# 페이지 설정
PAGE_TITLE = "포트폴리오 대시보드"
PAGE_ICON = "💰"
LAYOUT = "wide"

# 색상 팔레트
COLORS = {
    # 자산 유형별
    'STOCK': '#3498db',  # 파란색
    'BOND': '#2ecc71',   # 초록색
    'CASH': '#f39c12',   # 주황색

    # 증감
    'positive': '#27ae60',  # 녹색
    'negative': '#e74c3c',  # 빨간색
    'neutral': '#95a5a6',   # 회색

    # 기타
    'primary': '#3498db',
    'secondary': '#2ecc71',
    'accent': '#f39c12'
}

# 차트 기본 설정
CHART_DEFAULTS = {
    'height': 400,
    'font_size': 12,
    'line_width': 3,
    'marker_size': 10
}

# 데이터 제한
DATA_LIMITS = {
    'etf_lookthrough_top_n': 10,
    'total_holdings_top_n': 20,
    'sectors_top_n': 10
}

# 캐싱 설정 (초 단위)
CACHE_TTL = {
    'monthly_data': 3600,      # 1시간
    'etf_data': 86400,         # 24시간
    'static_data': 604800      # 7일
}

# 데이터베이스 경로
DB_PATH = "portfolio.db"
