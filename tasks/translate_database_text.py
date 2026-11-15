"""Translate stored body-part labels without changing API field names.

Run from the project root with the project's Python interpreter.
"""
from pathlib import Path
import sqlite3


TRANSLATIONS = {
    'Cuello': 'Neck',
    'Brazo izquierdo': 'Left arm',
    'Brazo derecho': 'Right arm',
    'Pierna izquierda': 'Left leg',
    'Pierna derecha': 'Right leg',
}


def translate(path: Path) -> None:
    connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=rw', uri=True)
    try:
        connection.execute('PRAGMA foreign_keys = OFF')
        connection.execute('BEGIN IMMEDIATE')
        rows = connection.execute('SELECT id_parte, nombre FROM partes_corporales').fetchall()
        translated = [(identifier, TRANSLATIONS.get(name, name)) for identifier, name in rows]
        if any(name not in TRANSLATIONS.values() for _, name in translated):
            raise ValueError('Unrecognized body-part label; no changes made.')
        connection.execute("""CREATE TABLE partes_corporales_english (
            id_parte INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE CHECK (nombre IN (
                'Neck', 'Left arm', 'Right arm', 'Left leg', 'Right leg'
            ))
        )""")
        connection.executemany('INSERT INTO partes_corporales_english VALUES (?, ?)', translated)
        connection.execute('DROP TABLE partes_corporales')
        connection.execute('ALTER TABLE partes_corporales_english RENAME TO partes_corporales')
        if connection.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign key check failed; changes rolled back.')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Integrity check failed; changes rolled back.')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    translate(Path(__file__).resolve().parents[1] / 'data' / 'astronautas.db')
    print('Body-part labels translated. Integrity and foreign keys verified.')
