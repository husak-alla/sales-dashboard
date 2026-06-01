import pandas as pd
from app.services.database import query_db


# ── Pandas метрики — динамічні, рахуються на відфільтрованому df ──

def total_revenue(df: pd.DataFrame) -> float:
    return df['revenue'].sum()


def total_profit(df: pd.DataFrame) -> float:
    return df['profit'].sum()


def avg_margin(df: pd.DataFrame) -> float:
    """
    Незважена маржа: кожен рядок впливає однаково незалежно від розміру.
    Для KPI використовуй weighted_margin() — вона точніша.
    """
    return df['margin'].mean() * 100


def weighted_margin(df: pd.DataFrame) -> float:
    """
    Зважена маржа: SUM(profit) / SUM(revenue).
    Великі угоди впливають пропорційно — це реальна маржа бізнесу.
    """
    revenue = df['revenue'].sum()
    if revenue == 0:
        return 0.0
    return df['profit'].sum() / revenue * 100


def orders_count(df: pd.DataFrame) -> int:
    # nunique() а не count() — одне замовлення може мати кілька рядків
    return df['order_id'].nunique()


def avg_order_value(df: pd.DataFrame) -> float:
    return df['revenue'].mean()


def median_order_value(df: pd.DataFrame) -> float:
    return df['revenue'].median()


# ── SQL метрики — статичні агрегації по повному датасету ──

def revenue_by_year() -> pd.DataFrame:
    return query_db("""
        SELECT 
            year,
            sales_channel,
            ROUND(SUM(revenue), 2)                     AS total_revenue,
            ROUND(SUM(profit), 2)                      AS total_profit,
            ROUND(SUM(profit) / SUM(revenue) * 100, 1) AS weighted_margin_pct
        FROM sales
        GROUP BY year, sales_channel
        ORDER BY year, sales_channel
    """)


def revenue_by_product() -> pd.DataFrame:
    return query_db("""
        SELECT
            item_type,
            ROUND(SUM(revenue), 2)                     AS total_revenue,
            ROUND(SUM(profit), 2)                      AS total_profit,
            ROUND(SUM(profit) / SUM(revenue) * 100, 1) AS weighted_margin_pct,
            COUNT(DISTINCT order_id)                   AS orders_count
        FROM sales
        GROUP BY item_type
        ORDER BY total_revenue DESC
    """)


def revenue_by_region() -> pd.DataFrame:
    return query_db("""
        SELECT
            region,
            ROUND(SUM(revenue), 2)                     AS total_revenue,
            ROUND(SUM(profit), 2)                      AS total_profit,
            ROUND(SUM(profit) / SUM(revenue) * 100, 1) AS weighted_margin_pct
        FROM sales
        WHERE region != 'unknown'
        GROUP BY region
        ORDER BY total_revenue DESC
    """)


def top_countries(n: int = 10) -> pd.DataFrame:
    # f-string безпечний — n це int з дефолтом, не user input
    return query_db(f"""
        SELECT
            country_name,
            ROUND(SUM(revenue), 2)                     AS total_revenue,
            ROUND(SUM(profit), 2)                      AS total_profit,
            ROUND(SUM(profit) / SUM(revenue) * 100, 1) AS weighted_margin_pct
        FROM sales
        WHERE country_name != 'unknown'
        GROUP BY country_name
        ORDER BY total_revenue DESC
        LIMIT {n}
    """)


if __name__ == "__main__":
    # Швидка перевірка без запуску Streamlit — python metrics.py
    df = query_db("SELECT * FROM sales")
    print(f"Зважена: {df['profit'].sum() / df['revenue'].sum() * 100:.2f}%")
    print(f"Незважена: {df['margin'].mean() * 100:.2f}%")
    print(f"Рядків: {len(df)}")
    print(f"Унікальних замовлень: {df['order_id'].nunique()}")
    print(f"Позицій на замовлення: {len(df) / df['order_id'].nunique():.1f}")