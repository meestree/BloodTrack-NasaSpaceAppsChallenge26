"""Add synthetic samples every 15 minutes for today so far (UTC).

Mostly normal PU readings with short low/high warning and danger episodes.
Existing records are retained; repeated runs skip already seeded timestamps.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from math import sin
from pathlib import Path
from random import Random
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from frontend.components.flow import flow_ranges


def seed_today(path: Path) -> tuple[int, dict, Path]:
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rng = Random(int(now.strftime('%Y%m%d')))
    counts = Counter()
    backup_path = Path(tempfile.mkdtemp(prefix='bloodtrack-before-today-')) / path.name
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=rw', uri=True)
    try:
        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        before = connection.execute('SELECT COUNT(*) FROM registros').fetchone()[0]
        users = [row[0] for row in connection.execute('SELECT id_usuario FROM usuarios')]
        parts = connection.execute('SELECT id_parte,nombre FROM partes_corporales ORDER BY id_parte').fetchall()
        existing = {(user, part, datetime.fromisoformat(timestamp.replace('Z', '+00:00')))
                    for user, part, timestamp in connection.execute(
                        'SELECT id_usuario,id_parte,timestamp FROM registros WHERE date(timestamp)=?',
                        (midnight.date().isoformat(),))}
        rows = []
        for user in users:
            for slot in range(int((now - midnight).total_seconds() // 900) + 1):
                timestamp = midnight + timedelta(minutes=15 * slot)
                for part, name in parts:
                    low, normal_low, normal_high, high = flow_ranges(name)
                    episode = (slot + part * 3) % 40
                    category = 'normal'
                    value = rng.uniform(normal_low + .5, normal_high - .5)
                    if episode == 0:
                        category, value = 'low danger', rng.uniform(low * .4, low * .8)
                    elif episode == 20:
                        category, value = 'high danger', rng.uniform(high * 1.1, high * 1.25)
                    elif episode in (1, 2):
                        category, value = 'low warning', rng.uniform(low + .1, normal_low - .1)
                    elif episode in (21, 22):
                        category, value = 'high warning', rng.uniform(normal_high + .1, high - .1)
                    temperature = round(max(35.5, min(37, 36.3 + .3 * sin(slot / 6 + part) + rng.gauss(0, .08))), 2)
                    movement = int(rng.random() < (.4 if category != 'normal' else .1))
                    if (user, part, timestamp) not in existing:
                        counts[category] += 1
                        rows.append((user, part, timestamp.isoformat().replace('+00:00', 'Z'),
                                     temperature, round(value, 2), movement))
        connection.executemany('''INSERT INTO registros
            (id_usuario,id_parte,timestamp,temperatura,caudal,movimiento) VALUES (?,?,?,?,?,?)''', rows)
        day = midnight.date().isoformat()
        connection.execute('DELETE FROM resumenes_diarios WHERE fecha=?', (day,))
        connection.execute('''INSERT INTO resumenes_diarios
            (id_usuario,id_parte,fecha,muestras,temperatura_media,caudal_media,movimiento_unos)
            SELECT id_usuario,id_parte,date(timestamp),COUNT(*),AVG(temperatura),AVG(caudal),SUM(movimiento)
            FROM registros WHERE date(timestamp)=? GROUP BY id_usuario,id_parte,date(timestamp)''', (day,))
        assert connection.execute('SELECT COUNT(*) FROM registros').fetchone()[0] == before + len(rows)
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        connection.commit()
        return len(rows), dict(counts), backup_path
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    count, categories, backup = seed_today(ROOT / 'data' / 'astronautas.db')
    print(f'Added {count} samples for today (UTC): {categories}')
    print(f'Backup: {backup}')
