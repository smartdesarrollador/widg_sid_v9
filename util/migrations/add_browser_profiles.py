"""
Migration: Add browser_profiles table for persistent web sessions
Author: Widget Sidebar Team
Date: 2025-11-03

This migration creates the browser_profiles table to support persistent
browser profiles (cookies, LocalStorage, cache, authentication).
"""

import sqlite3
import logging
from pathlib import Path
import sys

# Add src to path
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent.parent.parent

sys.path.insert(0, str(base_dir))

logger = logging.getLogger(__name__)


def run_migration():
    """Run the migration to add browser_profiles table."""

    db_path = base_dir / "widget_sidebar.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        return False

    print(f"[INFO] Database: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='browser_profiles'
        """)

        if cursor.fetchone():
            print("[WARNING] Tabla 'browser_profiles' ya existe")
            conn.close()
            return True

        # Create browser_profiles table
        print("[INFO] Creando tabla 'browser_profiles'...")

        cursor.execute("""
            CREATE TABLE browser_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                storage_path TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create default profile
        print("[INFO] Creando perfil por defecto...")

        cursor.execute("""
            INSERT INTO browser_profiles (name, storage_path, is_default)
            VALUES ('Default', 'browser_data/default', 1)
        """)

        conn.commit()

        # Verify
        cursor.execute("SELECT COUNT(*) FROM browser_profiles")
        count = cursor.fetchone()[0]

        print(f"[SUCCESS] Migracion completada exitosamente")
        print(f"   - Tabla 'browser_profiles' creada")
        print(f"   - Perfil por defecto agregado")
        print(f"   - Total de perfiles: {count}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Error en migracion: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACION: Add browser_profiles table")
    print("=" * 60)

    success = run_migration()

    print("=" * 60)

    if success:
        print("[SUCCESS] MIGRACION EXITOSA")
        sys.exit(0)
    else:
        print("[ERROR] MIGRACION FALLIDA")
        sys.exit(1)
