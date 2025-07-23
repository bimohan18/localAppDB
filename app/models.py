# app/models.py
import oracledb
from app.config import DB_CONFIG

def get_db_connection():
    try:
        connection = oracledb.connect(
            user=DB_CONFIG["username"],
            password=DB_CONFIG["password"],
            dsn=DB_CONFIG["dsn"]
        )
        return connection
    except oracledb.DatabaseError as e:
        print(f"Database connection error: {e}")
        return None
