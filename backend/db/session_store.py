from typing import Optional
import psycopg
from backend.core.config import config

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

def init_sessions_table():
    with psycopg.connect(config.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()


def get_summary(session_id: str) -> str:
    with psycopg.connect(config.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT summary FROM sessions WHERE session_id = %s", (session_id,))
            result = cur.fetchone()
            return result[0] if result else ""
            
        
def update_summary(session_id: str, summary: str):
    with psycopg.connect(config.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions(session_id, summary)
                VALUES (%s, %s)
                ON CONFLICT (session_id) 
                DO UPDATE SET summary = EXCLUDED.summary, updated_at = NOW()
                """,
                (session_id, summary)
            )
        conn.commit()
        
