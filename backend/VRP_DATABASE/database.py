# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_DATABASE\database.py
"""
SQLite + criação/migração do schema.
- get_conn(): conexão
- init_db(): cria e migra tabelas
"""
import sqlite3

try:
    from backend.VRP_SERVICE.export_paths import DB_PATH
except Exception:
    from pathlib import Path
    DB_PATH = Path(__file__).resolve().parents[1] / "VRP_DATABASE" / "vrp.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in cur.fetchall())


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # --- Tabelas base
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('CONTRATANTE','CONTRATADA')) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vrp_sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            place TEXT,
            brand TEXT,
            type TEXT CHECK(type IN ('Ação Direta','Auto-Regulada','Pilotada')),
            dn INTEGER CHECK(dn IN (50,60,85,100,150,200,250,300,350)),
            access_install TEXT CHECK(access_install IN ('passeio','rua')),
            traffic TEXT CHECK(traffic IN ('alto','baixo')),
            lids TEXT CHECK(lids IN ('visiveis','cobertas')),
            notes_access TEXT,
            latitude REAL,
            longitude REAL,
            network_depth_cm REAL,
            has_automation INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            service_type TEXT CHECK(service_type IN ('Manutenção Preventiva','Manutenção Preditiva','Manutenção Corretiva','Ajuste e Aferição')) NOT NULL,
            contractor_id INTEGER,
            contracted_id INTEGER,
            team_id INTEGER,
            vrp_site_id INTEGER,
            has_reg_upstream INTEGER DEFAULT 0,
            has_reg_downstream INTEGER DEFAULT 0,
            has_bypass INTEGER DEFAULT 0,
            notes_hydraulics TEXT,
            p_up_before REAL, p_down_before REAL, p_up_after REAL, p_down_after REAL,
            observations_general TEXT,
            FOREIGN KEY(contractor_id) REFERENCES companies(id),
            FOREIGN KEY(contracted_id) REFERENCES companies(id),
            FOREIGN KEY(team_id) REFERENCES teams(id),
            FOREIGN KEY(vrp_site_id) REFERENCES vrp_sites(id)
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER,
            label TEXT,
            file_path TEXT NOT NULL,
            caption TEXT,
            include_in_report INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            -- vrp_site_id será garantido por migração abaixo (ADD COLUMN)
            FOREIGN KEY(checklist_id) REFERENCES checklists(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER UNIQUE,
            ai_summary TEXT,
            docx_path TEXT,
            pdf_path TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(checklist_id) REFERENCES checklists(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_checklists_site ON checklists(vrp_site_id);
        CREATE INDEX IF NOT EXISTS idx_photos_checklist ON photos(checklist_id);
        """
    )

    # --- Migração: garantir coluna vrp_site_id em photos
    if not _column_exists(conn, "photos", "vrp_site_id"):
        cur.execute("ALTER TABLE photos ADD COLUMN vrp_site_id INTEGER;")
        conn.commit()
        # preenche vrp_site_id usando o checklist vinculado (quando existir)
        cur.execute(
            """
            UPDATE photos
               SET vrp_site_id = (
                    SELECT vrp_site_id FROM checklists
                     WHERE checklists.id = photos.checklist_id
               )
             WHERE vrp_site_id IS NULL;
            """
        )
        conn.commit()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_site ON photos(vrp_site_id);")
        conn.commit()

    # --- Migração: adicionar campos de localização geográfica
    if not _column_exists(conn, "vrp_sites", "latitude"):
        cur.execute("ALTER TABLE vrp_sites ADD COLUMN latitude REAL;")
        conn.commit()
    
    if not _column_exists(conn, "vrp_sites", "longitude"):
        cur.execute("ALTER TABLE vrp_sites ADD COLUMN longitude REAL;")
        conn.commit()

    # --- Migração: adicionar novos campos do checklist
    if not _column_exists(conn, "vrp_sites", "network_depth_cm"):
        cur.execute("ALTER TABLE vrp_sites ADD COLUMN network_depth_cm REAL;")
        conn.commit()
    
    if not _column_exists(conn, "vrp_sites", "has_automation"):
        cur.execute("ALTER TABLE vrp_sites ADD COLUMN has_automation INTEGER DEFAULT 0;")
        conn.commit()

    conn.close()
