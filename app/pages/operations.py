import streamlit as st
import pandas as pd
import plotly.express as px
from app.components.header import page_title
from app.services import metrics


ROW_HEIGHT = 400  # єдина константа висоти — всі графіки однакові


def _weighted_margin(subset: pd.DataFrame) -> float:
    """Зважена маржа для підмножини df — потрібна для online/offline окремо."""
    rev = subset['revenue'].sum()
    return subset['profit'].sum() / rev * 100 if rev else 0.0


def render_operations(df: pd.DataFrame) -> None:
    """Операційний аналіз: SLA пріоритетів, сезонність, логістика."""

    page_title(
        icon="gear-fill",
        title="Operations — операційний аналіз",
        caption="Логістика, сезонність та пріоритети замовлень",
    )

    df_clean = df.copy()
    df_clean['item_type']  = df_clean['item_type'].str.title()
    df_clean['month_name'] = df_clean['order_date'].dt.month_name()

    months_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Рахуємо до alert — значення потрібні для перевірки SLA
    prio_delivery = df_clean.groupby('order_priority')['order_processing'].mean()
    crit = prio_delivery.get('C', 0)
    high = prio_delivery.get('H', 0)
    med  = prio_delivery.get('M', 0)
    low  = prio_delivery.get('L', 0)

    # SLA alert: перевіряємо чи розрив між Critical і Low достатній.
    # gap_ratio < 0.15 означає що різниця менше 15% від середнього — система не працює.
    if pd.notna(crit) and pd.notna(low) and crit > 0 and low > 0:
        crit_low_gap = low - crit
        avg_all      = df_clean['order_processing'].mean()
        gap_ratio    = crit_low_gap / avg_all if avg_all else 0

        # Інверсія: нижчий пріоритет обробляється швидше за вищий
        valid         = [x for x in [crit, high, med, low] if pd.notna(x) and x > 0]
        has_inversion = any(valid[i] > valid[i + 1] for i in range(len(valid) - 1))

        if gap_ratio < 0.15 or has_inversion:
            st.error(
                f"🚨 **Система пріоритетів не виконує своєї функції.** "
                f"Critical-замовлення обробляються за **{crit:.1f} дн.**, "
                f"Low — за **{low:.1f} дн.** Різниця лише **{crit_low_gap:.1f} дн.** "
                f"(~{gap_ratio*100:.0f}% від середнього часу {avg_all:.1f} дн.). "
                f"Пріоритет майже не впливає на швидкість — критичні замовлення "
                f"стоять у черзі майже нарівні з низькопріоритетними. "
                f"Потрібен процесний аудит маршрутизації замовлень."
            )
        else:
            st.success(
                f"✅ **Система пріоритетів працює:** Critical ({crit:.1f} дн.) "
                f"обробляється на **{crit_low_gap:.1f} дн.** швидше за Low ({low:.1f} дн.)."
            )

    avg_delivery   = df_clean['order_processing'].mean()
    online_margin  = _weighted_margin(df_clean[df_clean['sales_channel'] == 'online'])
    offline_margin = _weighted_margin(df_clean[df_clean['sales_channel'] == 'offline'])
    total_margin   = metrics.weighted_margin(df_clean)

    kpi_main_1, kpi_main_2, kpi_main_3, kpi_main_4 = st.columns(4)
    with kpi_main_1: st.metric("Сер. доставка",  f"{avg_delivery:.1f} днів")
    with kpi_main_2: st.metric("Маржа Online",   f"{online_margin:.1f}%")
    with kpi_main_3: st.metric("Маржа Offline",  f"{offline_margin:.1f}%")
    with kpi_main_4: st.metric("Заг. маржа",     f"{total_margin:.1f}%")

    st.caption(
        f"ℹ️ Середній час обробки **{avg_delivery:.1f} дн.** — характерно для "
        f"B2B/wholesale-логістики. Для роздрібного e-commerce це було б довго; "
        f"інтерпретуйте з урахуванням бізнес-моделі."
    )

    st.caption("⏱️ Середній час доставки по пріоритету замовлення")
    kpi_prio_C, kpi_prio_H, kpi_prio_M, kpi_prio_L = st.columns(4)
    with kpi_prio_C: st.metric("Critical", f"{prio_delivery.get('C', 0):.1f} днів")
    with kpi_prio_H: st.metric("High",     f"{prio_delivery.get('H', 0):.1f} днів")
    with kpi_prio_M: st.metric("Medium",   f"{prio_delivery.get('M', 0):.1f} днів")
    with kpi_prio_L: st.metric("Low",      f"{prio_delivery.get('L', 0):.1f} днів")

    st.divider()

    chart_heatmap, chart_priority = st.columns([3, 2])

    with chart_heatmap:
        st.subheader("Сезонність продажів по місяцях")

        cat_order = (
            df_clean.groupby('item_type')['units_sold']
            .sum().sort_values(ascending=False).index
        )
        # pivot_table: рядки = категорії, колонки = місяці, значення = units_sold
        # reindex гарантує хронологічний порядок місяців і сортування категорій за обсягом
        heatmap_data = df_clean.pivot_table(
            index='item_type', columns='month_name',
            values='units_sold', aggfunc='sum'
        ).reindex(index=cat_order, columns=months_order)

        fig1 = px.imshow(
            heatmap_data, color_continuous_scale='Blues',
            labels={'x': 'Місяць', 'y': 'Категорія', 'color': 'Продано одиниць'},
            aspect='auto',
        )
        fig1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=30, b=40),
            height=ROW_HEIGHT, xaxis=dict(side='bottom'),
        )
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    with chart_priority:
        # Показуємо час обробки, а не кількість замовлень —
        # операційне питання: "чи швидше обробляються важливі?"
        st.subheader("Час обробки по пріоритетах")
        st.caption("Стовпці майже рівні — пріоритет слабо впливає на швидкість")

        prio_map       = {'C': 'Critical', 'H': 'High', 'M': 'Medium', 'L': 'Low'}
        priority_order = ['Critical', 'High', 'Medium', 'Low']

        prio_time = (
            df_clean.assign(priority_label=df_clean['order_priority'].map(prio_map))
            .groupby('priority_label')['order_processing']
            .mean()
            .reindex(priority_order)
            .reset_index(name='mean_days')
        )

        fig2 = px.bar(
            prio_time, x='priority_label', y='mean_days',
            color='priority_label',
            color_discrete_map={'Critical': '#08306b', 'High': '#2171b5', 'Medium': '#6baed6', 'Low': '#c6dbef'},
            category_orders={'priority_label': priority_order},
            labels={'priority_label': 'Пріоритет', 'mean_days': 'Сер. час обробки (днів)'},
        )
        fig2.update_traces(width=0.55, hovertemplate='<b>%{x}</b><br>Факт: %{y:.1f} дн.<extra></extra>')
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False, margin=dict(l=10, r=10, t=30, b=40), height=ROW_HEIGHT,
            yaxis=dict(range=[0, prio_time['mean_days'].max() * 1.15], gridcolor='rgba(255,255,255,0.05)'),
        )
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    chart_time, chart_volume = st.columns([3, 2])

    monthly_delivery = (
        df_clean.groupby('month_name')['order_processing']
        .mean().reindex(months_order).reset_index()
        .rename(columns={'order_processing': 'mean_days'})
    )

    with chart_time:
        st.subheader("Сезонне навантаження на логістику")
        st.caption("Чи бувають місяці з повільнішою обробкою замовлень?")

        fig3 = px.line(
            monthly_delivery, x='month_name', y='mean_days', markers=True,
            labels={'month_name': 'Місяць', 'mean_days': 'Сер. час обробки (днів)'},
            color_discrete_sequence=['#2171b5'],
        )
        fig3.update_traces(
            line=dict(width=3),
            marker=dict(size=10, line=dict(width=2, color='#08306b')),
            hovertemplate='<b>%{x}</b><br>Сер. час: %{y:.1f} днів<extra></extra>',
        )
        overall_mean_days = monthly_delivery['mean_days'].mean()
        fig3.add_hline(
            y=overall_mean_days, line_dash='dash',
            line_color='rgba(156,163,175,0.5)',
            annotation_text=f'Середнє: {overall_mean_days:.1f} днів',
            annotation_position='top right',
            annotation_font=dict(color='#9ca3af', size=11),
        )
        fig3.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=30, b=40), height=ROW_HEIGHT,
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
            xaxis=dict(tickangle=-35),
        )
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

    monthly_volume = (
        df_clean.groupby('month_name')['units_sold']
        .sum().reindex(months_order).reset_index()
        .rename(columns={'units_sold': 'total_units'})
    )
    monthly_volume['units_K'] = monthly_volume['total_units'] / 1e3

    with chart_volume:
        st.subheader("Обсяг роботи по місяцях")
        st.caption("Скільки одиниць товару склад обробляє щомісяця?")

        fig4 = px.bar(
            monthly_volume, x='month_name', y='units_K',
            color='units_K', color_continuous_scale='Blues',
            labels={'month_name': 'Місяць', 'units_K': 'Одиниць (тис.)'},
        )
        fig4.update_traces(width=0.6, hovertemplate='<b>%{x}</b><br>Обсяг: %{y:.1f} тис. одиниць<extra></extra>')
        fig4.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            coloraxis_showscale=False, margin=dict(l=10, r=10, t=30, b=40), height=ROW_HEIGHT,
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)', range=[0, monthly_volume['units_K'].max() * 1.15]),
            xaxis=dict(tickangle=-35),
        )
        st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    st.subheader("Операційні висновки та аномалії")

    slowest_month = monthly_delivery.set_index('month_name')['mean_days'].idxmax()
    fastest_month = monthly_delivery.set_index('month_name')['mean_days'].idxmin()
    slow_days     = monthly_delivery['mean_days'].max()
    fast_days     = monthly_delivery['mean_days'].min()
    range_days    = slow_days - fast_days
    busiest_month = monthly_volume.set_index('month_name')['total_units'].idxmax()
    busiest_units = monthly_volume['total_units'].max() / 1e3

    if range_days > 3:
        if slowest_month == busiest_month:
            st.warning(
                f"📦 **Подвійне навантаження у {slowest_month}:** склад обробляє "
                f"**{busiest_units:.1f} тис.** одиниць (максимум за рік) і час обробки виростає до "
                f"**{slow_days:.1f} дн.** Великий обсяг = повільніша робота. "
                f"Варто посилювати команду у цей період."
            )
        else:
            slowest_month_units = monthly_volume.set_index('month_name').loc[slowest_month, 'total_units'] / 1e3
            slowest_volume_rank = monthly_volume['total_units'].rank(ascending=False).astype(int)[
                monthly_volume['month_name'] == slowest_month
            ].iloc[0]
            st.info(
                f"📦 **Сезонність логістики:** найповільніший місяць — **{slowest_month}** "
                f"({slow_days:.1f} дн.), найшвидший — **{fastest_month}** ({fast_days:.1f} дн.), "
                f"розкид **{range_days:.1f} дн.** "
                f"Цікаво, що у {slowest_month} обсяг = {slowest_month_units:.1f} тис. одиниць "
                f"({slowest_volume_rank}-й місяць за обсягом з 12). "
                f"Це говорить, що повільність викликана **не лише обсягом** — імовірно, "
                f"відпустки персоналу або інші ресурсні обмеження."
            )

    # Захист від плоских даних: якщо всі місяці однакові — інсайт не має сенсу
    fruits_data = df_clean[df_clean['item_type'] == 'Fruits']
    if not fruits_data.empty:
        fruits_monthly = fruits_data.groupby('month_name')['units_sold'].sum().reindex(months_order)
        if fruits_monthly.nunique() > 1 and fruits_monthly.sum() > 0:
            top_two_months = fruits_monthly.nlargest(2).index.tolist()
            st.info(
                f"🍎 **Fruits** має чітко виражені піки продажів у "
                f"**{top_two_months[0]}** та **{top_two_months[1]}**. "
                f"Рекомендується заздалегідь планувати складські потужності під сезонний попит."
            )
        else:
            st.caption("ℹ️ Немає вираженої сезонності по категорії Fruits для обраних фільтрів.")

    if pd.notna(crit) and pd.notna(med) and crit > 0 and med > 0:
        seq       = {'Critical': crit, 'High': high, 'Medium': med, 'Low': low}
        seq_valid = {k: v for k, v in seq.items() if pd.notna(v) and v > 0}
        keys      = list(seq_valid.keys())
        inversions = [
            f"{keys[i]} ({seq_valid[keys[i]]:.1f} дн.) > {keys[i+1]} ({seq_valid[keys[i+1]]:.1f} дн.)"
            for i in range(len(keys) - 1)
            if seq_valid[keys[i]] > seq_valid[keys[i + 1]]
        ]

        if inversions:
            st.warning(
                "⚠️ **Інверсії у порядку обробки** (нижчий пріоритет обробляється "
                "швидше за вищий): " + "; ".join(inversions) + ". "
                "Це підтверджує, що черга обробки не керується пріоритетом."
            )
        else:
            # Монотонний порядок — але достатність розриву оцінює alert вгорі
            st.info(
                f"ℹ️ Порядок обробки за пріоритетом монотонний "
                f"(Critical {crit:.1f} → Low {low:.1f} дн.), "
                f"але оцініть достатність розриву у alert вгорі сторінки."
            )