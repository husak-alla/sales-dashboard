import streamlit as st
from streamlit_option_menu import option_menu

from app.services.data_loader import get_sales_data
from app.components.filters import render_filters, apply_filters
from app.pages.overview import render_overview
from app.pages.product import render_product
from app.pages.geography import render_geography
from app.pages.operations import render_operations
from app.pages.data_dict import render_data_dict


# set_page_config — обов'язково перший виклик Streamlit у файлі
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Глобальний CSS: підключення шрифту, Bootstrap Icons і overrides Streamlit UI.
# Визначається один раз тут — діє на всі 5 сторінок.
st.markdown(
"""<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<style>
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] { justify-content: flex-start; }
.modebar { display: none !important; }
.page-title { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; margin-top: 8px; }
.page-title-icon { color: #6baed6; font-size: 30px; line-height: 1; }
.page-title-text { font-size: 30px; font-weight: 700; color: #ffffff; line-height: 1.2; }
</style>""",
unsafe_allow_html=True,
)

# Завантажуємо дані один раз — get_sales_data() кешована через @st.cache_data
df = get_sales_data()


with st.sidebar:
    st.markdown("""
    <div style='padding: 20px 0 8px 0;'>
        <div style='
            font-family: "Space Grotesk", sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.1;
            letter-spacing: -0.8px;
        '>Sales Analytics</div>
        <div style='
            font-family: "Space Grotesk", sans-serif;
            font-size: 11px;
            color: #6baed6;
            font-weight: 600;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-top: 6px;
        '>Dashboard</div>
        <div style='
            font-size: 12px;
            color: #94a3b8;
            margin-top: 14px;
        '>Аналітика продажів · 2010–2017</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    selected = option_menu(
        menu_title=None,
        options=["Overview", "Product", "Geography", "Operations", "Data Dictionary"],
        icons=["bar-chart-fill", "box-seam-fill", "globe2", "gear-fill", "book-fill"],
        default_index=0,
        styles={
            "container":        {"padding": "0", "background-color": "transparent"},
            "icon":             {"color": "#6baed6", "font-size": "20px"},
            "nav-link": {
                "font-size": "17px", "font-weight": "500", "text-align": "left",
                "margin": "4px 0", "padding": "12px 16px", "border-radius": "10px",
                "color": "#cbd5e1", "--hover-color": "rgba(33, 113, 181, 0.15)",
            },
            "nav-link-selected": {
                "background-color": "rgba(33, 113, 181, 0.25)",
                "color": "#ffffff", "font-weight": "600",
                "border-left": "3px solid #2171b5",
            },
        },
    )

    st.divider()


filters     = render_filters(df)
filtered_df = apply_filters(df, filters)

st.sidebar.divider()
st.sidebar.caption(
    f"📂 Записів: **{len(df):,}** · Після фільтрів: **{len(filtered_df):,}**"
)


# Overview отримує df_full окремо — щоб YoY delta не залежала від фільтрів
pages = {
    "Product":         render_product,
    "Geography":       render_geography,
    "Operations":      render_operations,
    "Data Dictionary": render_data_dict,
}

if filtered_df.empty:
    st.markdown(f"## 📊 {selected}")
    st.warning(
        "⚠️ **Немає даних для відображення.**\n\n"
        "Ви відключили забагато фільтрів (кількість записів після фільтрації: 0).\n "
        "Будь ласка, увімкніть хоча б один параметр або натисніть кнопку "
        "**«🔄 Скинути фільтри»** на панелі ліворуч."
    )
else:
    if selected == "Overview":
        render_overview(filtered_df, df_full=df)
    else:
        pages[selected](filtered_df)