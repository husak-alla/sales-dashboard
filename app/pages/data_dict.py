import streamlit as st
import pandas as pd
from app.components.header import page_title


def render_data_dict(df: pd.DataFrame) -> None:
    """Документація датасету: поля, якість даних, методологічні рішення."""

    page_title(
        icon="book-fill",
        title="Data Dictionary",
        caption="Опис полів, бізнес-логіка розрахунків та якість даних",
    )

    st.subheader("Джерела даних")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📄 **events.csv**\n\n1 330 записів · 10 сирих полів\n\nОсновна таблиця транзакцій продажів 2010–2017")
    with col2:
        st.info("📄 **products.csv**\n\n12 записів · 2 поля\n\nКласифікатор товарних категорій")
    with col3:
        st.info("📄 **countries.csv**\n\n249 записів · 5 полів\n\nДовідник країн та регіонів ISO 3166")

    st.divider()

    st.subheader("Опис полів")

    # Список словників → DataFrame: кожен словник = один рядок таблиці
    fields = pd.DataFrame([
        # events.csv — сирі поля
        {'Таблиця': 'events',     'Поле': 'Order ID',       'Тип': 'int64',    'Опис': 'Унікальний ідентифікатор замовлення',   'Примітки': 'Primary key'},
        {'Таблиця': 'events',     'Поле': 'Order Date',     'Тип': 'datetime', 'Опис': 'Дата оформлення замовлення',            'Примітки': 'Конвертовано з MM/DD/YYYY'},
        {'Таблиця': 'events',     'Поле': 'Ship Date',      'Тип': 'datetime', 'Опис': 'Дата відправки замовлення',             'Примітки': 'Конвертовано з MM/DD/YYYY'},
        {'Таблиця': 'events',     'Поле': 'Order Priority', 'Тип': 'str',      'Опис': 'Пріоритет замовлення',                  'Примітки': 'C=Critical, H=High, M=Medium, L=Low'},
        {'Таблиця': 'events',     'Поле': 'Country Code',   'Тип': 'str',      'Опис': 'ISO alpha-3 код країни',                'Примітки': 'Пропуски заповнено "unknown"'},
        {'Таблиця': 'events',     'Поле': 'Product ID',     'Тип': 'int64',    'Опис': 'Ідентифікатор товарної категорії',      'Примітки': 'Foreign key → products.id'},
        {'Таблиця': 'events',     'Поле': 'Sales Channel',  'Тип': 'str',      'Опис': 'Канал продажів',                        'Примітки': 'Online / Offline'},
        {'Таблиця': 'events',     'Поле': 'Units Sold',     'Тип': 'float64',  'Опис': 'Кількість проданих одиниць',            'Примітки': 'Пропуски заповнено медіаною'},
        {'Таблиця': 'events',     'Поле': 'Unit Price',     'Тип': 'float64',  'Опис': 'Ціна за одиницю товару ($)',            'Примітки': 'Базис для revenue'},
        {'Таблиця': 'events',     'Поле': 'Unit Cost',      'Тип': 'float64',  'Опис': 'Собівартість одиниці товару ($)',       'Примітки': 'Базис для profit'},
        # products.csv
        {'Таблиця': 'products',   'Поле': 'id',             'Тип': 'int64',    'Опис': 'Ідентифікатор категорії',               'Примітки': 'Primary key, joins з events.Product ID'},
        {'Таблиця': 'products',   'Поле': 'item_type',      'Тип': 'str',      'Опис': 'Назва товарної категорії',              'Примітки': '12 категорій: cosmetics, baby food, household, …'},
        # countries.csv
        {'Таблиця': 'countries',  'Поле': 'name',           'Тип': 'str',      'Опис': 'Назва країни',                          'Примітки': 'Використовується в KPI та на карті'},
        {'Таблиця': 'countries',  'Поле': 'alpha-2',        'Тип': 'str',      'Опис': '2-літерний код ISO 3166-1',             'Примітки': 'Namibia: "NA" → відновлено вручну'},
        {'Таблиця': 'countries',  'Поле': 'alpha-3',        'Тип': 'str',      'Опис': '3-літерний код ISO 3166-1',             'Примітки': 'Joins з events.Country Code'},
        {'Таблиця': 'countries',  'Поле': 'region',         'Тип': 'str',      'Опис': 'Регіон (Europe, Asia, …)',              'Примітки': 'Використовується в donut і KPI Geography'},
        {'Таблиця': 'countries',  'Поле': 'sub-region',     'Тип': 'str',      'Опис': 'Субрегіон (Eastern Europe, …)',         'Примітки': 'Деталізація region'},
        # розраховані поля — результат build_sales() в data_loader.py
        {'Таблиця': 'розрахунок', 'Поле': 'revenue',        'Тип': 'float64',  'Опис': 'Загальний дохід',                       'Примітки': 'Units Sold × Unit Price'},
        {'Таблиця': 'розрахунок', 'Поле': 'total_cost',     'Тип': 'float64',  'Опис': 'Загальна собівартість',                 'Примітки': 'Units Sold × Unit Cost'},
        {'Таблиця': 'розрахунок', 'Поле': 'profit',         'Тип': 'float64',  'Опис': 'Чистий прибуток',                       'Примітки': 'revenue − total_cost'},
        {'Таблиця': 'розрахунок', 'Поле': 'margin',         'Тип': 'float64',  'Опис': 'Маржинальність',                        'Примітки': 'profit / revenue (для KPI — зважена)'},
        {'Таблиця': 'розрахунок', 'Поле': 'order_processing','Тип': 'int64',   'Опис': 'Час обробки замовлення (днів)',          'Примітки': '(Ship Date − Order Date).days'},
        {'Таблиця': 'розрахунок', 'Поле': 'year / month_year','Тип': 'int/str','Опис': 'Похідні від дати',                      'Примітки': 'Для агрегацій у трендах'},
    ])

    st.dataframe(fields, use_container_width=True, hide_index=True)
    st.divider()

    st.subheader("Якість даних після очищення")

    total_rows  = len(df)
    total_cols  = len(df.columns)
    total_nulls = int(df.isnull().sum().sum())
    total_dupes = int(df.duplicated().sum())

    nulls_icon = "✅" if total_nulls == 0 else "⚠️"
    dupes_icon = "✅" if total_dupes == 0 else "⚠️"

    # f"{n:,}".replace(",", " ") — форматування з пробілом як розділювачем тисяч
    def _fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    col4, col5, col6, col7 = st.columns(4)
    with col4: st.metric("✅ Рядків",              _fmt(total_rows))
    with col5: st.metric(f"{nulls_icon} Пропусків", _fmt(total_nulls))
    with col6: st.metric(f"{dupes_icon} Дублікатів", _fmt(total_dupes))
    with col7: st.metric("✅ Колонок",              f"{total_cols}")

    # 10 сирих полів з events.csv, решта — похідні після join і розрахунків
    RAW_COLUMNS_COUNT = 10
    derived_count     = total_cols - RAW_COLUMNS_COUNT
    st.caption(
        f"_{total_cols} колонок у df = {RAW_COLUMNS_COUNT} сирих (events) "
        f"+ {derived_count} похідних (розрахунки, joins з products/countries)_"
    )

    st.divider()

    # Перевіряємо наявність колонок явно — точніше ніж широкий try/except
    total_rev  = df['revenue'].sum()     if 'revenue'      in df.columns else 0
    europe_rev = df[df['region'] == 'Europe']['revenue'].sum() if 'region' in df.columns else 0
    europe_pct = (europe_rev / total_rev * 100) if total_rev else 0.0
    unknown_count = df[df['country_name'] == 'unknown'].shape[0] if 'country_name' in df.columns else 0

    st.subheader("Примітки")
    st.markdown(f"""
    - **Датасет:** навчальний · мета — демонстрація архітектури дашборду
    - **Період:** 2010–2017 · 8 років · {_fmt(total_rows)} транзакцій
    - **Географія:** переважно Європа (**{europe_pct:.1f}%** доходу)
    - **Joins:** `events.Product ID → products.id` і `events.Country Code → countries.alpha-3`
    - **Unknown:** **{unknown_count}** записів без `country_code` — показуємо окремо як data gap
    - **Namibia:** код `NA` помилково читається pandas як `NaN` — відновлено вручну на етапі ініціалізації
    - **Медіана:** використана для заповнення пропусків у `Units Sold` — стійка до аномальних викидів
    - **Маржа:** на KPI використовується **зважена** (`SUM(profit) / SUM(revenue)`), а не середня по рядках — щоб великі замовлення впливали пропорційно до їх фінансової ваги
    """)