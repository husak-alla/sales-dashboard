import streamlit as st


def page_title(icon: str, title: str, caption: str | None = None) -> None:
    """
    Рендерить стилізований заголовок сторінки з Bootstrap-іконкою.

    CSS класи визначені глобально в main.py.
    icon — назва без префікса 'bi-', наприклад 'bar-chart-fill'
    """
    html = (
        f'<div class="page-title">'
        f'<i class="bi bi-{icon} page-title-icon"></i>'
        f'<div class="page-title-text">{title}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    if caption:
        st.caption(caption)