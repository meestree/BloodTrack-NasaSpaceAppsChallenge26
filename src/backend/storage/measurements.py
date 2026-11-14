"""User-scoped collection, UTC history, and persisted daily aggregates."""
from datetime import date, datetime

from backend.measurements.schemas import MeasurementBatch
from backend.storage.auth import AuthStore


class UnknownBodyPart(Exception):
    pass


class MeasurementStore:
    def __init__(self, auth_store: AuthStore) -> None:
        self.database = auth_store

    def initialize(self) -> None:
        with self.database.connection() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS resumenes_diarios (
                id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
                id_parte INTEGER NOT NULL REFERENCES partes_corporales(id_parte),
                fecha TEXT NOT NULL,
                muestras INTEGER NOT NULL,
                temperatura_media REAL NOT NULL,
                caudal_media REAL NOT NULL,
                movimiento_unos INTEGER NOT NULL,
                PRIMARY KEY (id_usuario, id_parte, fecha)
            )""")
            # Rebuild on startup to incorporate pre-existing/imported measurements.
            connection.execute("DELETE FROM resumenes_diarios")
            connection.execute("""INSERT INTO resumenes_diarios
                SELECT id_usuario, id_parte, date(timestamp), COUNT(*),
                       AVG(temperatura), AVG(caudal), SUM(movimiento)
                FROM registros GROUP BY id_usuario, id_parte, date(timestamp)""")

    def body_parts(self) -> list[dict]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT id_parte, nombre FROM partes_corporales ORDER BY id_parte")]

    def collect(self, user_id: int, batch: MeasurementBatch) -> list[int]:
        with self.database.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            known = {row[0] for row in connection.execute("SELECT id_parte FROM partes_corporales")}
            if any(item.id_parte not in known for item in batch.measurements):
                raise UnknownBodyPart
            ids = []
            groups = set()
            for item in batch.measurements:
                timestamp = item.timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
                cursor = connection.execute("""INSERT INTO registros
                    (id_usuario, id_parte, timestamp, temperatura, caudal, movimiento)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, item.id_parte, timestamp, item.temperatura, item.caudal, item.movimiento))
                ids.append(cursor.lastrowid)
                groups.add((item.id_parte, item.timestamp.date().isoformat()))
            for part, day in groups:
                connection.execute("""INSERT OR REPLACE INTO resumenes_diarios
                    SELECT id_usuario, id_parte, date(timestamp), COUNT(*),
                           AVG(temperatura), AVG(caudal), SUM(movimiento)
                    FROM registros WHERE id_usuario = ? AND id_parte = ? AND date(timestamp) = ?
                    GROUP BY id_usuario, id_parte, date(timestamp)""", (user_id, part, day))
            return ids

    def history(self, user_id: int, start: datetime, end: datetime,
                part: int | None, limit: int, offset: int) -> dict:
        where = "id_usuario = ? AND julianday(timestamp) >= julianday(?) AND julianday(timestamp) <= julianday(?)"
        args = [user_id, start.isoformat(), end.isoformat()]
        if part is not None:
            where += " AND id_parte = ?"
            args.append(part)
        with self.database.connection() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM registros WHERE {where}", args).fetchone()[0]
            rows = connection.execute(f"""SELECT * FROM registros WHERE {where}
                ORDER BY julianday(timestamp) DESC, id_registro DESC LIMIT ? OFFSET ?""", [*args, limit, offset])
            return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}

    def daily(self, user_id: int, start: datetime, end: datetime, part: int | None) -> list[dict]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("""SELECT * FROM resumenes_diarios
                WHERE id_usuario = ? AND fecha >= ? AND fecha <= ? AND (? IS NULL OR id_parte = ?)
                ORDER BY fecha, id_parte""", (user_id, start.date().isoformat(), end.date().isoformat(), part, part))]

    def analytics(self, user_id: int, start: datetime, end: datetime, days: int, part: int | None) -> list[dict]:
        with self.database.connection() as connection:
            rows = connection.execute("""SELECT id_parte, COUNT(*) AS muestras,
                AVG(temperatura) AS temperatura_media, MIN(temperatura) AS temperatura_min,
                MAX(temperatura) AS temperatura_max, AVG(caudal) AS caudal_media,
                MIN(caudal) AS caudal_min, MAX(caudal) AS caudal_max,
                SUM(movimiento) AS movimiento_unos,
                AVG(movimiento) AS movimiento_fraccion,
                COUNT(DISTINCT date(timestamp)) AS dias_con_datos
                FROM registros WHERE id_usuario = ?
                AND julianday(timestamp) >= julianday(?) AND julianday(timestamp) <= julianday(?)
                AND (? IS NULL OR id_parte = ?) GROUP BY id_parte ORDER BY id_parte""",
                (user_id, start.isoformat(), end.isoformat(), part, part))
            items = []
            for row in rows:
                item = dict(row)
                item["dias_sin_datos"] = days - item["dias_con_datos"]
                item["cobertura_dias_fraccion"] = item["dias_con_datos"] / days
                items.append(item)
            return items

    def latest(self, user_id: int, selected: date | None) -> dict:
        with self.database.connection() as connection:
            if selected is None:
                row = connection.execute("""SELECT date(timestamp) FROM registros
                    WHERE id_usuario = ? ORDER BY julianday(timestamp) DESC, id_registro DESC LIMIT 1""",
                    (user_id,)).fetchone()
                if row is None:
                    return {"date": None, "items": []}
                selected = date.fromisoformat(row[0])
            rows = connection.execute("""WITH ranked AS (
                SELECT r.*, p.nombre,
                    ROW_NUMBER() OVER (PARTITION BY r.id_parte
                        ORDER BY julianday(r.timestamp) DESC, r.id_registro DESC) AS rank
                FROM registros r JOIN partes_corporales p ON p.id_parte = r.id_parte
                WHERE r.id_usuario = ? AND date(r.timestamp) = ?)
                SELECT id_registro, id_usuario, id_parte, nombre, timestamp,
                       temperatura, caudal, movimiento
                FROM ranked WHERE rank = 1 ORDER BY id_parte""", (user_id, selected.isoformat()))
            return {"date": selected.isoformat(), "items": [dict(row) for row in rows]}

    def movement(self, user_id: int, start: date, end: date, part: int | None) -> dict:
        hourly = start == end
        pattern = '%Y-%m-%dT%H:00:00Z' if hourly else '%Y-%m-%d'
        with self.database.connection() as connection:
            rows = connection.execute('''SELECT strftime(?, timestamp) AS periodo,
                COUNT(*) AS muestras, SUM(movimiento) AS movimiento_unos
                FROM registros WHERE id_usuario = ? AND date(timestamp) BETWEEN ? AND ?
                AND (? IS NULL OR id_parte = ?)
                GROUP BY periodo ORDER BY periodo''',
                (pattern, user_id, start.isoformat(), end.isoformat(), part, part))
            return {'from': start.isoformat(), 'to': end.isoformat(),
                    'granularity': 'hour' if hourly else 'day',
                    'items': [dict(row) for row in rows]}

    def statistics(self, user_id: int, start: date, end: date, metric: str) -> dict:
        """Welford sample statistics avoid cancellation in variance calculations."""
        from math import sqrt
        assert metric in ('temperatura', 'caudal')
        pattern = '%Y-%m-%dT%H:00:00Z' if start == end else '%Y-%m-%d'
        groups = {}
        with self.database.connection() as connection:
            rows = connection.execute(f'''SELECT r.id_parte, p.nombre,
                strftime(?, r.timestamp) AS periodo, r.{metric} AS valor
                FROM registros r JOIN partes_corporales p ON p.id_parte = r.id_parte
                WHERE r.id_usuario = ? AND date(r.timestamp) BETWEEN ? AND ?
                ORDER BY julianday(r.timestamp), r.id_registro''',
                (pattern, user_id, start.isoformat(), end.isoformat()))
            for row in rows:
                key = (row['id_parte'], row['periodo'])
                if key not in groups:
                    groups[key] = {'id_parte': row['id_parte'], 'nombre': row['nombre'],
                        'periodo': row['periodo'], 'muestras': 0, 'media': 0.,
                        'm2': 0., 'minimo': row['valor'], 'maximo': row['valor']}
                group = groups[key]
                group['muestras'] += 1
                delta = row['valor'] - group['media']
                group['media'] += delta / group['muestras']
                group['m2'] += delta * (row['valor'] - group['media'])
                group['minimo'] = min(group['minimo'], row['valor'])
                group['maximo'] = max(group['maximo'], row['valor'])
        items = []
        for key in sorted(groups):
            group = groups[key]
            m2 = group.pop('m2')
            group['desviacion_estandar'] = sqrt(max(0., m2) / (group['muestras'] - 1)) if group['muestras'] > 1 else None
            items.append(group)
        return {'from': start.isoformat(), 'to': end.isoformat(), 'metric': metric,
                'granularity': 'hour' if start == end else 'day', 'items': items}
