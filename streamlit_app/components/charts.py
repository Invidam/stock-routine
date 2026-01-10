"""
Plotly 차트 컴포넌트
"""
import plotly.graph_objects as go
import pandas as pd
from streamlit_app.config import CHART_DEFAULTS


def create_waterfall_chart(
    categories: list,
    values: list,
    title: str = "Waterfall Chart",
    height: int = CHART_DEFAULTS['height']
) -> go.Figure:
    """
    Waterfall Chart 생성

    Args:
        categories: X축 카테고리 ['전월', '입금', '손익', '금월']
        values: Y축 값 [1320000, 100000, 50000, 1470000]
        title: 차트 제목
        height: 차트 높이

    Returns:
        Plotly Figure 객체
    """
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=categories,
        y=values,
        text=[f"{v:,}원" for v in values],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#27ae60"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}}
    ))

    fig.update_layout(
        title=title,
        showlegend=False,
        height=height,
        xaxis_title="",
        yaxis_title="금액 (원)",
        yaxis_tickformat=",",
        font=dict(size=CHART_DEFAULTS['font_size'])
    )

    return fig


def create_sunburst_chart(
    df: pd.DataFrame,
    title: str = "Sunburst Chart",
    height: int = 600
) -> go.Figure:
    """
    Sunburst Chart 생성 (계층적 데이터)

    Args:
        df: 계층 데이터프레임 (컬럼: labels, parents, values, colors)
        title: 차트 제목
        height: 차트 높이

    Returns:
        Plotly Figure 객체
    """
    fig = go.Figure(go.Sunburst(
        labels=df['labels'],
        parents=df['parents'],
        values=df['values'],
        branchvalues="total",
        marker=dict(
            colors=df['colors'],
            line=dict(color='white', width=2)
        ),
        hovertemplate='<b>%{label}</b><br>' +
                      '금액: %{value:,}원<br>' +
                      '비중: %{percentParent}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        height=height,
        margin=dict(t=50, l=0, r=0, b=0)
    )

    return fig


def create_pie_chart(
    df: pd.DataFrame,
    labels_col: str = 'labels',
    values_col: str = 'values',
    title: str = "Pie Chart",
    height: int = CHART_DEFAULTS['height'],
    colors: list = None
) -> go.Figure:
    """
    Pie Chart 생성

    Args:
        df: 데이터프레임
        labels_col: 레이블 컬럼명
        values_col: 값 컬럼명
        title: 차트 제목
        height: 차트 높이
        colors: 커스텀 색상 리스트

    Returns:
        Plotly Figure 객체
    """
    default_colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6',
                      '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400']

    fig = go.Figure(data=[go.Pie(
        labels=df[labels_col],
        values=df[values_col],
        textinfo='label+percent',
        textposition='inside',
        marker=dict(
            colors=colors or default_colors,
            line=dict(color='white', width=2)
        )
    )])

    fig.update_layout(
        title=title,
        height=height,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
    )

    return fig


def create_horizontal_bar_chart(
    df: pd.DataFrame,
    x_col: str = 'amount',
    y_col: str = 'sector_name',
    title: str = "Horizontal Bar Chart",
    height: int = CHART_DEFAULTS['height'],
    show_values: bool = True
) -> go.Figure:
    """
    Horizontal Bar Chart 생성

    Args:
        df: 데이터프레임
        x_col: X축 컬럼 (금액)
        y_col: Y축 컬럼 (카테고리)
        title: 차트 제목
        height: 차트 높이
        show_values: 값 표시 여부

    Returns:
        Plotly Figure 객체
    """
    # 값 표시 텍스트 생성
    if show_values and 'percent' in df.columns:
        text = [f"{pct:.1f}% ({amt:,}원)"
                for pct, amt in zip(df['percent'], df[x_col])]
    elif show_values:
        text = [f"{amt:,}원" for amt in df[x_col]]
    else:
        text = None

    fig = go.Figure(go.Bar(
        x=df[x_col],
        y=df[y_col],
        orientation='h',
        text=text,
        textposition='outside',
        marker=dict(
            color=df[x_col],
            colorscale='Blues',
            showscale=False
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title="금액 (원)",
        yaxis_title="",
        xaxis_tickformat=",",
        height=height,
        yaxis={'categoryorder': 'total ascending'},
        font=dict(size=CHART_DEFAULTS['font_size'])
    )

    return fig


def create_line_chart(
    df: pd.DataFrame,
    x_col: str = 'month',
    y_col: str = 'value',
    title: str = "Line Chart",
    height: int = CHART_DEFAULTS['height'],
    line_color: str = '#3498db'
) -> go.Figure:
    """
    Line Chart 생성 (시계열 데이터)

    Args:
        df: 데이터프레임
        x_col: X축 컬럼 (날짜/월)
        y_col: Y축 컬럼 (값)
        title: 차트 제목
        height: 차트 높이
        line_color: 라인 색상

    Returns:
        Plotly Figure 객체
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='lines+markers',
        name='총 자산',
        line=dict(color=line_color, width=CHART_DEFAULTS['line_width']),
        marker=dict(size=CHART_DEFAULTS['marker_size'], color=line_color)
    ))

    fig.update_layout(
        title=title,
        xaxis_title="월",
        yaxis_title="금액 (원)",
        yaxis_tickformat=",",
        height=height,
        hovermode='x unified',
        font=dict(size=CHART_DEFAULTS['font_size'])
    )

    return fig
