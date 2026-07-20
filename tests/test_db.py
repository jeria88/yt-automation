import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db

def test_tables_created():
    engine = db.engine
    # SQLAlchemy 2.x
    tables = db.metadata.tables.keys()
    assert len(tables) >= 4, f"expected >=4 tables, got {tables}"
    for t in ("videos", "hooks", "scripts", "posts"):
        assert t in tables, f"missing table {t}"
