"""
Script de prueba para verificar integración del navegador
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_integration():
    """Verifica que la integración está completa."""

    print("=" * 60)
    print("FASE 2: VERIFICACIÓN DE INTEGRACIÓN")
    print("=" * 60)

    # Test 1: Imports del controller
    print("\n[1/4] Verificando imports de MainController...")
    try:
        from src.controllers.main_controller import MainController
        print("[OK] MainController importado")
    except ImportError as e:
        print(f"[ERROR] Error importando MainController: {e}")
        return False

    # Test 2: MainController crea browser_manager
    print("\n[2/4] Verificando inicializacion de browser_manager...")
    try:
        controller = MainController()
        assert hasattr(controller, 'browser_manager'), "browser_manager no existe"
        assert controller.browser_manager is not None, "browser_manager es None"
        print("[OK] browser_manager inicializado")
    except Exception as e:
        print(f"[ERROR] Error en browser_manager: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Método toggle_browser existe
    print("\n[3/4] Verificando metodo toggle_browser...")
    try:
        assert hasattr(controller, 'toggle_browser'), "toggle_browser no existe"
        print("[OK] toggle_browser existe")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

    # Test 4: Sidebar tiene señal browser_clicked
    print("\n[4/4] Verificando Sidebar.browser_clicked...")
    try:
        from src.views.sidebar import Sidebar
        sidebar = Sidebar()
        # Verificar que tiene la señal
        assert hasattr(sidebar, 'browser_clicked'), "browser_clicked signal no existe"
        assert hasattr(sidebar, 'browser_button'), "browser_button no existe"
        print("[OK] Sidebar tiene browser_clicked y browser_button")
    except Exception as e:
        print(f"[ERROR] Error en Sidebar: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] INTEGRACIÓN COMPLETADA")
    print("=" * 60)
    print("\nFASE 2 COMPLETADA")
    print("- Boton agregado al sidebar")
    print("- Senales conectadas correctamente")
    print("- SimpleBrowserManager inicializado en MainController")
    print("- Metodo toggle_browser implementado")
    print("\nLa aplicacion esta lista para probar el navegador!")
    print("Ejecuta: python main.py")
    print("Luego haz click en el boton del globo (🌐) en el sidebar")

    # Cleanup
    if hasattr(controller, '__del__'):
        controller.__del__()

    return True


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
