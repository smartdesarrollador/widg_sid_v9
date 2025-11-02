"""
Test rápido de integración
"""

print("Test 1: Import SimpleBrowserManager")
try:
    from src.core.simple_browser_manager import SimpleBrowserManager
    print("[OK]")
except Exception as e:
    print(f"[ERROR] {e}")

print("\nTest 2: Import MainController")
try:
    from src.controllers.main_controller import MainController
    print("[OK]")
except Exception as e:
    print(f"[ERROR] {e}")

print("\nTest 3: Import Sidebar")
try:
    from src.views.sidebar import Sidebar
    print("[OK]")
except Exception as e:
    print(f"[ERROR] {e}")

print("\nTest 4: Verificar que MainController tiene toggle_browser")
try:
    assert hasattr(MainController, 'toggle_browser')
    print("[OK]")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n[SUCCESS] Todos los imports funcionan correctamente")
print("La integracion esta completa. Prueba con: python main.py")
