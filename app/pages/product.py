import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.components.header import page_title


def render_product(df: pd.DataFrame) -> None:
    """Аналіз товарних категорій: маржинальність, дохід, Парето."""

    st.markdown("""
    <style>
    [data-testid="stMetricDelta"] svg { display: none; }
    [data-testid="stMetricDelta"] { justify-content: flex-start; }
    </style>
    """, unsafe_allow_html=True)

    page_title(
        icon="box-seam-fill",
        title="Product — аналіз продукції",
        caption="Маржинальність, дохід та структура прибутку по категоріях",
    )

    # Зважена маржа: SUM(profit)/SUM(revenue) — а не AVG(margin).
    # AVG дав би однакову вагу дрібному і великому замовленню.
    prod_stats = (
        df.groupby('item_type')
        .agg(
            revenue=('revenue', 'sum'),
            profit=('profit', 'sum'),
            orders=('order_id', 'nunique'),
            units=('units_sold', 'sum'),
        )
        .reset_index()
    )
    prod_stats['margin']          = prod_stats['profit'] / prod_stats['revenue']
    prod_stats['avg_order_value'] = prod_stats['revenue'] / prod_stats['orders']
    prod_stats['revenue_share']   = prod_stats['revenue'] / prod_stats['revenue'].sum() * 100
    prod_stats['profit_share']    = prod_stats['profit']  / prod_stats['profit'].sum()  * 100

    total_revenue   = prod_stats['revenue'].sum()
    total_profit    = prod_stats['profit'].sum()
    weighted_margin = total_profit / total_revenue

    top_revenue_row = prod_stats.loc[prod_stats['revenue'].idxmax()]
    top_profit_row  = prod_stats.loc[prod_stats['profit'].idxmax()]
    top_margin_row  = prod_stats.loc[prod_stats['margin'].idxmax()]
    low_margin_row  = prod_stats.loc[prod_stats['margin'].idxmin()]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "ТОП ЗА ДОХОДОМ",
            top_revenue_row['item_type'].title(),
            delta=f"${top_revenue_row['revenue'] / 1e6:.1f}M · {top_revenue_row['revenue_share']:.1f}% від загального",
        )
    with col2:
        st.metric(
            "ТОП ЗА ПРИБУТКОМ",
            top_profit_row['item_type'].title(),
            delta=f"${top_profit_row['profit'] / 1e6:.1f}M · {top_profit_row['profit_share']:.1f}% від загального",
        )
    with col3:
        st.metric(
            "ТОП ЗА МАРЖЕЮ",
            top_margin_row['item_type'].title(),
            delta=f"{top_margin_row['margin'] * 100:.1f}%",
        )
    with col4:
        # delta_color="inverse" — червоний для низького значення (семантично правильно)
        st.metric(
            "НАЙНИЖЧА МАРЖА",
            low_margin_row['item_type'].title(),
            delta=f"{low_margin_row['margin'] * 100:.1f}%",
            delta_color="inverse",
        )

    st.caption(
        f"Загальна зважена маржа портфеля: **{weighted_margin * 100:.1f}%** · "
        f"розкид між категоріями: {low_margin_row['margin'] * 100:.1f}% — "
        f"{top_margin_row['margin'] * 100:.1f}% "
        f"(різниця {(top_margin_row['margin'] - low_margin_row['margin']) * 100:.1f} п.п.)"
    )

    st.divider()

    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Дохід по категоріях · колір = маржа")

        prod_sorted = prod_stats.sort_values('revenue', ascending=True)
        prod_sorted['revenue_M'] = prod_sorted['revenue'] / 1e6

        fig1 = px.bar(
            prod_sorted,
            x='revenue_M', y='item_type',
            orientation='h',
            color='margin',
            color_continuous_scale='Blues',
            text='revenue_share',
            labels={'revenue_M': 'Дохід (млн $)', 'item_type': 'Категорія', 'margin': 'Маржа'},
            custom_data=['margin', 'profit', 'revenue_share'],
        )
        fig1.update_traces(
            texttemplate='%{text:.1f}%',
            textposition='outside',
            textfont=dict(size=10, color='#cbd5e1'),
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Дохід: %{x:.1f} млн $<br>'
                'Частка: %{customdata[2]:.1f}%<br>'
                'Маржа: %{customdata[0]:.1%}<br>'
                'Прибуток: %{customdata[1]:$,.0f}<extra></extra>'
            ),
        )
        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            coloraxis_colorbar=dict(tickformat='.0%', title='Маржа', thickness=12, len=0.7),
            xaxis=dict(
                gridcolor='rgba(148,163,184,0.1)',
                range=[0, prod_sorted['revenue_M'].max() * 1.18],  # місце для підписів %
            ),
            yaxis=dict(title=''),
            margin=dict(t=30, b=40, l=10, r=20),
            height=440,
        )
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        st.caption("Підпис справа від бару = % від загального доходу")

    with col6:
        st.subheader("Revenue vs Margin · розмір = кількість замовлень")

        # Підписуємо лише категорії з доходом >= медіани —
        # дрібні злипаються в нечитабельний кластер, їх назви доступні в hover
        revenue_threshold = prod_stats['revenue'].median()
        prod_stats['scatter_label'] = prod_stats.apply(
            lambda r: r['item_type'] if r['revenue'] >= revenue_threshold else '',
            axis=1,
        )

        fig2 = px.scatter(
            prod_stats,
            x='revenue', y='margin',
            size='orders', text='scatter_label',
            color='profit', color_continuous_scale='Blues',
            labels={'revenue': 'Дохід ($)', 'margin': 'Маржа', 'profit': 'Прибуток ($)', 'orders': 'Замовлення'},
            size_max=40,
            custom_data=['item_type', 'orders', 'profit'],
        )
        fig2.update_traces(
            textposition='top center', textfont_size=10,
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>'
                'Дохід: %{x:$,.0f}<br>'
                'Маржа: %{y:.1%}<br>'
                'Замовлень: %{customdata[1]}<br>'
                'Прибуток: %{customdata[2]:$,.0f}<extra></extra>'
            ),
        )
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False, yaxis=dict(tickformat='.0%'),
        )
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        st.caption("Підписані лише великі категорії · решта — у підказці при наведенні")

    col7, col8 = st.columns(2)
    with col7:
        st.info(
            f"💡 **{top_margin_row['item_type'].title()}** — найвища маржа "
            f"**{top_margin_row['margin'] * 100:.1f}%**, але це лише "
            f"**{top_margin_row['revenue_share']:.1f}%** загального доходу "
            f"(${top_margin_row['revenue']/1e6:.1f}M). "
            f"Можливість для зростання — масштабувати продажі."
        )
    with col8:
        st.warning(
            f"⚠️ **{low_margin_row['item_type'].title()}** — маржа лише "
            f"**{low_margin_row['margin'] * 100:.1f}%** при доході "
            f"${low_margin_row['revenue']/1e6:.1f}M "
            f"({low_margin_row['revenue_share']:.1f}% від загального). "
            f"Перегляд ціноутворення або собівартості може суттєво вплинути на прибуток."
        )

    st.divider()

    st.subheader("Парето аналіз — які категорії дають 80% прибутку?")

    pareto = prod_stats.sort_values('profit', ascending=False).reset_index(drop=True)
    pareto['rank']            = pareto.index + 1
    pareto['profit_cumsum']   = pareto['profit'].cumsum()
    pareto['profit_pct']      = pareto['profit'] / pareto['profit'].sum() * 100
    pareto['profit_cum_pct']  = pareto['profit_cumsum'] / pareto['profit'].sum() * 100

    # Знаходимо перший рядок де накопичений % перетинає 80%
    above_80_idx = pareto[pareto['profit_cum_pct'] >= 80].index
    top_cats     = pareto.loc[:above_80_idx[0], 'item_type'].tolist() if len(above_80_idx) > 0 else pareto['item_type'].tolist()
    pareto['in_top_80'] = pareto['item_type'].isin(top_cats)
    total_cats = len(pareto)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=pareto['item_type'],
        y=pareto['profit_pct'],
        marker=dict(color=['#2171b5' if x else '#6b7280' for x in pareto['in_top_80']]),
        text=[f"{v:.1f}%" for v in pareto['profit_pct']],
        textposition='outside', textfont=dict(size=11),
        name='% від прибутку', yaxis='y',
        customdata=list(zip(pareto['rank'], pareto['profit_cum_pct'], pareto['profit'] / 1e6)),
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Ранг: %{customdata[0]} з ' + str(total_cats) + '<br>'
            'Частка: %{y:.1f}%<br>'
            'Накопичено: %{customdata[1]:.1f}%<br>'
            'Прибуток: $%{customdata[2]:.1f}M<extra></extra>'
        ),
    ))
    fig3.add_trace(go.Scatter(
        x=pareto['item_type'], y=pareto['profit_cum_pct'],
        mode='lines+markers',
        line=dict(color='#f59e0b', width=2.5),
        marker=dict(size=8, color='#f59e0b'),
        name='Накопичений %', yaxis='y2',
        hovertemplate='<b>%{x}</b><br>Накопичено: %{y:.1f}%<extra></extra>',
    ))
    # Пунктир 80% — прив'язаний до правої осі (yref='y2')
    fig3.add_hline(y=80, line_dash='dash', line_color='rgba(245,158,11,0.5)', line_width=1.5, yref='y2')

    fig3.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(title='% від загального прибутку', showgrid=True, gridcolor='rgba(255,255,255,0.05)', ticksuffix='%'),
        # yaxis2 накладається на ту саму область — дві шкали на одному графіку
        yaxis2=dict(title='Накопичений %', overlaying='y', side='right', range=[0, 110],
                    ticksuffix='%', showgrid=False, tickvals=[0, 20, 40, 60, 80, 100]),
        xaxis=dict(title='Категорія'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified',
        margin=dict(t=60, b=40, l=40, r=60),
    )
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

    bottom_cats         = [c.title() for c in pareto[~pareto['in_top_80']]['item_type'].tolist()]
    bottom_profit_share = pareto[~pareto['in_top_80']]['profit_pct'].sum()

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.success(
            f"✅ **{len(top_cats)} з {total_cats} категорій** ({len(top_cats)/total_cats:.0%}) "
            f"дають 80% прибутку: {', '.join(c.title() for c in top_cats)}. "
            f"Це core-портфель — потребує максимальної уваги."
        )
    with col_p2:
        if bottom_cats:
            st.markdown(
                f"""
                <div style='background:rgba(148,163,184,0.05);
                            border-left:3px solid #94a3b8;
                            border-radius:0;
                            padding:12px 14px; font-size:14px; color:#cbd5e1;'>
                    <b style='color:#e2e8f0;'>📉 "Довгий хвіст":</b> {len(bottom_cats)} категорій
                    ({', '.join(bottom_cats)}) дають разом лише
                    <b>{bottom_profit_share:.1f}%</b> прибутку.
                    Розглянути: оптимізація асортименту або фокус на найперспективніших.
                </div>
                """,
                unsafe_allow_html=True,
            )