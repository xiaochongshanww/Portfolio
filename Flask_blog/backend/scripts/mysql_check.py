import os, sys, json, sqlalchemy as sa
from sqlalchemy import text

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print(json.dumps({'ok': False, 'error': 'DATABASE_URL not set'}))
    sys.exit(1)

engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
res = {'ok': True, 'url': DATABASE_URL, 'server_version': None, 'variables': {}, 'schemas_match': True, 'notes': []}
try:
    with engine.connect() as conn:
        ver = conn.execute(text('SELECT VERSION()')).scalar()
        res['server_version'] = ver
        # Charset / collation quick check (MySQL / MariaDB)
        try:
            charset = conn.execute(text("SHOW VARIABLES LIKE 'character_set_server'" )).fetchone()
            coll = conn.execute(text("SHOW VARIABLES LIKE 'collation_server'" )).fetchone()
            if charset: res['variables']['character_set_server'] = charset[1]
            if coll: res['variables']['collation_server'] = coll[1]
            if charset and charset[1].lower() not in ('utf8mb4','utf8mb4_0900_ai_ci'):
                res['notes'].append('Recommend utf8mb4 for full Unicode support')
        except Exception as e:
            res['notes'].append(f'variable check skipped: {e}')
        # Compare existing columns vs models (simple)
        from app import create_app, db
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
        with app.app_context():
            insp = sa.inspect(db.engine)
            missing = []
            from app.models import Article
            # minimal check: ensure views_count column exists
            cols = [c['name'] for c in insp.get_columns('articles')]
            if 'views_count' not in cols:
                missing.append('articles.views_count')
            res['schemas_missing'] = missing
            if missing:
                res['schemas_match'] = False
except Exception as e:
    res['ok'] = False
    res['error'] = str(e)

print(json.dumps(res, ensure_ascii=False, indent=2))
