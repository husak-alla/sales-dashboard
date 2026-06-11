import streamlit as st
import pandas as pd


def _filter_summary(selected_count: int, total: int, label_all: str = "всі") -> str:
    """Підпис для заголовка expander: 'всі', '— нічого' або '5/8'."""
    if selected_count == total:
        return label_all
    if selected_count == 0:
        return "— нічого"
    return f"{selected_count}/{total}"


def render_filters(df: pd.DataFrame) -> dict:
    st.sidebar.title("🔍 Фільтри")

    years      = sorted(df['year'].unique())
    channels   = sorted(df['sales_channel'].unique())
    categories = sorted(df['item_type'].unique())
    regions    = sorted(df[df['region'] != 'unknown']['region'].unique())

    for y   in years:      st.session_state.setdefault(f'cb_year_{y}',     True)
    for ch  in channels:   st.session_state.setdefault(f'cb_channel_{ch}', True)
    for cat in categories: st.session_state.setdefault(f'cb_cat_{cat}',    True)
    for r   in regions:    st.session_state.setdefault(f'cb_region_{r}',   True)

    # Зберігаємо стан expander — True = відкритий
    st.session_state.setdefault('exp_years',      False)
    st.session_state.setdefault('exp_channels',   False)
    st.session_state.setdefault('exp_categories', False)
    st.session_state.setdefault('exp_regions',    False)

    def set_all_years(val: bool):
        for y in years:
            st.session_state[f'cb_year_{y}'] = val

    def set_all_categories(val: bool):
        for cat in categories:
            st.session_state[f'cb_cat_{cat}'] = val

    def reset_all_filters():
        set_all_years(True)
        set_all_categories(True)
        for ch in channels: st.session_state[f'cb_channel_{ch}'] = True
        for r  in regions:  st.session_state[f'cb_region_{r}']   = True

    active_years      = [y   for y   in years      if st.session_state[f'cb_year_{y}']]
    active_channels   = [ch  for ch  in channels   if st.session_state[f'cb_channel_{ch}']]
    active_categories = [cat for cat in categories if st.session_state[f'cb_cat_{cat}']]
    active_regions    = [r   for r   in regions    if st.session_state[f'cb_region_{r}']]

    with st.sidebar.expander(
        f"Рік  ·  {_filter_summary(len(active_years), len(years))}",
        expanded=st.session_state['exp_years']
    ):
        # expanded у expander не зберігається автоматично — робимо це вручну
        st.session_state['exp_years'] = True
        col_a, col_b = st.columns(2)
        col_a.button("Усі",   key='btn_years_all',  on_click=set_all_years, args=(True,),  use_container_width=True)
        col_b.button("Жоден", key='btn_years_none', on_click=set_all_years, args=(False,), use_container_width=True)
        for y in years:
            st.checkbox(str(y), key=f'cb_year_{y}')

    with st.sidebar.expander(
        f"Канал  ·  {_filter_summary(len(active_channels), len(channels))}",
        expanded=st.session_state['exp_channels']
    ):
        st.session_state['exp_channels'] = True
        for ch in channels:
            st.checkbox(ch.capitalize(), key=f'cb_channel_{ch}')

    with st.sidebar.expander(
        f"Категорія  ·  {_filter_summary(len(active_categories), len(categories))}",
        expanded=st.session_state['exp_categories']
    ):
        st.session_state['exp_channels'] = True
        col_a, col_b = st.columns(2)
        col_a.button("Усі",   key='btn_cats_all',  on_click=set_all_categories, args=(True,),  use_container_width=True)
        col_b.button("Жоден", key='btn_cats_none', on_click=set_all_categories, args=(False,), use_container_width=True)
        for cat in categories:
            st.checkbox(cat.capitalize(), key=f'cb_cat_{cat}')

    with st.sidebar.expander(
        f"Регіон  ·  {_filter_summary(len(active_regions), len(regions))}",
        expanded=st.session_state['exp_regions']
    ):
        st.session_state['exp_regions'] = True
        for r in regions:
            st.checkbox(r, key=f'cb_region_{r}')

    st.sidebar.divider()
    st.sidebar.button("🔄 Скинути фільтри", on_click=reset_all_filters, use_container_width=True)

    return {
        'years':      [y   for y   in years      if st.session_state[f'cb_year_{y}']],
        'channels':   [ch  for ch  in channels   if st.session_state[f'cb_channel_{ch}']],
        'categories': [cat for cat in categories if st.session_state[f'cb_cat_{cat}']],
        'regions':    [r   for r   in regions    if st.session_state[f'cb_region_{r}']],
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    mask = (
        df['year'].isin(filters['years'])                                      &
        df['sales_channel'].isin(filters['channels'])                          &
        df['item_type'].isin(filters['categories'])                            &
        (df['region'].isin(filters['regions']) | (df['region'] == 'unknown'))
    )
    return df[mask].copy()
