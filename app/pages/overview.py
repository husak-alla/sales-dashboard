import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.components.header import page_title

# Design tokens — всі кольори в одному місці, легко змінити під будь-який бренд
COLOR_ONLINE     = '#2171b5'
COLOR_OFFLINE    = '#c6dbef'
COLOR_TOTAL      = '#f59e0b'
COLOR_GROWTH_POS = '#10a37f'
COLOR_GROWTH_NEG = '#ef4444'
COLOR_TREND_MA   = '#f59e0b'
COLOR_TREND_RAW  = '#3b82f6'


def _compute_yoy_metrics(df_full: pd.DataFrame) -> dict:
    """
    Рахує YoY метрики на повному датасеті — не на відфільтрованому.
    Так delta стабільна незалежно від того які роки вибрані у фільтрах.
    """
    yearly = (
        df_full.groupby('year')
        .agg(
            revenue=('revenue', 'sum'),
            profit=('profit', 'sum'),
            orders=('order_id', 'nunique') if 'order_id' in df_full.columns else ('revenue', 'count'),
            units=('units_sold', 'sum'),
        )
        .reset_index()
        .sort_values('year')
    )
    yearly['margin'] = yearly['profit'] / yearly['revenue']

    if len(yearly) < 2:
        return {}

    last = yearly.iloc[-1]
    prev = yearly.iloc[-2]

    def _delta(curr, prev):
        if prev == 0 or pd.isna(prev):
            return None
        return (curr - prev) / prev * 100

    peak_year = yearly.loc[yearly['revenue'].idxmax()]
    cumulative_drop_from_peak = (last['revenue'] - peak_year['revenue']) / peak_year['revenue'] * 100

    return {
        'revenue_delta':       _delta(last['revenue'], prev['revenue']),
        'profit_delta':        _delta(last['profit'],  prev['profit']),
        'margin_delta_pp':     (last['margin'] - prev['margin']) * 100,  # п.п., не %
        'last_year':           int(last['year']),
        'prev_year':           int(prev['year']),
        'peak_year':           int(peak_year['year']),
        'cumulative_from_peak': cumulative_drop_from_peak,
        'years_with_decline':  int((yearly['revenue'].pct_change() < 0).sum()),
        'total_years_compared': len(yearly) - 1,
    }


def _render_kpi_with_delta(label: str, value: str, delta: float | None,
                            delta_suffix: str = '%', invert_colors: bool = False) -> str:
    """Повертає HTML для KPI картки з кольоровою стрілкою YoY delta."""
    if delta is None or pd.isna(delta):
        delta_html = ""
    else:
        is_positive = delta > 0
        if invert_colors:
            is_positive = not is_positive
        color = COLOR_GROWTH_POS if is_positive else COLOR_GROWTH_NEG
        arrow = '▲' if delta > 0 else '▼'
        delta_html = (
            f"<div style='font-size:14px; color:{color}; font-weight:500; margin-top:4px;'>"
            f"{arrow} {abs(delta):.1f}{delta_suffix} YoY</div>"
        )

    return f"""
    <div style='padding:8px 0;'>
        <div style='font-size:13px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;'>{label}</div>
        <div style='font-size:32px; color:#f1f5f9; font-weight:600; margin-top:4px;'>{value}</div>
        {delta_html}
    </div>
    """


def _render_alert_banner(metrics: dict) -> None:
    """Показує червоний alert якщо падіння > 10% від піку і більше половини років зі спадом."""
    if not metrics:
        return

    cumulative = metrics.get('cumulative_from_peak', 0)
    declines   = metrics.get('years_with_decline', 0)
    total      = metrics.get('total_years_compared', 1)
    peak_year  = metrics.get('peak_year')
    last_year  = metrics.get('last_year')

    if cumulative < -10 and declines / total >= 0.5:
        st.markdown(
            f"""
            <div style='background:linear-gradient(90deg, rgba(239,68,68,0.15) 0%, rgba(239,68,68,0.05) 100%);
                        border-left:4px solid {COLOR_GROWTH_NEG};
                        padding:14px 18px; border-radius:6px; margin:8px 0 20px 0;'>
                <div style='color:#fca5a5; font-size:14px; font-weight:600; margin-bottom:4px;'>
                    ⚠️ Тренд доходу: спадний
                </div>
                <div style='color:#e2e8f0; font-size:13px; line-height:1.5;'>
                    Зниження на <b>{abs(cumulative):.1f}%</b> від піку {peak_year} → {last_year} року.
                    Падіння у <b>{declines} з {total}</b> річних періодів.
                    Деталі — у блоці YoY Growth нижче.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_overview(df: pd.DataFrame, df_full: pd.DataFrame | None = None) -> None:
    """Головна сторінка: KPI з YoY delta, тренди, динаміка по роках."""

    page_title(
        icon="bar-chart-fill",
        title="Overview — загальна картина",
        caption="Ключові показники та динаміка по роках · фільтри: рік / канал",
    )

    yoy_metrics = _compute_yoy_metrics(df_full if df_full is not None else df)
    _render_alert_banner(yoy_metrics)

    # KPI рядок — зважена маржа, медіана для порівняння з AOV
    revenue_total = df['revenue'].sum()
    profit_total  = df['profit'].sum()
    margin_total  = profit_total / revenue_total if revenue_total else 0
    orders_total  = df['order_id'].nunique() if 'order_id' in df.columns else len(df)
    aov          = revenue_total / orders_total if orders_total else 0
    median_order  = (
        df.groupby('order_id')['revenue'].sum().median()
        if 'order_id' in df.columns else df['revenue'].median()
    )

    kpi_cols = st.columns(6)
    kpi_data = [
        ('Дохід',           f'${revenue_total / 1e6:.1f}M',  yoy_metrics.get('revenue_delta')),
        ('Прибуток',        f'${profit_total / 1e6:.1f}M',   yoy_metrics.get('profit_delta')),
        ('Маржа',           f'{margin_total * 100:.1f}%',     yoy_metrics.get('margin_delta_pp')),
        ('Замовлення',      f'{orders_total:,}',              None),
        ('Сер. угода (AOV)',f'${aov / 1e6:.2f}M',            None),
        ('Медіанна угода',  f'${median_order / 1e6:.2f}M',   None),
    ]
    for col, (label, value, delta) in zip(kpi_cols, kpi_data):
        with col:
            # Маржа в п.п. — математично коректно (зміна з 30% до 33% = +3 п.п., не +10%)
            suffix = 'п.п.' if label == 'Маржа' else '%'
            st.markdown(
                _render_kpi_with_delta(label, value, delta, delta_suffix=suffix),
                unsafe_allow_html=True,
            )

    if orders_total > 0:
        skew_ratio = aov / median_order if median_order else 0
        if skew_ratio > 1.3:
            st.caption(
                f"💡 AOV у **{skew_ratio:.1f}× більший за медіану** — розподіл замовлень "
                f"асиметричний: кілька великих угод тягнуть середнє вгору."
            )

    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Дохід по роках · Online vs Offline")

        rev_by_year = (
            df.groupby(['year', 'sales_channel'])['revenue']
            .sum().reset_index()
        )
        rev_by_year['revenue_M'] = rev_by_year['revenue'] / 1e6

        total_by_year = df.groupby('year')['revenue'].sum().reset_index()
        total_by_year['revenue_M'] = total_by_year['revenue'] / 1e6

        fig1 = px.bar(
            rev_by_year,
            x='year', y='revenue_M',
            color='sales_channel',
            color_discrete_map={'online': COLOR_ONLINE, 'offline': COLOR_OFFLINE},
            barmode='stack',
            labels={'revenue_M': 'Дохід (млн $)', 'year': 'Рік', 'sales_channel': 'Канал'},
        )
        fig1.update_traces(
            hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y:.1f} млн $<extra></extra>'
        )

        # Total-лінія поверх барів — add_trace додає новий шар до існуючого figure
        fig1.add_trace(go.Scatter(
            x=total_by_year['year'],
            y=total_by_year['revenue_M'],
            mode='lines+markers+text',
            name='Total',
            line=dict(color=COLOR_TOTAL, width=2.5),
            marker=dict(size=8, color=COLOR_TOTAL, line=dict(color='#1e293b', width=1.5)),
            text=[f'${v:.0f}M' for v in total_by_year['revenue_M']],
            textposition='top center',
            textfont=dict(color=COLOR_TOTAL, size=11),
            hovertemplate='<b>%{x}</b><br>Total: %{y:.1f} млн $<extra></extra>',
        ))

        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'),
            margin=dict(t=70, b=40, l=40, r=20),
            xaxis=dict(dtick=1),
            height=420,
            hovermode='x unified',
        )
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    with col2:
        st.subheader("Канали продажів")

        channel_stats = (
            df.groupby('sales_channel')
            .agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'))
            .reset_index()
        )

        total_revenue = channel_stats['revenue'].sum()
        if total_revenue > 0:
            channel_stats['margin'] = channel_stats['profit'] / channel_stats['revenue'] * 100
            channel_stats['share']  = channel_stats['revenue'] / total_revenue * 100
        else:
            channel_stats['margin'] = 0.0
            channel_stats['share']  = 0.0

        # Захист від фільтра: канал може бути вимкнений користувачем
        online_data  = channel_stats[channel_stats['sales_channel'] == 'online']
        offline_data = channel_stats[channel_stats['sales_channel'] == 'offline']

        online_summary  = (f"Online {online_data.iloc[0]['share']:.1f}% · маржа {online_data.iloc[0]['margin']:.1f}%"
                           if not online_data.empty else "Online вимкнено у фільтрах")
        offline_summary = (f"Offline {offline_data.iloc[0]['share']:.1f}% · маржа {offline_data.iloc[0]['margin']:.1f}%"
                           if not offline_data.empty else "Offline вимкнено у фільтрах")

        st.markdown(
            f"""
            <div style='background:rgba(148,163,184,0.05); padding:10px 14px;
                        border-radius:6px; margin-bottom:12px; font-size:13px; line-height:1.6;'>
                <div style='color:#94a3b8;'>Стан каналів продажів:</div>
                <div style='color:{COLOR_ONLINE}; font-weight:600;'>{online_summary}</div>
                <div style='color:#cbd5e1; font-weight:600;'>{offline_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not channel_stats.empty:
            fig2 = px.bar(
                channel_stats.sort_values('margin', ascending=True),
                x='margin', y='sales_channel',
                orientation='h',
                color='sales_channel',
                color_discrete_map={'online': COLOR_ONLINE, 'offline': COLOR_OFFLINE},
                text='margin',
                labels={'margin': 'Маржа (%)', 'sales_channel': ''},
            )
            fig2.update_traces(
                texttemplate='%{text:.1f}%', textposition='outside',
                hovertemplate='<b>%{y}</b><br>Маржа: %{x:.2f}%<extra></extra>',
            )
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False, height=240,
                margin=dict(t=10, b=30, l=10, r=40),
                xaxis=dict(showgrid=False, range=[0, max(channel_stats['margin'].max() * 1.25, 10)]),
            )
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    st.subheader("Помісячний тренд доходу")

    if not df.empty:
        monthly = (
            df.groupby('month_year')['revenue']
            .sum().reset_index().sort_values('month_year')
        )
        monthly['revenue_M'] = monthly['revenue'] / 1e6
        # rolling(6) — ковзна середня за 6 місяців, згладжує сезонний шум
        monthly['ma_6m'] = monthly['revenue_M'].rolling(window=6, min_periods=3).mean()

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=monthly['month_year'], y=monthly['revenue_M'],
            mode='lines', name='Місячний дохід',
            line=dict(color=COLOR_TREND_RAW, width=1), opacity=0.4,
            hovertemplate='<b>%{x}</b><br>%{y:.1f} млн $<extra></extra>',
        ))
        # Невидима лінія тільки для fill='tozeroy' — area chart ефект
        fig3.add_trace(go.Scatter(
            x=monthly['month_year'], y=monthly['revenue_M'],
            mode='lines', line=dict(color='rgba(0,0,0,0)'),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
            showlegend=False, hoverinfo='skip',
        ))
        fig3.add_trace(go.Scatter(
            x=monthly['month_year'], y=monthly['ma_6m'],
            mode='lines', name='Тренд (6-міс MA)',
            line=dict(color=COLOR_TREND_MA, width=3),
            hovertemplate='<b>%{x}</b><br>MA: %{y:.1f} млн $<extra></extra>',
        ))

        unique_years = sorted(pd.to_datetime(monthly['month_year']).dt.year.unique().tolist())
        fig3.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            height=380,
            xaxis=dict(
                tickmode='array',
                tickvals=[f"{y}-01" for y in unique_years],
                ticktext=[str(y) for y in unique_years],
                tickangle=0, title='Рік',
            ),
            yaxis=dict(title='Дохід (млн $)', gridcolor='rgba(148,163,184,0.15)'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'),
            margin=dict(t=50, b=40, l=40, r=20),
            hovermode='x unified',
        )
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        st.caption(
            "Тонка лінія — місячні значення, товста помаранчева — 6-місячна ковзна середня. "
            "MA згладжує сезонний шум і показує справжній тренд."
        )

    st.subheader("YoY Growth %")

    yoy_source    = df_full if df_full is not None else df
    visible_years = set(df['year'].unique())

    yoy_all = (
        yoy_source.groupby('year')['revenue']
        .sum().reset_index().sort_values('year')
    )
    yoy_all['revenue_M']    = yoy_all['revenue'] / 1e6
    yoy_all['growth']       = yoy_all['revenue'].pct_change() * 100
    yoy_all['abs_delta_M']  = yoy_all['revenue_M'].diff()

    yoy_visible = yoy_all[yoy_all['year'].isin(visible_years)].sort_values('year')

    years_sorted = sorted(visible_years)
    if years_sorted and years_sorted != list(range(years_sorted[0], years_sorted[-1] + 1)):
        st.caption(
            "⚠️ YoY обчислюється на повному датасеті; "
            "приховані роки в проміжку не впливають на розрахунок."
        )

    worst_year = None
    if not yoy_visible['growth'].dropna().empty:
        worst_year = int(yoy_visible.loc[yoy_visible['growth'].idxmin(), 'year'])

    html = "<div style='display:flex; flex-wrap:wrap; gap:8px; width:100%; margin-top:8px; margin-bottom:16px;'>"
    for _, row in yoy_visible.iterrows():
        year     = int(row['year'])
        is_worst = (year == worst_year)
        border   = (
            f"border:1px solid {COLOR_GROWTH_NEG}; box-shadow:0 0 12px rgba(239,68,68,0.25);"
            if is_worst else
            "border:1px solid rgba(148,163,184,0.15);"
        )

        if pd.isna(row['growth']):
            html += f"""
            <div style='text-align:center; flex:1; min-width:90px; padding:10px 6px;
                        border-radius:6px; {border} background:rgba(148,163,184,0.03);'>
                <div style='font-size:13px; color:#94a3b8;'>{year}</div>
                <div style='font-size:18px; color:#e2e8f0; font-weight:500; margin-top:4px;'>base</div>
                <div style='font-size:11px; color:#64748b; margin-top:2px;'>${row['revenue_M']:.0f}M</div>
            </div>"""
        else:
            color    = COLOR_GROWTH_POS if row['growth'] > 0 else COLOR_GROWTH_NEG
            sign     = '+' if row['growth'] > 0 else ''
            abs_sign = '+' if row['abs_delta_M'] > 0 else ''
            html += f"""
            <div style='text-align:center; flex:1; min-width:90px; padding:10px 6px;
                        border-radius:6px; {border} background:rgba(148,163,184,0.03);'>
                <div style='font-size:13px; color:#94a3b8;'>{year}</div>
                <div style='font-size:18px; color:{color}; font-weight:600; margin-top:4px;'>
                    {sign}{row['growth']:.1f}%
                </div>
                <div style='font-size:11px; color:#64748b; margin-top:2px;'>
                    {abs_sign}${row['abs_delta_M']:.0f}M
                </div>
            </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    if worst_year is not None:
        worst_growth = yoy_visible.loc[yoy_visible['year'] == worst_year, 'growth'].iloc[0]
        st.caption(
            f"🔴 Найгірший рік за динамікою: **{worst_year}** ({worst_growth:+.1f}%). "
            "Рекомендую перейти на сторінки Product / Geography з фільтром по цьому році "
            "для root-cause аналізу."
        )