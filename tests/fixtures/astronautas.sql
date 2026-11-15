-- Schema snapshot of the supplied database; no personal data.

CREATE TABLE usuarios (
    id_usuario       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario   TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE,
    fecha_nacimiento TEXT NOT NULL,
    creado_en        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    CHECK (
        date(fecha_nacimiento) IS NOT NULL
        AND date(fecha_nacimiento) = fecha_nacimiento
    )
);

CREATE VIEW vista_usuarios AS
SELECT
    id_usuario,
    nombre_usuario,
    email,
    fecha_nacimiento,
    CAST(
        strftime('%Y', 'now') - strftime('%Y', fecha_nacimiento)
        - (strftime('%m-%d', 'now') < strftime('%m-%d', fecha_nacimiento))
        AS INTEGER
    ) AS edad,
    creado_en
FROM usuarios;

CREATE TABLE partes_corporales (
    id_parte INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL UNIQUE
        CHECK (nombre IN (
            'Neck',
            'Left arm',
            'Right arm',
            'Left leg',
            'Right leg'
        ))
);

CREATE TABLE registros (
    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario  INTEGER NOT NULL,
    id_parte    INTEGER NOT NULL,
    timestamp   TEXT NOT NULL,
    temperatura REAL NOT NULL,
    caudal      REAL NOT NULL,
    movimiento  INTEGER NOT NULL CHECK (movimiento IN (0, 1)),

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (id_parte)
        REFERENCES partes_corporales (id_parte)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK (datetime(timestamp) IS NOT NULL)
);

CREATE TABLE datos_basales (
    id_datos_basales INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario       INTEGER NOT NULL UNIQUE,

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE mediciones_basales (
    id_medicion_basal INTEGER PRIMARY KEY AUTOINCREMENT,
    id_datos_basales  INTEGER NOT NULL,
    id_parte          INTEGER NOT NULL,
    timestamp         TEXT NOT NULL,
    temperatura       REAL NOT NULL,
    caudal            REAL NOT NULL,
    movimiento        INTEGER NOT NULL CHECK (movimiento IN (0, 1)),

    FOREIGN KEY (id_datos_basales)
        REFERENCES datos_basales (id_datos_basales)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (id_parte)
        REFERENCES partes_corporales (id_parte)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    UNIQUE (id_datos_basales, id_parte),
    CHECK (datetime(timestamp) IS NOT NULL)
);

CREATE INDEX idx_registros_usuario_parte_fecha
    ON registros (id_usuario, id_parte, timestamp);

CREATE INDEX idx_registros_usuario_fecha
    ON registros (id_usuario, timestamp);

CREATE INDEX idx_mediciones_basales_conjunto
    ON mediciones_basales (id_datos_basales, id_parte);
