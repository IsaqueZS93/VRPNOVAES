"""
SQLite + criação/migração do schema.
- get_conn(): conexão
- init_db(): cria e migra tabelas
"""
import sqlite3
from pathlib import Path

try:
    from backend.VRP_SERVICE.export_paths import DB_PATH
except Exception:
    DB_PATH = Path(__file__).resolve().parents[1] / "VRP_DATABASE" / "vrp.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r["name"] == column for r in cur.fetchall())


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cur.fetchone() is not None


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ---------------- MIGRAÇÃO ROBUSTA DA TABELA PHOTOS ----------------
    # 1) Se já existe 'photos' com colunas antigas, migra para o novo layout
    if _table_exists(conn, "photos"):
        cur.execute("PRAGMA table_info(photos);")
        cols = [r["name"] for r in cur.fetchall()]
        if ("path" in cols) or ("include" in cols) or ("order_num" in cols):
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS photos_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_id INTEGER,
                    vrp_site_id INTEGER,
                    file_path TEXT,
                    drive_file_id TEXT,
                    label TEXT,
                    caption TEXT,
                    include_in_report INTEGER,
                    display_order INTEGER
                );
            """)
            # Copia dados antigos -> novos nomes (drive_file_id fica NULL)
            cur.execute("""
                INSERT INTO photos_temp (id, checklist_id, vrp_site_id, file_path, label, caption, include_in_report, display_order, drive_file_id)
                SELECT id, checklist_id, vrp_site_id, path, label, caption, include, order_num, NULL
                FROM photos;
            """)
            cur.execute("DROP TABLE photos;")
            cur.execute("ALTER TABLE photos_temp RENAME TO photos;")
            conn.commit()

        # 2) Se a photos existe, mas por algum motivo falta 'drive_file_id', adiciona
        if not _column_exists(conn, "photos", "drive_file_id"):
            cur.execute("ALTER TABLE photos ADD COLUMN drive_file_id TEXT;")
            conn.commit()

        # 3) Se alguma das colunas novas faltar (situação rara), tenta renomear
        # Obs: normalmente o bloco acima (temp-table) já resolve isso.
        if (not _column_exists(conn, "photos", "file_path")) and _column_exists(conn, "photos", "path"):
            try:
                cur.execute("ALTER TABLE photos RENAME COLUMN path TO file_path;")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        if (not _column_exists(conn, "photos", "include_in_report")) and _column_exists(conn, "photos", "include"):
            try:
                cur.execute("ALTER TABLE photos RENAME COLUMN include TO include_in_report;")
                conn.commit()
            except sqlite3.OperationalError:
                pass
        if (not _column_exists(conn, "photos", "display_order")) and _column_exists(conn, "photos", "order_num"):
            try:
                cur.execute("ALTER TABLE photos RENAME COLUMN order_num TO display_order;")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    # ---------------- TABELAS BASE (idempotentes) ----------------
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
            ai_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER,
            ai_summary TEXT,
            docx_path TEXT,
            pdf_path TEXT
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER,
            vrp_site_id INTEGER,
            file_path TEXT,
            drive_file_id TEXT,
            label TEXT,
            caption TEXT,
            include_in_report INTEGER,
            display_order INTEGER
        );

        CREATE TABLE IF NOT EXISTS email_destinatarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE
        );
        """
    )

    # Garante coluna nova em vrp_sites (rodará só se faltar)
    if not _column_exists(conn, "vrp_sites", "has_automation"):
        cur.execute("ALTER TABLE vrp_sites ADD COLUMN has_automation INTEGER DEFAULT 0;")
        conn.commit()

    # Garante 'drive_file_id' mesmo que a tabela photos tenha sido criada agora por outro .db antigo
    if not _column_exists(conn, "photos", "drive_file_id"):
        cur.execute("ALTER TABLE photos ADD COLUMN drive_file_id TEXT;")
        conn.commit()

    conn.close()


# ----------------- utilitários de emails -----------------
def add_destinatario(email: str) -> bool:
    """Adiciona um novo destinatário de email"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO email_destinatarios (email) VALUES (?)", (email,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Email já existe
        try:
            conn.close()
        except Exception:
            pass
        return False
    except Exception as e:
        # Log do erro para debug
        print(f"Erro ao adicionar email {email}: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def remove_destinatario(email: str) -> bool:
    """Remove um destinatário de email"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM email_destinatarios WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return False


def listar_destinatarios() -> list:
    """Lista todos os destinatários de email"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT email FROM email_destinatarios ORDER BY email")
        emails = [row["email"] for row in cur.fetchall()]
        conn.close()
        return emails
    except Exception:
        # Se a tabela não existir por algum motivo, cria e retorna lista vazia
        conn = get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_destinatarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE
            );
        """)
        conn.commit()
        conn.close()
        return []
