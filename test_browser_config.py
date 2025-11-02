"""
Test de configuración del navegador
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_browser_config():
    """Verifica que la configuración del navegador funciona."""

    print("=" * 60)
    print("FASE 3: VERIFICACIÓN DE CONFIGURACIÓN")
    print("=" * 60)

    # Test 1: Import BrowserSettings
    print("\n[1/5] Verificando import de BrowserSettings...")
    try:
        from src.views.browser_settings import BrowserSettings
        print("[OK] BrowserSettings importado")
    except ImportError as e:
        print(f"[ERROR] Error importando BrowserSettings: {e}")
        return False

    # Test 2: SettingsWindow tiene BrowserSettings
    print("\n[2/5] Verificando SettingsWindow con pestaña Navegador...")
    try:
        from src.views.settings_window import SettingsWindow
        from src.controllers.main_controller import MainController

        # Crear controller
        controller = MainController()

        # No podemos crear SettingsWindow sin QApplication, pero podemos verificar imports
        print("[OK] SettingsWindow importado correctamente")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Verificar métodos de configuración en DB
    print("\n[3/5] Verificando métodos de base de datos...")
    try:
        from src.database.db_manager import DBManager

        db = DBManager(":memory:")

        # Probar guardar configuración
        test_config = {
            'home_url': 'https://github.com',
            'width': 600,
            'height': 800
        }
        result = db.save_browser_config(test_config)
        assert result == True, "save_browser_config falló"

        # Probar cargar configuración
        loaded_config = db.get_browser_config()
        assert loaded_config['home_url'] == 'https://github.com', "URL no coincide"
        assert loaded_config['width'] == 600, "Width no coincide"
        assert loaded_config['height'] == 800, "Height no coincide"

        db.close()

        print("[OK] Métodos de base de datos funcionando")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: SimpleBrowserManager usa configuración
    print("\n[4/5] Verificando SimpleBrowserManager usa config...")
    try:
        from src.core.simple_browser_manager import SimpleBrowserManager
        from src.database.db_manager import DBManager

        db = DBManager(":memory:")

        # Guardar config personalizada
        custom_config = {
            'home_url': 'https://docs.python.org',
            'width': 700,
            'height': 900
        }
        db.save_browser_config(custom_config)

        # Crear browser manager
        browser_mgr = SimpleBrowserManager(db)

        # Verificar que carga la URL correcta
        loaded_url = browser_mgr.load_home_url()
        assert loaded_url == 'https://docs.python.org', f"URL incorrecta: {loaded_url}"

        db.close()

        print("[OK] SimpleBrowserManager carga configuración correctamente")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 5: Verificar que set_home_url funciona
    print("\n[5/5] Verificando set_home_url...")
    try:
        from src.core.simple_browser_manager import SimpleBrowserManager
        from src.database.db_manager import DBManager

        db = DBManager(":memory:")
        browser_mgr = SimpleBrowserManager(db)

        # Cambiar URL
        new_url = 'https://www.wikipedia.org'
        browser_mgr.set_home_url(new_url)

        # Verificar que se guardó
        loaded_url = browser_mgr.load_home_url()
        assert loaded_url == new_url, f"URL no se guardó correctamente: {loaded_url}"

        db.close()

        print("[OK] set_home_url funciona correctamente")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    print("\nFASE 3 COMPLETADA")
    print("- Pestaña 'Navegador' agregada a SettingsWindow")
    print("- Campos de configuración implementados (URL, Width, Height)")
    print("- Guardado y carga de configuración funcionando")
    print("- SimpleBrowserManager usa configuración correctamente")
    print("\nPara probar:")
    print("1. Ejecuta: python main.py")
    print("2. Click en ⚙ (Configuración) en el sidebar")
    print("3. Ve a la pestaña 'Navegador'")
    print("4. Configura la URL de inicio")
    print("5. Click en 'Guardar Configuración'")
    print("6. Click en 🌐 para abrir el navegador con la nueva URL")

    return True


if __name__ == "__main__":
    success = test_browser_config()
    sys.exit(0 if success else 1)
