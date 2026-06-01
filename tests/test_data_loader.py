import pandas as pd
import pytest
from app.services.data_loader import (
    clean_events,
    clean_products,
    get_sales_data,
)


def test_clean_events_removes_nan():
    """clean_events має заповнити всі пропуски: country_code → 'unknown', units_sold → медіана."""
    raw = pd.DataFrame({
        'Order ID':       [1, 2],
        'Order Date':     ['1/1/2015', '2/1/2015'],
        'Ship Date':      ['1/5/2015', '2/5/2015'],
        'Order Priority': ['H', 'M'],
        'Country Code':   [None, 'UKR'],    # навмисний пропуск
        'Product ID':     [100, 200],
        'Sales Channel':  ['Online', 'Offline'],
        'Units Sold':     [None, 500.0],    # навмисний пропуск
        'Unit Price':     [10.0, 20.0],
        'Unit Cost':      [5.0, 10.0],
    })
    cleaned = clean_events(raw)
    assert cleaned.isnull().sum().sum() == 0


def test_clean_products_lowercase():
    """clean_products має нормалізувати регістр — інакше groupby створить дублікати груп."""
    raw = pd.DataFrame({
        'id':        [1, 2],
        'item_type': ['Cosmetics', 'OFFICE SUPPLIES'],
    })
    cleaned = clean_products(raw)
    assert cleaned['item_type'].tolist() == ['cosmetics', 'office supplies']


def test_get_sales_data_shape():
    """Інтеграційний тест: весь pipeline від CSV до фінального df."""
    df = get_sales_data()
    assert df.shape[0] == 1330      # жоден рядок не загубився при merge
    assert 'revenue' in df.columns  # фінансові розрахунки виконані
    assert 'profit'  in df.columns
    assert 'margin'  in df.columns