import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.components.header import page_title
from app.services.data_loader import load_raw_data, clean_countries


@st.cache_data
def _get_countries_ref() -> pd.DataFrame:
    """Кешований довідник країн — не залежить від фільтрів, читається один раз."""
    _, _, countries_ref = load_raw_data()
    return clean_countries(countries_ref)


def _find_subregion_col(frame: pd.DataFrame) -> str | None:
    """Шукає колонку субрегіону за кількома варіантами назви — захист від різних джерел даних."""
    for c in ['sub_region', 'sub-region', 'subregion', 'subRegion']:
        if c in frame.columns:
            return c
    return None


def render_geography(df: pd.DataFrame) -> None:
    """Географічний аналіз: карта, топ-10 країн, регіони, субрегіони."""

    page_title(
        icon="globe2",
        title="Geography — географічний аналіз",
        caption="Розподіл продажів по країнах та регіонах",
    )

    df_known = df[df['country_name'] != 'unknown']

    country_rev = df_known.groupby('country_name')['revenue'].sum()
    if len(country_rev) > 0:
        top_country     = country_rev.idxmax()
        top_country_rev = country_rev.max()
    else:
        top_country     = "—"
        top_country_rev = 0

    # Europe рахуємо від загального доходу включно з unknown —
    # не можемо приписати unknown до жодного регіону, тому не виключаємо зі знаменника
    total_revenue   = df['revenue'].sum()
    europe_pct      = (df[df['region'] == 'Europe']['revenue'].sum() / total_revenue * 100 if total_revenue else 0.0)
    top_country_pct = (top_country_rev / total_revenue * 100) if total_revenue else 0.0
    unknown_count   = df[df['country_name'] == 'unknown'].shape[0]
    countries_count = df_known['country_name'].nunique()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # % від загального показує що навіть лідер дає малу частку — ринок фрагментований
        st.metric(
            "Країна #1",
            top_country.title() if isinstance(top_country, str) else top_country,
            delta=f"${top_country_rev / 1e6:.1f}M · {top_country_pct:.1f}% від загального",
        )
    with col2:
        st.metric("Частка Europe", f"{europe_pct:.1f}%")
    with col3:
        st.metric("Записів без country_code", unknown_count)
    with col4:
        st.metric("Країн у вибірці", countries_count)

    st.divider()

    st.subheader("Карта доходів по країнах")
    st.caption("Сірі країни — немає продажів у вибірці. Масштаб охоплює всі ринки, включно з Азією.")

    countries_ref = _get_countries_ref()

    map_data = df_known.groupby('country_name')['revenue'].sum().reset_index()
    map_data  = map_data.merge(
        countries_ref[['name', 'alpha_3']],
        left_on='country_name', right_on='name', how='left'
    )
    # Plotly choropleth очікує upper case — в довіднику коди зберігаються lower
    map_data['alpha_3']   = map_data['alpha_3'].str.upper()
    map_data['revenue_M'] = map_data['revenue'] / 1e6

    fig_map = px.choropleth(
        map_data,
        locations='alpha_3', color='revenue_M',
        hover_name='country_name',
        color_continuous_scale='Blues',
        labels={'revenue_M': 'Дохід (млн $)'},
    )
    fig_map.update_traces(
        hovertemplate='<b>%{hovertext}</b><br>Дохід: %{z:.1f} млн $<extra></extra>'
    )
    fig_map.update_geos(
        fitbounds='locations',  # зум на країни з продажами, а не весь світ
        visible=True, showcountries=True,
        countrycolor='rgba(255,255,255,0.15)',
        bgcolor='rgba(0,0,0,0)', showcoastlines=False,
        showland=True, landcolor='rgba(255,255,255,0.02)',
    )
    fig_map.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0), height=500)
    st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Топ-10 країн за доходом")

        # sort ascending + tail(10) — найбільша країна зверху горизонтального бару
        top10 = (
            df_known.groupby('country_name')
            .agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'), orders=('order_id', 'nunique'))
            .reset_index()
            .sort_values('revenue', ascending=True)
            .tail(10)
        )
        top10['margin']        = top10['profit'] / top10['revenue']
        top10['revenue_M']     = top10['revenue'] / 1e6
        top10['revenue_share'] = top10['revenue'] / total_revenue * 100

        fig5 = px.bar(
            top10, x='revenue_M', y='country_name', orientation='h',
            color='margin', color_continuous_scale='Blues',
            labels={'revenue_M': 'Дохід (млн $)', 'country_name': 'Країна', 'margin': 'Маржа'},
            custom_data=['margin', 'revenue_share', 'orders'],
        )
        fig5.update_traces(
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Дохід: %{x:.1f} млн $<br>'
                'Частка: %{customdata[1]:.1f}% від загального<br>'
                'Маржа: %{customdata[0]:.1%}<br>'
                'Замовлень: %{customdata[2]}<extra></extra>'
            ),
        )
        fig5.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            coloraxis_colorbar=dict(tickformat='.0%', title='Маржа'),
        )
        st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})

    with col6:
        st.subheader("Дохід по регіонах")
        st.caption("`unknown` — записи без country_code, які не можна приписати до регіону")

        # unknown показуємо сірим — не ховаємо data gap, а робимо його явним
        regions = (
            df.groupby('region')['revenue'].sum()
            .reset_index().sort_values('revenue', ascending=False)
        )
        regions['revenue_M'] = regions['revenue'] / 1e6

        fig6 = px.pie(
            regions, values='revenue_M', names='region', color='region',
            color_discrete_map={'Europe': '#6baed6', 'Asia': '#2171b5', 'unknown': '#6b7280'},
            hole=0.5,
            labels={'revenue_M': 'Дохід (млн $)'},
        )
        fig6.update_traces(
            textposition='inside', insidetextorientation='auto',
            texttemplate='%{label}<br>%{percent}',
            textfont=dict(color='white', size=14),
            hovertemplate='<b>%{label}</b><br>Дохід: %{value:.2f} млн $<extra></extra>',
        )
        fig6.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False, margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig6, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    st.subheader("Деталізація по субрегіонах")

    sub_col = _find_subregion_col(df)

    # Якщо субрегіон відсутній у df — підтягуємо з довідника через merge
    if sub_col is None:
        sub_ref_col = _find_subregion_col(countries_ref)
        if sub_ref_col is not None and 'country_name' in df.columns:
            df = df.merge(
                countries_ref[['name', sub_ref_col]].rename(
                    columns={'name': 'country_name', sub_ref_col: 'sub_region'}
                ),
                on='country_name', how='left',
            )
            sub_col = 'sub_region'

    if sub_col is not None:
        sub_data = (
            df[df['region'] != 'unknown']
            .dropna(subset=[sub_col])
            .groupby(sub_col)
            .agg(revenue=('revenue', 'sum'), profit=('profit', 'sum'))
            .reset_index()
            .sort_values('revenue', ascending=True)
        )
        if not sub_data.empty:
            sub_data['margin']        = sub_data['profit'] / sub_data['revenue']
            sub_data['revenue_M']     = sub_data['revenue'] / 1e6
            sub_data['revenue_share'] = sub_data['revenue'] / total_revenue * 100

            fig_sub = px.bar(
                sub_data, x='revenue_M', y=sub_col, orientation='h',
                color='margin', color_continuous_scale='Blues',
                labels={'revenue_M': 'Дохід (млн $)', sub_col: 'Субрегіон', 'margin': 'Маржа'},
                custom_data=['margin', 'revenue_share'],
            )
            fig_sub.update_traces(
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Дохід: %{x:.1f} млн $<br>'
                    'Частка: %{customdata[1]:.1f}% від загального<br>'
                    'Маржа: %{customdata[0]:.1%}<extra></extra>'
                ),
            )
            fig_sub.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                coloraxis_colorbar=dict(tickformat='.0%', title='Маржа'),
                yaxis=dict(title=''), height=360,
                margin=dict(t=20, b=40, l=10, r=20),
            )
            st.plotly_chart(fig_sub, use_container_width=True, config={'displayModeBar': False})
            st.caption("Деталі (дохід, частка, маржа) — у підказці при наведенні")

            top_sub = sub_data.iloc[-1]
            st.info(
                f"💡 Провідний субрегіон — **{top_sub[sub_col]}** "
                f"(${top_sub['revenue_M']:.1f}M, {top_sub['revenue_share']:.1f}% "
                f"від загального доходу). Деталізація показує, що залежність "
                f"від Європи концентрується саме тут."
            )
    else:
        st.caption("Поле субрегіону відсутнє в даних — деталізацію пропущено.")

    st.divider()

    if europe_pct >= 80:
        st.warning(f"⚠️ **{europe_pct:.1f}%** доходу з Europe — критична залежність від одного регіону")
    elif europe_pct >= 50:
        st.info(f"💡 Europe дає **{europe_pct:.1f}%** доходу — основний ринок")
    elif europe_pct > 0:
        st.info(f"💡 Europe: {europe_pct:.1f}% від загального доходу")

    if not top10.empty:
        top10_total_share = top10['revenue_share'].sum()
        leader_share      = top10['revenue_share'].max()
        spread            = top10['revenue_M'].max() - top10['revenue_M'].min()
        st.info(
            f"💡 Топ-10 країн дають разом **{top10_total_share:.1f}%** доходу, "
            f"але лідер — лише **{leader_share:.1f}%** (розкид у топ-10 ~${spread:.1f}M). "
            f"Немає домінуючого ринку — дохід **фрагментований** по дрібних країнах. "
            f"Це знижує залежність від однієї країни, але ускладнює масштабування."
        )

    if unknown_count > 0:
        st.info(
            f"💡 **{unknown_count}** записів без `country_code` — показуємо окремо як data gap, "
            f"не приписуємо до жодного регіону"
        )