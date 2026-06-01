import pandas as pd
from pathlib import Path
import streamlit as st

# Відносний шлях — працює на будь-якій машині незалежно від розташування проєкту
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"


def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Extract-шар ETL: зчитує три незмінних CSV без трансформацій."""
    events    = pd.read_csv(DATA_DIR / "events.csv")
    products  = pd.read_csv(DATA_DIR / "products.csv")
    countries = pd.read_csv(DATA_DIR / "countries.csv")
    return events, products, countries


def clean_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Нормалізує довідник країн: snake_case, регістр, edge cases."""
    df = df.copy()

    df.columns = [
        col.lower().replace('-', '_').replace(' ', '_')
        for col in df.columns
    ]

    text_cols = df.select_dtypes(include='object').columns
    df[text_cols] = df[text_cols].apply(lambda x: x.str.strip())

    cols_to_lower = ['alpha_2', 'alpha_3']
    df[cols_to_lower] = df[cols_to_lower].apply(lambda x: x.str.lower())

    df['region']     = df['region'].str.title()
    df['sub_region'] = df['sub_region'].str.title()

    # ISO код Намібії — буквально рядок 'NA', pandas читає як NaN.
    # Без цього рядка Намібія зникає з географічного аналізу.
    df.loc[df['name'] == 'Namibia', 'alpha_2'] = 'NA'

    # Антарктида відсутня в ISO 3166 — заповнюємо явно щоб уникнути NaN після merge
    df.loc[df['name'] == 'Antarctica', ['region', 'sub_region']] = 'Antarctica'

    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """Нормалізує категорії товарів — критично для коректного groupby."""
    df = df.copy()

    # lowercase + strip: без цього 'Cosmetics' і 'cosmetics' — різні групи
    df['item_type'] = df['item_type'].str.lower().str.strip()

    return df


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    """Очищує основну таблицю транзакцій: схема → типи → пропуски."""
    df = df.copy()

    df.columns = [
        col.lower().replace('-', '_').replace(' ', '_')
        for col in df.columns
    ]

    text_cols = df.select_dtypes(include='object').columns
    df[text_cols] = df[text_cols].apply(lambda x: x.str.strip().str.lower())

    # Пріоритети повертаємо у UPPER після загального lower — C/H/M/L це коди
    df['order_priority'] = df['order_priority'].str.upper()

    df['order_date'] = pd.to_datetime(df['order_date'])
    df['ship_date']  = pd.to_datetime(df['ship_date'])

    # NaN у ключі JOIN обриває зв'язок з countries — зберігаємо як 'unknown'
    df['country_code'] = df['country_code'].fillna('unknown')

    # Медіана стійкіша за mean() при аномально великих замовленнях
    df['units_sold'] = df['units_sold'].fillna(df['units_sold'].median())

    return df


def build_sales(
    events: pd.DataFrame,
    products: pd.DataFrame,
    countries: pd.DataFrame
) -> pd.DataFrame:
    """
    Load-шар ETL: два LEFT JOIN + розрахунок бізнес-метрик.
    LEFT JOIN обраний свідомо — INNER JOIN призвів би до тихої втрати даних.
    """
    sales = (
        events
        .merge(products,  left_on='product_id',  right_on='id',      how='left')
        .merge(countries, left_on='country_code', right_on='alpha_3', how='left')
    )

    # Технічні дублікати ключів після merge — не потрібні в аналізі
    sales.drop(columns=['id', 'alpha_3', 'alpha_2'], inplace=True)
    sales.rename(columns={'name': 'country_name'}, inplace=True)

    # 82 записи з 'unknown' country_code не знайшли пари в countries при JOIN
    geo_cols = ['country_name', 'region', 'sub_region']
    sales[geo_cols] = sales[geo_cols].fillna('unknown')

    # Порядок важливий: revenue і total_cost мають існувати до profit і margin
    sales['revenue']    = sales['units_sold'] * sales['unit_price']
    sales['total_cost'] = sales['units_sold'] * sales['unit_cost']
    sales['profit']     = sales['revenue'] - sales['total_cost']
    sales['margin']     = sales['profit'] / sales['revenue']

    sales['order_processing'] = (sales['ship_date'] - sales['order_date']).dt.days

    sales['year']       = sales['order_date'].dt.year
    sales['month']      = sales['order_date'].dt.month
    sales['month_year'] = sales['order_date'].dt.to_period('M').astype(str)

    return sales


@st.cache_data
def get_sales_data() -> pd.DataFrame:
    """
    Публічний API модуля — єдина функція яку імпортують сторінки.
    Кешується @st.cache_data: pipeline виконується один раз при старті,
    не повторюється при кожній взаємодії користувача.
    """
    events, products, countries = load_raw_data()
    events    = clean_events(events)
    products  = clean_products(products)
    countries = clean_countries(countries)
    return build_sales(events, products, countries)