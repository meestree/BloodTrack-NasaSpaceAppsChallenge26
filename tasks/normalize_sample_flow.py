"""Replace sample flow readings with reproducible PU examples.

Pass --varied for normal, warning, and danger episodes in two-hour blocks.

Preserves users, timestamps, temperatures, movement flags, and record counts.
Creates a backup in the system temporary directory before modifying the database.
"""
from datetime import datetime
import argparse
from math import sin, tau
from pathlib import Path
from random import Random
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from frontend.components.flow import flow_ranges


def normalize(path: Path, varied: bool = False) -> tuple[Path, int]:
    rng = Random(20261115)
    connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=rw', uri=True)
    backup_path = Path(tempfile.mkdtemp(prefix='bloodtrack-before-sample-pu-')) / path.name
    try:
        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        parts = dict(connection.execute('SELECT id_parte, nombre FROM partes_corporales'))
        for name in parts.values():
            flow_ranges(name)
        count = 0
        for table, primary_key in (('registros', 'id_registro'),
                                   ('mediciones_basales', 'id_medicion_basal')):
            rows = connection.execute(
                f'SELECT {primary_key}, id_parte, timestamp FROM {table} ORDER BY {primary_key}'
            ).fetchall()
            updates = []
            for identifier, part, timestamp in rows:
                danger_low, lower, upper, danger_high = flow_ranges(parts[part])
                time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                day_fraction = (time.hour * 3600 + time.minute * 60 + time.second) / 86400
                width = upper - lower
                value = ((lower + upper) / 2
                         + width * .28 * sin(tau * day_fraction + part * .4)
                         + rng.gauss(0, width * .04))
                value = round(min(upper - .01, max(lower + .01, value)), 2)
                if varied:
                    # Stable two-hour episodes show up in hourly charts rather
                    # than becoming isolated spikes that disappear in means.
                    episode = (time.toordinal() * 7 + time.hour // 2 + part * 3) % 20
                    if episode == 0:
                        value = rng.uniform(danger_low * .35, danger_low * .8)
                    elif episode == 1:
                        value = rng.uniform(danger_high * 1.1, danger_high * 1.3)
                    elif episode in (2, 3):
                        value = rng.uniform(danger_low + .1, lower - .1)
                    elif episode in (4, 5):
                        value = rng.uniform(upper + .1, danger_high - .1)
                    value = round(value, 2)
                updates.append((value, identifier))
            connection.executemany(f'UPDATE {table} SET caudal = ? WHERE {primary_key} = ?', updates)
            assert connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == len(rows)
            for part, name in parts.items():
                _, lower, upper, danger_high = flow_ranges(name)
                if varied:
                    lower, upper = 0, danger_high * 1.31
                invalid = connection.execute(
                    f'SELECT COUNT(*) FROM {table} WHERE id_parte = ? '
                    'AND (caudal IS NULL OR caudal < ? OR caudal > ?)', (part, lower, upper)
                ).fetchone()[0]
                if invalid:
                    raise ValueError(f'Invalid sample PU values in {table}')
            count += len(rows)
        connection.execute('DELETE FROM resumenes_diarios')
        connection.execute('''INSERT INTO resumenes_diarios
            (id_usuario, id_parte, fecha, muestras, temperatura_media, caudal_media, movimiento_unos)
            SELECT id_usuario, id_parte, date(timestamp), COUNT(*),
                   AVG(temperatura), AVG(caudal), SUM(movimiento)
            FROM registros GROUP BY id_usuario, id_parte, date(timestamp)''')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key check failed')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database integrity check failed')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return backup_path, count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--varied', action='store_true', help='Include warning and danger episodes.')
    args = parser.parse_args()
    backup, count = normalize(ROOT / 'data' / 'astronautas.db', varied=args.varied)
    print(f'Updated {count} sample flow readings; daily summaries rebuilt.')
    print(f'Backup: {backup}')
