"""
Main Window View
"""
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QScreen, QShortcut, QKeySequence
import sys
import logging
import traceback
from pathlib import Path
import ctypes
from ctypes import wintypes

sys.path.insert(0, str(Path(__file__).parent.parent))
from views.sidebar import Sidebar
from views.floating_panel import FloatingPanel
from views.global_search_panel import GlobalSearchPanel
from views.favorites_floating_panel import FavoritesFloatingPanel
from views.stats_floating_panel import StatsFloatingPanel
from views.settings_window import SettingsWindow
from views.pinned_panels_window import PinnedPanelsWindow
from views.dialogs.popular_items_dialog import PopularItemsDialog
from views.dialogs.forgotten_items_dialog import ForgottenItemsDialog
from views.dialogs.suggestions_dialog import FavoriteSuggestionsDialog
from views.dialogs.stats_dashboard import StatsDashboard
from views.dialogs.panel_config_dialog import PanelConfigDialog
from views.category_filter_window import CategoryFilterWindow
from models.item import Item
from core.hotkey_manager import HotkeyManager
from core.tray_manager import TrayManager
from core.session_manager import SessionManager
from core.notification_manager import NotificationManager

# Get logger
logger = logging.getLogger(__name__)

# ===========================================================================
# Windows AppBar API Constants and Structures
# ===========================================================================
ABM_NEW = 0x00000000
ABM_REMOVE = 0x00000001
ABM_QUERYPOS = 0x00000002
ABM_SETPOS = 0x00000003
ABE_RIGHT = 2


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]


class MainWindow(QMainWindow):
    """Main application window - frameless, always-on-top sidebar"""

    # Signals
    category_selected = pyqtSignal(str)  # category_id
    item_selected = pyqtSignal(object)  # Item

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.config_manager = controller.config_manager if controller else None
        self.sidebar = None
        self.floating_panel = None  # Panel flotante activo (no anclado) - compatibility
        self.pinned_panels = []  # Lista de paneles anclados
        self.pinned_panels_window = None  # Ventana de gestión de paneles anclados
        self.global_search_panel = None  # Ventana flotante para búsqueda global
        self.favorites_panel = None  # Ventana flotante para favoritos
        self.stats_panel = None  # Ventana flotante para estadísticas
        self.structure_dashboard = None  # Dashboard de estructura (no-modal)
        self.category_filter_window = None  # Ventana de filtros de categorías
        self.current_category_id = None  # Para el toggle
        self.hotkey_manager = None
        self.tray_manager = None
        self.notification_manager = NotificationManager()
        self.is_visible = True

        # Panel shortcuts management
        self.panel_shortcuts = {}  # Dict[panel_id, QShortcut] - Track keyboard shortcuts for panels
        self.panel_by_shortcut = {}  # Dict[shortcut_str, panel] - Quick lookup panel by shortcut

        # Minimizar/Maximizar estado
        self.is_minimized = False
        self.normal_height = None  # Se guardará después de calcular
        self.minimized_height = 75  # Altura cuando está minimizada (title bar 30px + WS label ~45px)

        # AppBar state (para reservar espacio en Windows)
        self.appbar_registered = False

        self.init_ui()
        self.position_window()
        self.register_appbar()  # Registrar como AppBar para reservar espacio
        self.setup_hotkeys()
        self.setup_tray()
        self.check_notifications_delayed()

        # AUTO-RESTORE: Restore pinned panels from database on startup
        self.restore_pinned_panels_on_startup()

    def init_ui(self):
        """Initialize the user interface"""
        # Window properties
        self.setWindowTitle("Widget Sidebar")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Calculate window height: 100% of screen height (toda la altura disponible menos barra de tareas)
        screen = self.screen()
        if screen:
            screen_height = screen.availableGeometry().height()
            window_height = screen_height  # 100% de la altura disponible (menos barra de tareas)
        else:
            window_height = 600  # Fallback

        # Guardar altura normal para minimizar/maximizar
        self.normal_height = window_height

        # Set window size (starts with sidebar only)
        self.setFixedWidth(70)  # Just sidebar initially
        self.setMinimumHeight(400)
        self.resize(70, window_height)

        # Set window opacity
        self.setWindowOpacity(0.95)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout (vertical: title bar + sidebar)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar with minimize and close buttons
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom: 1px solid #007acc;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(5, 0, 5, 0)
        title_bar_layout.setSpacing(5)

        # Spacer
        title_bar_layout.addStretch()

        # Minimize button
        self.minimize_button = QPushButton("─")
        self.minimize_button.setFixedSize(25, 25)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #007acc;
            }
        """)
        self.minimize_button.clicked.connect(self.minimize_window)
        title_bar_layout.addWidget(self.minimize_button)

        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(25, 25)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c42b1c;
                border: 1px solid #e81123;
                color: #ffffff;
            }
        """)
        self.close_button.clicked.connect(self.close_window)
        title_bar_layout.addWidget(self.close_button)

        main_layout.addWidget(title_bar)

        # Create sidebar only (no embedded panel)
        self.sidebar = Sidebar()
        self.sidebar.category_clicked.connect(self.on_category_clicked)
        self.sidebar.global_search_clicked.connect(self.on_global_search_clicked)
        self.sidebar.favorites_clicked.connect(self.on_favorites_clicked)
        self.sidebar.stats_clicked.connect(self.on_stats_clicked)
        self.sidebar.browser_clicked.connect(self.on_browser_clicked)
        self.sidebar.dashboard_clicked.connect(self.open_structure_dashboard)
        self.sidebar.settings_clicked.connect(self.open_settings)
        self.sidebar.category_filter_clicked.connect(self.on_category_filter_clicked)
        main_layout.addWidget(self.sidebar)

    def load_categories(self, categories):
        """Load categories into sidebar"""
        if self.sidebar:
            self.sidebar.load_categories(categories)

    def on_category_clicked(self, category_id: str):
        """Handle category button click - toggle floating panel"""
        try:
            logger.info(f"Category clicked: {category_id}")

            # Toggle: Si se hace clic en la misma categoría Y el panel NO está anclado, ocultarlo
            if (self.current_category_id == category_id and
                self.floating_panel and
                self.floating_panel.isVisible() and
                not self.floating_panel.is_pinned):
                logger.info(f"Toggling off - hiding floating panel for category: {category_id}")
                self.floating_panel.hide()
                self.current_category_id = None
                return

            # Get category from controller
            if self.controller:
                logger.debug(f"Getting category {category_id} from controller...")
                category = self.controller.get_category(category_id)

                if category:
                    logger.info(f"Category found: {category.name} with {len(category.items)} items")

                    # Si el panel actual está anclado, agregarlo a la lista de pinned
                    if self.floating_panel and self.floating_panel.is_pinned:
                        logger.info(f"Current panel is pinned, adding to pinned_panels list")
                        if self.floating_panel not in self.pinned_panels:
                            self.pinned_panels.append(self.floating_panel)
                        self.floating_panel = None  # Clear current panel

                    # Create floating panel if it doesn't exist or current one is pinned
                    if not self.floating_panel:
                        self.floating_panel = FloatingPanel(
                            config_manager=self.config_manager,
                            list_controller=self.controller.list_controller if self.controller else None
                        )
                        self.floating_panel.item_clicked.connect(self.on_item_clicked)
                        self.floating_panel.window_closed.connect(self.on_floating_panel_closed)
                        self.floating_panel.pin_state_changed.connect(self.on_panel_pin_changed)
                        self.floating_panel.customization_requested.connect(self.on_panel_customization_requested)
                        logger.debug("New floating panel created")

                    # Load category into floating panel
                    self.floating_panel.load_category(category)

                    # Position near sidebar (con offset si hay paneles anclados)
                    self.position_new_panel(self.floating_panel)

                    # Update current category
                    self.current_category_id = category_id

                    logger.debug("Category loaded into floating panel")
                else:
                    logger.warning(f"Category {category_id} not found")

            # Emit signal
            self.category_selected.emit(category_id)
            logger.debug("Category selected signal emitted")

        except Exception as e:
            logger.error(f"Error in on_category_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al cargar categoría:\n{str(e)}\n\nRevisa widget_sidebar_error.log"
            )

    def on_floating_panel_closed(self):
        """Handle floating panel closed"""
        logger.info("Floating panel closed")

        # Determinar qué panel se cerró
        sender_panel = self.sender()

        # Si es el panel actual (no anclado)
        if sender_panel == self.floating_panel:
            logger.info("Closing active (non-pinned) panel")
            self.current_category_id = None  # Reset para el toggle
            if self.floating_panel:
                self.floating_panel.deleteLater()
                self.floating_panel = None
        else:
            # Es un panel anclado
            logger.info("Closing pinned panel")
            if sender_panel in self.pinned_panels:
                self.pinned_panels.remove(sender_panel)
                sender_panel.deleteLater()
                logger.info(f"Pinned panel removed. Remaining pinned panels: {len(self.pinned_panels)}")

    def on_panel_pin_changed(self, is_pinned):
        """Handle when a panel's pin state changes"""
        sender_panel = self.sender()
        logger.info(f"Panel pin state changed: is_pinned={is_pinned}")

        if is_pinned:
            # Panel was just pinned
            if sender_panel == self.floating_panel:
                logger.info("Active panel was pinned - will create new panel on next category click")

            # AUTO-SAVE: Save panel to database when pinned
            if sender_panel.current_category and self.controller:
                try:
                    category_id = sender_panel.current_category.id

                    # Save panel state to database
                    panel_id = self.controller.pinned_panels_manager.save_panel_state(
                        panel_widget=sender_panel,
                        category_id=category_id,
                        custom_name=sender_panel.custom_name,
                        custom_color=sender_panel.custom_color
                    )

                    # Store panel_id in the FloatingPanel instance
                    sender_panel.panel_id = panel_id
                    logger.info(f"[SHORTCUT DEBUG] Panel anchored with panel_id: {panel_id}")

                    # Register keyboard shortcut if one was assigned
                    logger.info(f"[SHORTCUT DEBUG] Retrieving panel data to check for keyboard shortcut")
                    panel_data = self.controller.pinned_panels_manager.get_panel_by_id(panel_id)
                    logger.info(f"[SHORTCUT DEBUG] Panel data retrieved: {panel_data}")

                    if panel_data:
                        shortcut = panel_data.get('keyboard_shortcut')
                        logger.info(f"[SHORTCUT DEBUG] Keyboard shortcut from database: '{shortcut}'")
                        if shortcut:
                            logger.info(f"[SHORTCUT DEBUG] Registering shortcut '{shortcut}' for newly pinned panel {panel_id}")
                            self.register_panel_shortcut(sender_panel, shortcut)
                        else:
                            logger.info(f"[SHORTCUT DEBUG] No keyboard shortcut assigned to panel {panel_id}")
                    else:
                        logger.warning(f"[SHORTCUT DEBUG] Could not retrieve panel data for panel_id {panel_id}")

                    logger.info(f"Panel auto-saved to database with ID: {panel_id} (Category: {sender_panel.current_category.name})")

                except Exception as e:
                    logger.error(f"Error auto-saving panel: {e}", exc_info=True)
        else:
            # Panel was unpinned
            if sender_panel in self.pinned_panels:
                # Remove from pinned list and make it the active panel
                self.pinned_panels.remove(sender_panel)
                if self.floating_panel:
                    # Current active panel becomes pinned
                    if self.floating_panel.is_pinned:
                        self.pinned_panels.append(self.floating_panel)
                self.floating_panel = sender_panel
                logger.info(f"Panel unpinned and became active panel. Remaining pinned: {len(self.pinned_panels)}")

            # Delete panel from database if it was saved
            if sender_panel.panel_id and self.controller:
                try:
                    # Unregister keyboard shortcut before deleting
                    self.unregister_panel_shortcut(sender_panel)

                    self.controller.pinned_panels_manager.delete_panel(sender_panel.panel_id)
                    logger.info(f"Panel {sender_panel.panel_id} deleted from database on unpin")
                    # Clear panel_id so it won't try to update anymore
                    sender_panel.panel_id = None
                except Exception as e:
                    logger.error(f"Error deleting panel from database on unpin: {e}", exc_info=True)

    def position_new_panel(self, panel):
        """Position a new panel always at the same initial position (next to sidebar)"""
        # Calculate base position (next to sidebar) - always the same position
        panel.position_near_sidebar(self)
        logger.info(f"Panel positioned at initial position next to sidebar")

    def on_global_search_clicked(self):
        """Handle global search button click - show global search panel"""
        try:
            logger.info("Global search button clicked")

            if not self.controller:
                logger.error("No controller available")
                return

            # Create global search panel if it doesn't exist
            if not self.global_search_panel:
                # Get db_manager from controller's config_manager
                db_manager = self.config_manager.db if self.config_manager else None
                self.global_search_panel = GlobalSearchPanel(
                    db_manager=db_manager,
                    config_manager=self.config_manager
                )
                self.global_search_panel.item_clicked.connect(self.on_item_clicked)
                self.global_search_panel.window_closed.connect(self.on_global_search_panel_closed)
                logger.debug("Global search panel created")

            # Load all items
            self.global_search_panel.load_all_items()

            # Position near sidebar
            self.global_search_panel.position_near_sidebar(self)

            logger.debug("Global search panel loaded and positioned")

        except Exception as e:
            logger.error(f"Error in on_global_search_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir búsqueda global:\n{str(e)}\n\nRevisa widget_sidebar_error.log"
            )

    def on_global_search_panel_closed(self):
        """Handle global search panel closed"""
        logger.info("Global search panel closed")
        if self.global_search_panel:
            self.global_search_panel.deleteLater()
            self.global_search_panel = None

    def on_favorites_clicked(self):
        """Handle favorites button click - show favorites panel"""
        try:
            logger.info("Favorites button clicked")

            # Toggle: Si ya está visible, ocultarlo
            if self.favorites_panel and self.favorites_panel.isVisible():
                logger.info("Hiding favorites panel")
                self.favorites_panel.hide()
                return

            # Crear panel si no existe
            if not self.favorites_panel:
                self.favorites_panel = FavoritesFloatingPanel()
                self.favorites_panel.favorite_executed.connect(self.on_favorite_executed)
                self.favorites_panel.window_closed.connect(self.on_favorites_panel_closed)
                logger.debug("Favorites panel created")

            # Posicionar cerca del sidebar
            self.favorites_panel.position_near_sidebar(self)

            # Mostrar panel
            self.favorites_panel.show()
            self.favorites_panel.refresh()

            logger.info("Favorites panel shown")

        except Exception as e:
            logger.error(f"Error in on_favorites_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al mostrar favoritos:\n{str(e)}"
            )

    def on_favorites_panel_closed(self):
        """Handle favorites panel closed"""
        logger.info("Favorites panel closed")
        if self.favorites_panel:
            self.favorites_panel.deleteLater()
            self.favorites_panel = None

    def on_favorite_executed(self, item_id: int):
        """Handle favorite item executed"""
        try:
            logger.info(f"Favorite item executed: {item_id}")

            # Buscar el item y ejecutarlo
            if self.controller:
                # Aquí deberías tener una forma de obtener el item por ID
                # Por ahora solo hacemos log
                logger.info(f"Executing favorite item {item_id}")

        except Exception as e:
            logger.error(f"Error executing favorite: {e}", exc_info=True)

    def on_stats_clicked(self):
        """Handle stats button click - show stats panel"""
        try:
            logger.info("Stats button clicked")

            # Toggle: Si ya está visible, ocultarlo
            if self.stats_panel and self.stats_panel.isVisible():
                logger.info("Hiding stats panel")
                self.stats_panel.hide()
                return

            # Crear panel si no existe
            if not self.stats_panel:
                self.stats_panel = StatsFloatingPanel()
                self.stats_panel.window_closed.connect(self.on_stats_panel_closed)
                logger.debug("Stats panel created")

            # Posicionar cerca del sidebar
            self.stats_panel.position_near_sidebar(self)

            # Mostrar panel
            self.stats_panel.show()
            self.stats_panel.refresh()

            logger.info("Stats panel shown")

        except Exception as e:
            logger.error(f"Error in on_stats_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al mostrar estadísticas:\n{str(e)}"
            )

    def on_stats_panel_closed(self):
        """Handle stats panel closed"""
        logger.info("Stats panel closed")
        if self.stats_panel:
            self.stats_panel.deleteLater()
            self.stats_panel = None

    def on_browser_clicked(self):
        """Handle browser button click - toggle browser window"""
        try:
            logger.info("Browser button clicked")

            # Delegar al controller para toggle del navegador
            if self.controller:
                self.controller.toggle_browser()
            else:
                logger.warning("Controller not available")

        except Exception as e:
            logger.error(f"Error in on_browser_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir navegador:\n{str(e)}"
            )

    def open_structure_dashboard(self):
        """Open the structure dashboard"""
        try:
            logger.info("Opening structure dashboard...")

            if not self.controller:
                logger.error("No controller available")
                QMessageBox.warning(
                    self,
                    "Error",
                    "No hay controlador disponible"
                )
                return

            from views.dashboard.structure_dashboard import StructureDashboard

            # Create dashboard as non-modal window
            dashboard = StructureDashboard(
                db_manager=self.controller.config_manager.db,
                parent=self
            )

            # Store reference to keep it alive
            self.structure_dashboard = dashboard

            # Show as non-modal (allows interaction with main sidebar)
            dashboard.show()

            logger.info("Structure dashboard opened (non-modal)")

        except Exception as e:
            logger.error(f"Error opening structure dashboard: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al abrir dashboard de estructura:\n{str(e)}"
            )

    def on_category_filter_clicked(self):
        """Handle category filter button click - show filter window"""
        try:
            logger.info("Category filter button clicked")

            # Toggle: Si ya está visible, ocultarlo
            if self.category_filter_window and self.category_filter_window.isVisible():
                logger.info("Hiding category filter window")
                self.category_filter_window.hide()
                return

            # Crear ventana si no existe
            if not self.category_filter_window:
                self.category_filter_window = CategoryFilterWindow(self)
                self.category_filter_window.filters_changed.connect(self.on_category_filters_changed)
                self.category_filter_window.filters_cleared.connect(self.on_category_filters_cleared)
                self.category_filter_window.window_closed.connect(self.on_category_filter_window_closed)
                logger.debug("Category filter window created")

            # Posicionar a la IZQUIERDA del sidebar
            sidebar_rect = self.geometry()
            filter_window_width = self.category_filter_window.width()
            window_x = sidebar_rect.left() - filter_window_width - 10
            window_y = sidebar_rect.top()
            self.category_filter_window.move(window_x, window_y)

            # Mostrar ventana
            self.category_filter_window.show()

            logger.info("Category filter window shown")

        except Exception as e:
            logger.error(f"Error in on_category_filter_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al mostrar filtros de categorías:\n{str(e)}"
            )

    def on_category_filters_changed(self, filters: dict):
        """Handle category filters changed"""
        try:
            logger.info(f"Category filters changed: {filters}")

            # Aplicar filtros a través del controller
            if self.controller:
                self.controller.apply_category_filters(filters)

        except Exception as e:
            logger.error(f"Error applying category filters: {e}", exc_info=True)

    def on_category_filters_cleared(self):
        """Handle category filters cleared"""
        try:
            logger.info("Category filters cleared")

            # Recargar todas las categorías
            if self.controller:
                self.controller.load_all_categories()

        except Exception as e:
            logger.error(f"Error clearing category filters: {e}", exc_info=True)

    def on_category_filter_window_closed(self):
        """Handle category filter window closed"""
        logger.info("Category filter window closed")
        # No eliminamos la ventana, solo la ocultamos para reutilizarla

    def on_item_clicked(self, item: Item):
        """Handle item button click"""
        try:
            logger.info(f"Item clicked: {item.label}")

            # Copy to clipboard via controller
            if self.controller:
                logger.debug(f"Copying item to clipboard: {item.content[:50]}...")
                self.controller.copy_item_to_clipboard(item)
                logger.info("Item copied to clipboard successfully")

            # Emit signal
            self.item_selected.emit(item)

        except Exception as e:
            logger.error(f"Error in on_item_clicked: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al copiar item:\n{str(e)}\n\nRevisa widget_sidebar_error.log"
            )

    def position_window(self):
        """Position window on the right edge of the screen, ocupando toda la altura"""
        # Get primary screen
        screen = self.screen()
        if screen is None:
            return

        screen_geometry = screen.availableGeometry()

        # Position on right edge, arriba del todo (y=0)
        x = screen_geometry.width() - self.width()
        y = screen_geometry.y()  # Arriba del todo (puede ser 0 o el offset si hay barra superior)

        self.move(x, y)

    def register_appbar(self):
        """Registrar la ventana como AppBar de Windows para reservar espacio permanentemente"""
        try:
            if sys.platform != 'win32':
                logger.warning("AppBar solo funciona en Windows")
                return

            # Get window handle
            hwnd = int(self.winId())
            if not hwnd:
                logger.error("No se pudo obtener el window handle")
                return

            # Get screen geometry
            screen = self.screen()
            if not screen:
                return

            screen_geometry = screen.availableGeometry()

            # Create APPBARDATA structure
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = hwnd
            abd.uCallbackMessage = 0
            abd.uEdge = ABE_RIGHT  # Lado derecho

            # Set the rectangle for the AppBar (right edge)
            abd.rc.left = screen_geometry.width() - self.width()
            abd.rc.top = screen_geometry.y()
            abd.rc.right = screen_geometry.width()
            abd.rc.bottom = screen_geometry.y() + screen_geometry.height()

            # Register the AppBar
            result = ctypes.windll.shell32.SHAppBarMessage(ABM_NEW, ctypes.byref(abd))
            if result:
                logger.info("AppBar registrada exitosamente - espacio reservado en el escritorio")
                self.appbar_registered = True

                # Query and set position to reserve space
                ctypes.windll.shell32.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
                ctypes.windll.shell32.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
            else:
                logger.warning("No se pudo registrar AppBar")

        except Exception as e:
            logger.error(f"Error al registrar AppBar: {e}")
            logger.debug(traceback.format_exc())

    def unregister_appbar(self):
        """Desregistrar la ventana como AppBar al cerrar"""
        try:
            if not self.appbar_registered:
                return

            if sys.platform != 'win32':
                return

            hwnd = int(self.winId())
            if not hwnd:
                return

            # Create APPBARDATA structure
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = hwnd

            # Unregister the AppBar
            ctypes.windll.shell32.SHAppBarMessage(ABM_REMOVE, ctypes.byref(abd))
            self.appbar_registered = False
            logger.info("AppBar desregistrada")

        except Exception as e:
            logger.error(f"Error al desregistrar AppBar: {e}")

    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def setup_hotkeys(self):
        """Setup global hotkeys"""
        self.hotkey_manager = HotkeyManager()

        # Register Ctrl+Shift+V to toggle window visibility
        self.hotkey_manager.register_hotkey("ctrl+shift+v", self.toggle_visibility)

        # Start listening for hotkeys
        self.hotkey_manager.start()

        print("Hotkeys registered: Ctrl+Shift+V (toggle window)")

    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_manager = TrayManager()

        # Connect tray signals
        self.tray_manager.show_window_requested.connect(self.show_window)
        self.tray_manager.hide_window_requested.connect(self.hide_window)
        self.tray_manager.settings_requested.connect(self.show_settings)
        self.tray_manager.stats_dashboard_requested.connect(self.show_stats_dashboard)
        self.tray_manager.popular_items_requested.connect(self.show_popular_items)
        self.tray_manager.forgotten_items_requested.connect(self.show_forgotten_items)
        self.tray_manager.pinned_panels_requested.connect(self.open_pinned_panels_window)
        self.tray_manager.logout_requested.connect(self.logout_session)
        self.tray_manager.quit_requested.connect(self.quit_application)

        # Setup tray icon
        self.tray_manager.setup_tray(self)

        print("System tray icon created")

    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.hide_window()
        else:
            self.show_window()

    def show_window(self):
        """Show the window"""
        self.show()
        self.activateWindow()
        self.raise_()

    def minimize_window(self):
        """Toggle minimize/maximize sidebar height"""
        if self.is_minimized:
            # Maximizar - restaurar altura normal
            logger.info("Maximizing sidebar to normal height")
            self.is_minimized = False

            # Mostrar el sidebar
            if self.sidebar:
                self.sidebar.show()

            # Cambiar altura a normal
            self.setMinimumHeight(400)
            self.resize(70, self.normal_height)

            # Cambiar icono a minimizar (línea horizontal)
            self.minimize_button.setText("─")

            logger.info(f"Sidebar maximized to height: {self.normal_height}")
        else:
            # Minimizar - reducir altura para mostrar solo header "WS"
            logger.info("Minimizing sidebar to compact height")
            self.is_minimized = True

            # Ocultar el sidebar (todo excepto el title bar)
            if self.sidebar:
                self.sidebar.hide()

            # Cambiar altura a mínima (solo title bar)
            self.setMinimumHeight(self.minimized_height)
            self.resize(70, self.minimized_height)

            # Cambiar icono a maximizar (cuadrado)
            self.minimize_button.setText("□")

            logger.info(f"Sidebar minimized to height: {self.minimized_height}")

    def close_window(self):
        """Close the application"""
        logger.info("Closing application from close button")
        self.quit_application()

    def hide_window(self):
        """Hide the window"""
        self.hide()
        self.is_visible = False
        if self.tray_manager:
            self.tray_manager.update_window_state(False)
        print("Window hidden")

    def open_settings(self):
        """Open settings window"""
        print("Opening settings window...")
        settings_window = SettingsWindow(controller=self.controller, parent=self)
        settings_window.settings_changed.connect(self.on_settings_changed)

        if settings_window.exec() == QMessageBox.DialogCode.Accepted:
            print("Settings saved")

    def show_settings(self):
        """Show settings dialog (called from tray)"""
        self.open_settings()

    def on_settings_changed(self):
        """Handle settings changes"""
        print("Settings changed - reloading...")

        # Reload categories in sidebar
        if self.controller:
            categories = self.controller.get_categories()
            self.sidebar.load_categories(categories)

        # Apply appearance settings (opacity, etc.)
        if self.config_manager:
            opacity = self.config_manager.get_setting("opacity", 0.95)
            self.setWindowOpacity(opacity)

        print("Settings applied")

    def logout_session(self):
        """Logout current session"""
        logger.info("Logging out...")

        # Confirm logout
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Estás seguro que deseas cerrar sesión?\n\nDeberás ingresar tu contraseña nuevamente al abrir la aplicación.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Invalidate session
            session_manager = SessionManager()
            session_manager.invalidate_session()
            logger.info("Session invalidated")

            # Show notification
            if self.tray_manager:
                self.tray_manager.show_message(
                    "Sesión Cerrada",
                    "Has cerrado sesión exitosamente. La aplicación se cerrará."
                )

            # Quit application
            self.quit_application()

    def quit_application(self):
        """Quit the application"""
        print("Quitting application...")

        # Unregister AppBar
        self.unregister_appbar()

        # Stop hotkey manager
        if self.hotkey_manager:
            self.hotkey_manager.stop()

        # Cleanup tray
        if self.tray_manager:
            self.tray_manager.cleanup()

        # Close window
        self.close()

        # Exit application
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def check_notifications_delayed(self):
        """Verificar notificaciones 10 segundos después de abrir"""
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10000, self.check_notifications)  # 10 segundos

    def check_notifications(self):
        """Verificar y mostrar notificaciones pendientes"""
        try:
            notifications = self.notification_manager.get_pending_notifications()

            if not notifications:
                logger.info("No pending notifications")
                return

            # Mostrar solo las 2 primeras notificaciones (no saturar)
            priority_notifications = notifications[:2]

            logger.info(f"Found {len(notifications)} notifications, showing {len(priority_notifications)}")

            # Por ahora, solo mostramos un diálogo simple con la primera notificación de alta prioridad
            for notification in priority_notifications:
                if notification.get('priority') == 'high':
                    self.show_notification_message(notification)
                    break

        except Exception as e:
            logger.error(f"Error checking notifications: {e}")

    def show_notification_message(self, notification: dict):
        """Mostrar mensaje de notificación"""
        title = notification.get('title', 'Notificación')
        message = notification.get('message', '')
        action = notification.get('action', '')

        reply = QMessageBox.question(
            self,
            title,
            f"{message}\n\n¿Deseas verlo ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.handle_notification_action(action)

    def handle_notification_action(self, action: str):
        """Manejar acción de notificación"""
        try:
            if action == 'show_favorite_suggestions':
                self.show_favorite_suggestions()

            elif action == 'show_cleanup_suggestions':
                self.show_forgotten_items()

            elif action == 'show_abandoned_items':
                self.show_forgotten_items()

            elif action == 'show_failing_items':
                # TODO: Crear diálogo específico para items con errores
                QMessageBox.information(
                    self,
                    "Items con Errores",
                    "Funcionalidad en desarrollo"
                )

            elif action == 'show_slow_items':
                # TODO: Crear diálogo específico para items lentos
                QMessageBox.information(
                    self,
                    "Items Lentos",
                    "Funcionalidad en desarrollo"
                )

            elif action == 'show_shortcut_suggestions':
                # TODO: Crear diálogo para asignar atajos
                QMessageBox.information(
                    self,
                    "Sugerencias de Atajos",
                    "Funcionalidad en desarrollo"
                )

        except Exception as e:
            logger.error(f"Error handling notification action '{action}': {e}")

    def show_popular_items(self):
        """Mostrar diálogo de items populares"""
        try:
            dialog = PopularItemsDialog(self)
            dialog.item_selected.connect(self.on_popular_item_selected)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing popular items: {e}")
            QMessageBox.critical(self, "Error", f"Error al mostrar items populares:\n{str(e)}")

    def show_forgotten_items(self):
        """Mostrar diálogo de items olvidados"""
        try:
            dialog = ForgottenItemsDialog(self)
            if dialog.exec():
                # Recargar categorías si se eliminaron items
                if self.controller:
                    categories = self.controller.get_categories()
                    self.sidebar.load_categories(categories)
        except Exception as e:
            logger.error(f"Error showing forgotten items: {e}")
            QMessageBox.critical(self, "Error", f"Error al mostrar items olvidados:\n{str(e)}")

    def show_stats_dashboard(self):
        """Mostrar dashboard completo de estadísticas"""
        try:
            dialog = StatsDashboard(self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing stats dashboard: {e}")
            QMessageBox.critical(self, "Error", f"Error al mostrar dashboard de estadísticas:\n{str(e)}")

    def show_favorite_suggestions(self):
        """Mostrar diálogo de sugerencias de favoritos"""
        try:
            dialog = FavoriteSuggestionsDialog(self)
            if dialog.exec():
                # Refrescar panel de favoritos si existe
                if self.favorites_panel:
                    self.favorites_panel.refresh()
        except Exception as e:
            logger.error(f"Error showing favorite suggestions: {e}")
            QMessageBox.critical(self, "Error", f"Error al mostrar sugerencias:\n{str(e)}")

    def on_popular_item_selected(self, item_id: int):
        """Handler cuando se selecciona un item popular"""
        logger.info(f"Popular item selected: {item_id}")
        # TODO: Abrir el item o mostrarlo en la lista principal

    def on_panel_customization_requested(self):
        """Handle customization request from a pinned panel"""
        sender_panel = self.sender()
        logger.info(f"Customization requested for panel: {sender_panel.get_display_name()}")

        # Get current values
        current_name = sender_panel.custom_name or ""
        current_color = sender_panel.custom_color or "#007acc"
        category_name = sender_panel.current_category.name if sender_panel.current_category else ""

        # Get current keyboard shortcut from database if panel is saved
        current_shortcut = ""
        if sender_panel.panel_id and self.controller:
            panel_data = self.controller.pinned_panels_manager.get_panel_by_id(sender_panel.panel_id)
            if panel_data:
                current_shortcut = panel_data.get('keyboard_shortcut', '')

        # Open config dialog
        dialog = PanelConfigDialog(
            current_name=current_name,
            current_color=current_color,
            current_shortcut=current_shortcut,
            category_name=category_name,
            parent=self
        )

        # Connect save signal
        dialog.config_saved.connect(lambda name, color, shortcut: self.on_panel_customized(sender_panel, name, color, shortcut))

        # Show dialog
        dialog.exec()

    def on_panel_customized(self, panel, custom_name: str, custom_color: str, keyboard_shortcut: str):
        """Handle panel customization save"""
        logger.info(f"[SHORTCUT DEBUG] on_panel_customized called with shortcut: '{keyboard_shortcut}'")
        logger.info(f"Applying customization - Name: '{custom_name}', Color: {custom_color}, Shortcut: '{keyboard_shortcut}'")
        logger.info(f"[SHORTCUT DEBUG] Panel has panel_id: {panel.panel_id}")

        # Update panel appearance
        panel.update_customization(custom_name=custom_name, custom_color=custom_color)

        # If panel has panel_id (saved in database), update there too
        if panel.panel_id and self.controller:
            logger.info(f"[SHORTCUT DEBUG] Updating panel {panel.panel_id} in database with shortcut: '{keyboard_shortcut}'")
            self.controller.pinned_panels_manager.update_panel_customization(
                panel_id=panel.panel_id,
                custom_name=custom_name if custom_name else None,
                custom_color=custom_color,
                keyboard_shortcut=keyboard_shortcut if keyboard_shortcut else None
            )
            logger.info(f"Updated panel {panel.panel_id} in database")

            # Update keyboard shortcut registration
            logger.info(f"[SHORTCUT DEBUG] About to unregister old shortcut for panel {panel.panel_id}")
            self.unregister_panel_shortcut(panel)  # Remove old shortcut if exists
            if keyboard_shortcut:  # Register new shortcut if provided
                logger.info(f"[SHORTCUT DEBUG] About to register new shortcut '{keyboard_shortcut}' for panel {panel.panel_id}")
                self.register_panel_shortcut(panel, keyboard_shortcut)
            else:
                logger.info(f"[SHORTCUT DEBUG] No shortcut to register (empty string)")

    def register_panel_shortcut(self, panel, shortcut_str: str):
        """
        Register a keyboard shortcut for a panel to toggle minimize/maximize

        Args:
            panel: FloatingPanel instance
            shortcut_str: Keyboard shortcut string (e.g., 'Ctrl+Shift+1')
        """
        logger.info(f"[SHORTCUT DEBUG] register_panel_shortcut called with: '{shortcut_str}', panel_id: {panel.panel_id}")

        if not shortcut_str:
            logger.warning(f"[SHORTCUT DEBUG] Empty shortcut_str, not registering")
            return

        if not panel.panel_id:
            logger.warning(f"[SHORTCUT DEBUG] Panel has no panel_id, not registering")
            return

        try:
            # Remove old shortcut if panel already has one
            logger.info(f"[SHORTCUT DEBUG] Removing old shortcut if exists")
            self.unregister_panel_shortcut(panel)

            # Create QShortcut
            logger.info(f"[SHORTCUT DEBUG] Creating QShortcut for '{shortcut_str}'")
            key_sequence = QKeySequence(shortcut_str)
            logger.info(f"[SHORTCUT DEBUG] QKeySequence created: {key_sequence.toString()}")

            shortcut = QShortcut(key_sequence, self)
            # CRITICAL: Set context to ApplicationShortcut so it works even when panel is minimized
            from PyQt6.QtCore import Qt
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            logger.info(f"[SHORTCUT DEBUG] QShortcut object created with ApplicationShortcut context")
            logger.info(f"[SHORTCUT DEBUG] Connecting to activation handler")
            shortcut.activated.connect(lambda: self.on_panel_shortcut_activated(panel))

            # Store references
            self.panel_shortcuts[panel.panel_id] = shortcut
            self.panel_by_shortcut[shortcut_str] = panel

            logger.info(f"[SHORTCUT DEBUG] Successfully registered shortcut {shortcut_str} for panel {panel.panel_id}")
            logger.info(f"[SHORTCUT DEBUG] Total registered shortcuts: {len(self.panel_shortcuts)}")
            logger.info(f"[SHORTCUT DEBUG] Shortcuts dict: {list(self.panel_shortcuts.keys())}")
        except Exception as e:
            logger.error(f"[SHORTCUT DEBUG] Failed to register shortcut {shortcut_str}: {e}", exc_info=True)

    def unregister_panel_shortcut(self, panel):
        """
        Unregister keyboard shortcut for a panel

        Args:
            panel: FloatingPanel instance
        """
        if not panel.panel_id:
            return

        try:
            # Find and remove shortcut
            if panel.panel_id in self.panel_shortcuts:
                shortcut = self.panel_shortcuts[panel.panel_id]

                # Find shortcut string to remove from lookup dict
                shortcut_str = None
                for key, value in self.panel_by_shortcut.items():
                    if value == panel:
                        shortcut_str = key
                        break

                # Disconnect and delete shortcut
                shortcut.setEnabled(False)
                shortcut.activated.disconnect()
                del self.panel_shortcuts[panel.panel_id]

                if shortcut_str:
                    del self.panel_by_shortcut[shortcut_str]

                logger.info(f"Unregistered shortcut for panel {panel.panel_id}")
        except Exception as e:
            logger.error(f"Failed to unregister shortcut for panel {panel.panel_id}: {e}", exc_info=True)

    def on_panel_shortcut_activated(self, panel):
        """
        Handle keyboard shortcut activation - toggle panel minimize/maximize

        Args:
            panel: FloatingPanel instance
        """
        try:
            logger.info(f"[SHORTCUT DEBUG] ========== SHORTCUT ACTIVATED ==========")
            logger.info(f"[SHORTCUT DEBUG] Shortcut activated for panel {panel.panel_id}")
            logger.info(f"[SHORTCUT DEBUG] Panel minimized state: {panel.is_minimized}")
            logger.info(f"[SHORTCUT DEBUG] Panel visible: {panel.isVisible()}")

            # Toggle minimize/maximize state
            logger.info(f"[SHORTCUT DEBUG] Calling panel.toggle_minimize()")
            panel.toggle_minimize()
            logger.info(f"[SHORTCUT DEBUG] After toggle, minimized state: {panel.is_minimized}")

            # Make sure panel is visible and on top
            if not panel.isVisible():
                logger.info(f"[SHORTCUT DEBUG] Panel not visible, showing it")
                panel.show()
            logger.info(f"[SHORTCUT DEBUG] Raising panel to front")
            panel.raise_()
            panel.activateWindow()
            logger.info(f"[SHORTCUT DEBUG] ========== SHORTCUT ACTIVATION COMPLETE ==========")

        except Exception as e:
            logger.error(f"[SHORTCUT DEBUG] Error handling shortcut activation for panel {panel.panel_id}: {e}", exc_info=True)

    def open_pinned_panels_window(self):
        """Open the pinned panels management window"""
        if not self.controller:
            logger.error("No controller available")
            return

        # Create window if doesn't exist
        if not self.pinned_panels_window:
            self.pinned_panels_window = PinnedPanelsWindow(
                panels_manager=self.controller.pinned_panels_manager,
                parent=self
            )
            # Connect signals
            self.pinned_panels_window.panel_open_requested.connect(self.on_restore_panel_requested)
            self.pinned_panels_window.panel_deleted.connect(self.on_panel_deleted_from_window)
            self.pinned_panels_window.panel_updated.connect(self.on_panel_updated_from_window)
            logger.debug("Pinned panels window created")

        # Show and raise window
        self.pinned_panels_window.show()
        self.pinned_panels_window.raise_()
        self.pinned_panels_window.activateWindow()
        logger.info("Pinned panels window opened")

    def restore_pinned_panels_on_startup(self):
        """AUTO-RESTORE: Restore active pinned panels from database on application startup"""
        if not self.controller:
            logger.warning("No controller available - skipping panel restoration")
            return

        try:
            # Get all active panels from database
            active_panels = self.controller.pinned_panels_manager.restore_panels_on_startup()

            if not active_panels:
                logger.info("No active panels to restore")
                return

            logger.info(f"Restoring {len(active_panels)} active panels from database...")

            # Restore each panel
            for panel_data in active_panels:
                try:
                    panel_id = panel_data['id']
                    category_id = panel_data['category_id']

                    # Get category
                    category = self.controller.get_category(str(category_id))
                    if not category:
                        logger.warning(f"Category {category_id} not found for panel {panel_id} - skipping")
                        continue

                    # Create new floating panel with saved configuration
                    restored_panel = FloatingPanel(
                        config_manager=self.config_manager,
                        list_controller=self.controller.list_controller if self.controller else None,
                        panel_id=panel_id,
                        custom_name=panel_data.get('custom_name'),
                        custom_color=panel_data.get('custom_color')
                    )

                    # Connect signals
                    restored_panel.item_clicked.connect(self.on_item_clicked)
                    restored_panel.window_closed.connect(self.on_floating_panel_closed)
                    restored_panel.pin_state_changed.connect(self.on_panel_pin_changed)
                    restored_panel.customization_requested.connect(self.on_panel_customization_requested)

                    # Load category
                    restored_panel.load_category(category)

                    # Restore position and size
                    restored_panel.move(panel_data['x_position'], panel_data['y_position'])
                    restored_panel.resize(panel_data['width'], panel_data['height'])

                    # Apply custom styling
                    restored_panel.apply_custom_styling()

                    # Set as pinned
                    restored_panel.is_pinned = True
                    restored_panel.pin_button.setText("📍")
                    restored_panel.minimize_button.setVisible(True)
                    restored_panel.config_button.setVisible(True)

                    # Restore minimized state if needed
                    if panel_data.get('is_minimized'):
                        restored_panel.toggle_minimize()

                    # Restore filter configuration if available
                    if panel_data.get('filter_config'):
                        filter_config = self.controller.pinned_panels_manager._deserialize_filter_config(
                            panel_data['filter_config']
                        )
                        if filter_config:
                            restored_panel.apply_filter_config(filter_config)
                            logger.debug(f"Applied saved filters to panel {panel_id}")

                    # Add to pinned panels list
                    self.pinned_panels.append(restored_panel)

                    # Update last_opened in database
                    self.controller.pinned_panels_manager.mark_panel_opened(panel_id)

                    # Register keyboard shortcut if one is assigned
                    if panel_data.get('keyboard_shortcut'):
                        self.register_panel_shortcut(restored_panel, panel_data['keyboard_shortcut'])

                    # Show panel
                    restored_panel.show()

                    logger.info(f"Panel {panel_id} (Category: {category.name}) restored successfully")

                except Exception as e:
                    logger.error(f"Error restoring panel {panel_data.get('id', 'unknown')}: {e}", exc_info=True)
                    continue

            logger.info(f"Panel restoration complete: {len(self.pinned_panels)}/{len(active_panels)} panels restored")

        except Exception as e:
            logger.error(f"Error during panel restoration on startup: {e}", exc_info=True)

    def on_restore_panel_requested(self, panel_id: int):
        """Handle request to restore/open a saved panel"""
        logger.info(f"Restore panel requested: {panel_id}")

        if not self.controller:
            logger.error("No controller available")
            return

        # Get panel data from database
        panel_data = self.controller.pinned_panels_manager.get_panel_by_id(panel_id)
        if not panel_data:
            logger.error(f"Panel {panel_id} not found in database")
            QMessageBox.warning(
                self,
                "Error",
                f"Panel {panel_id} no encontrado en la base de datos"
            )
            return

        # Get category
        category = self.controller.get_category(str(panel_data['category_id']))
        if not category:
            logger.error(f"Category {panel_data['category_id']} not found")
            QMessageBox.warning(
                self,
                "Error",
                f"Categoria {panel_data['category_id']} no encontrada"
            )
            return

        # Create new floating panel with saved configuration
        restored_panel = FloatingPanel(
            config_manager=self.config_manager,
            list_controller=self.controller.list_controller if self.controller else None,
            panel_id=panel_id,
            custom_name=panel_data.get('custom_name'),
            custom_color=panel_data.get('custom_color')
        )

        # Connect signals
        restored_panel.item_clicked.connect(self.on_item_clicked)
        restored_panel.window_closed.connect(self.on_floating_panel_closed)
        restored_panel.pin_state_changed.connect(self.on_panel_pin_changed)
        restored_panel.customization_requested.connect(self.on_panel_customization_requested)

        # Load category
        restored_panel.load_category(category)

        # Restore position and size
        restored_panel.move(panel_data['x_position'], panel_data['y_position'])
        restored_panel.resize(panel_data['width'], panel_data['height'])

        # Apply custom styling
        restored_panel.apply_custom_styling()

        # Set as pinned
        restored_panel.is_pinned = True
        restored_panel.pin_button.setText("📍")
        restored_panel.minimize_button.setVisible(True)
        restored_panel.config_button.setVisible(True)

        # Restore minimized state if needed
        if panel_data.get('is_minimized'):
            restored_panel.toggle_minimize()

        # Restore filter configuration if available
        if panel_data.get('filter_config'):
            filter_config = self.controller.pinned_panels_manager._deserialize_filter_config(
                panel_data['filter_config']
            )
            if filter_config:
                restored_panel.apply_filter_config(filter_config)
                logger.debug(f"Applied saved filters to panel {panel_id}")

        # Add to pinned panels list
        self.pinned_panels.append(restored_panel)

        # Update last_opened in database
        self.controller.pinned_panels_manager.mark_panel_opened(panel_id)

        # Show panel
        restored_panel.show()

        logger.info(f"Panel {panel_id} restored successfully")

    def on_panel_deleted_from_window(self, panel_id: int):
        """Handle panel deletion from management window"""
        logger.info(f"Panel {panel_id} deleted from window - checking if currently open")

        # Check if this panel is currently open and close it
        for panel in self.pinned_panels[:]:
            if panel.panel_id == panel_id:
                logger.info(f"Closing currently open panel {panel_id}")
                self.pinned_panels.remove(panel)
                panel.close()
                panel.deleteLater()
                break

    def on_panel_updated_from_window(self, panel_id: int, custom_name: str, custom_color: str):
        """Handle panel update from management window"""
        logger.info(f"Panel {panel_id} updated from window")

        # Update currently open panel if found
        for panel in self.pinned_panels:
            if panel.panel_id == panel_id:
                logger.info(f"Updating currently open panel {panel_id}")
                panel.update_customization(custom_name=custom_name, custom_color=custom_color)
                break

    def closeEvent(self, event):
        """Override close event to minimize to tray instead of closing"""
        # Minimize to tray instead of closing
        event.ignore()
        self.hide_window()

        # Show notification on first minimize
        if self.tray_manager and self.is_visible:
            self.tray_manager.show_message(
                "Widget Sidebar",
                "La aplicación sigue ejecutándose en la bandeja del sistema"
            )
