"""
Script de prueba para verificar instalación de browser
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Verifica que todos los imports funcionan correctamente."""

    print("=" * 60)
    print("FASE 1: VERIFICACIÓN DE INSTALACIÓN")
    print("=" * 60)

    # Test 1: PyQt6 básico
    print("\n[1/5] Verificando PyQt6...")
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QUrl
        print("[OK] PyQt6")
    except ImportError as e:
        print(f"[ERROR] Error importando PyQt6: {e}")
        return False

    # Test 2: PyQt6-WebEngine
    print("\n[2/5] Verificando PyQt6-WebEngine...")
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        print("[OK] PyQt6-WebEngine")
    except ImportError as e:
        print(f"[ERROR] Error importando PyQt6-WebEngine: {e}")
        return False

    # Test 3: SimpleBrowserWindow
    print("\n[3/5] Verificando SimpleBrowserWindow...")
    try:
        from src.views.simple_browser_window import SimpleBrowserWindow
        print("[OK] SimpleBrowserWindow")
    except ImportError as e:
        print(f"[ERROR] Error importando SimpleBrowserWindow: {e}")
        return False

    # Test 4: SimpleBrowserManager
    print("\n[4/5] Verificando SimpleBrowserManager...")
    try:
        from src.core.simple_browser_manager import SimpleBrowserManager
        print("[OK] SimpleBrowserManager")
    except ImportError as e:
        print(f"[ERROR] Error importando SimpleBrowserManager: {e}")
        return False

    # Test 5: DBManager con métodos de browser
    print("\n[5/5] Verificando DBManager con browser_config...")
    try:
        from src.database.db_manager import DBManager

        # Verificar que la base de datos tiene la tabla
        db = DBManager(":memory:")

        # Verificar que los métodos existen
        assert hasattr(db, 'get_browser_config'), "Metodo get_browser_config no existe"
        assert hasattr(db, 'save_browser_config'), "Metodo save_browser_config no existe"

        # Probar métodos
        config = db.get_browser_config()
        assert 'home_url' in config, "Config no tiene home_url"
        assert config['home_url'] == 'https://www.google.com', "home_url incorrecto"

        # Probar guardar
        new_config = {
            'home_url': 'https://github.com',
            'is_visible': True,
            'width': 600,
            'height': 800
        }
        result = db.save_browser_config(new_config)
        assert result == True, "save_browser_config fallo"

        # Verificar que se guardó
        saved_config = db.get_browser_config()
        assert saved_config['home_url'] == 'https://github.com', "URL no se guardo correctamente"

        db.close()

        print("[OK] DBManager browser methods")

    except Exception as e:
        print(f"[ERROR] Error en DBManager: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] TODAS LAS VERIFICACIONES PASARON")
    print("=" * 60)
    print("\nFASE 1 COMPLETADA")
    print("- PyQt6-WebEngine instalado correctamente")
    print("- Archivos de estructura creados")
    print("- Base de datos migrada con tabla browser_config")
    print("- Todos los imports funcionan correctamente")
    print("\nPróximo paso: FASE 2 - Integración con MainWindow")

    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
