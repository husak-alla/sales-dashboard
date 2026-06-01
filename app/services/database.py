import sqlite3
import pandas as pd
from pathlib import Path

# processed/ — папка для згенерованих даних, відокремлена від raw/
DB_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "sales.db"


def save_to_db(df: pd.DataFrame) -> None:
    """Зберігає DataFrame у таблицю 'sales'. Створює файл БД якщо не існує."""
    conn = sqlite3.connect(DB_PATH)
    # if_exists='replace' — безпечний перезапис при повторному виклику
    df.to_sql('sales', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Збережено {len(df)} рядків у {DB_PATH}")


def get_db_connection() -> sqlite3.Connection:
    """Повертає з'єднання з БД. Виносимо окремо — одне місце для зміни шляху."""
    return sqlite3.connect(DB_PATH)


def query_db(sql: str) -> pd.DataFrame:
    """Виконує SQL і повертає результат як DataFrame."""
    conn = get_db_connection()
    result = pd.read_sql_query(sql, conn)
    conn.close()
    return result