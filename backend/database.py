from psycopg import Connection, connect
from psycopg.rows import dict_row

from config import DATABASE_URL


def get_connection() -> Connection:
    return connect(DATABASE_URL, row_factory=dict_row)
