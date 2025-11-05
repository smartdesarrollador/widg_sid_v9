"""
Simple Browser Window - Ventana flotante con navegador embebido
Author: Widget Sidebar Team
Date: 2025-11-02
"""

import sys
import logging
import ctypes
from ctypes import wintypes
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QApplication, QTabWidget, QTabBar, QMenu, QFrame
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QAction, QKeyEvent

logger = logging.getLogger(__name__)


# ===========================================================================
# Custom WebEngineView con menú contextual personalizado
# ===========================================================================
class CustomWebEngineView(QWebEngineView):
    """
    QWebEngineView personalizado con menú contextual que incluye
    opción para guardar texto seleccionado como snippet.
    """

    # Señal para solicitar guardar snippet
    save_snippet_requested = pyqtSignal(str)  # Emite el texto seleccionado

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_text = ""
        self.context_menu_pos = None  # Guardar posición del menú contextual

    def contextMenuEvent(self, event):
        """
        Sobrescribe el menú contextual para agregar opción de guardar snippet.
        """
        # Guardar la posición ANTES de la llamada asíncrona
        self.context_menu_pos = event.globalPos()

        # Obtener el texto seleccionado mediante JavaScript
        self.page().runJavaScript(
            "window.getSelection().toString();",
            lambda result: self._show_context_menu(result)
        )

    def _show_context_menu(self, selected_text):
        """
        Muestra el menú contextual con la opción de guardar snippet.

        Args:
            selected_text: Texto seleccionado obtenido via JavaScript
        """
        self.selected_text = selected_text.strip() if selected_text else ""

        # Crear menú contextual
        context_menu = QMenu(self)

        # Aplicar estilo oscuro
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #00d4ff;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3d3d3d;
                margin: 5px 0px;
            }
        """)

        # Si hay texto seleccionado, agregar opción de guardar snippet
        if self.selected_text:
            save_snippet_action = QAction("💾 Guardar como snippet", self)
            save_snippet_action.triggered.connect(
                lambda: self.save_snippet_requested.emit(self.selected_text)
            )
            context_menu.addAction(save_snippet_action)
            context_menu.addSeparator()

        # Agregar acciones estándar del navegador
        back_action = QAction("⬅ Atrás", self)
        back_action.triggered.connect(self.back)
        back_action.setEnabled(self.page().history().canGoBack())
        context_menu.addAction(back_action)

        forward_action = QAction("➡ Adelante", self)
        forward_action.triggered.connect(self.forward)
        forward_action.setEnabled(self.page().history().canGoForward())
        context_menu.addAction(forward_action)

        reload_action = QAction("🔄 Recargar", self)
        reload_action.triggered.connect(self.reload)
        context_menu.addAction(reload_action)

        context_menu.addSeparator()

        # Copiar (solo si hay texto seleccionado)
        if self.selected_text:
            copy_action = QAction("📋 Copiar", self)
            copy_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Copy))
            context_menu.addAction(copy_action)

        # Mostrar menú en la posición guardada del click derecho
        if self.context_menu_pos:
            context_menu.exec(self.context_menu_pos)


# ===========================================================================
# Search Bar Widget for Web Browser
# ===========================================================================
class BrowserSearchBar(QFrame):
    """
    Barra de búsqueda para el navegador web.
    Se muestra con Ctrl+F y permite buscar texto en la página actual.
    """

    # Señales
    closed = pyqtSignal()
    search_requested = pyqtSignal(str, bool)  # texto, forward (True=siguiente, False=anterior)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Configurar interfaz de la barra de búsqueda"""
        self.setObjectName("searchBar")
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Label
        label = QLabel("Buscar:")
        label.setStyleSheet("color: #00d4ff; font-weight: bold;")
        layout.addWidget(label)

        # Campo de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe para buscar...")
        self.search_input.returnPressed.connect(self.on_search_next)
        self.search_input.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.search_input)

        # Botón anterior
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(35)
        self.prev_btn.setToolTip("Anterior (Shift+F3)")
        self.prev_btn.clicked.connect(self.on_search_previous)
        layout.addWidget(self.prev_btn)

        # Botón siguiente
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(35)
        self.next_btn.setToolTip("Siguiente (F3 o Enter)")
        self.next_btn.clicked.connect(self.on_search_next)
        layout.addWidget(self.next_btn)

        # Label de resultados
        self.results_label = QLabel("")
        self.results_label.setStyleSheet("color: #00d4ff; font-size: 10px;")
        self.results_label.setMinimumWidth(80)
        layout.addWidget(self.results_label)

        # Botón cerrar
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(30)
        close_btn.setToolTip("Cerrar (Esc)")
        close_btn.clicked.connect(self.close_search)
        layout.addWidget(close_btn)

        # Estilos
        self.setStyleSheet("""
            #searchBar {
                background-color: #16213e;
                border: 2px solid #00d4ff;
                border-radius: 5px;
            }
            QLineEdit {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #00d4ff;
            }
            QPushButton {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16213e;
                border: 2px solid #00d4ff;
            }
            QPushButton:pressed {
                background-color: #00d4ff;
                color: #1a1a2e;
            }
        """)

    def on_text_changed(self, text):
        """Handler cuando cambia el texto de búsqueda"""
        if text:
            self.search_requested.emit(text, True)  # Buscar hacia adelante

    def on_search_next(self):
        """Buscar siguiente coincidencia"""
        text = self.search_input.text()
        if text:
            self.search_requested.emit(text, True)

    def on_search_previous(self):
        """Buscar anterior coincidencia"""
        text = self.search_input.text()
        if text:
            self.search_requested.emit(text, False)

    def close_search(self):
        """Cerrar barra de búsqueda"""
        self.closed.emit()
        self.hide()

    def show_and_focus(self):
        """Mostrar barra y dar foco al campo de búsqueda"""
        self.show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def keyPressEvent(self, event: QKeyEvent):
        """Manejar eventos de teclado"""
        if event.key() == Qt.Key.Key_Escape:
            self.close_search()
        elif event.key() == Qt.Key.Key_F3:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.on_search_previous()
            else:
                self.on_search_next()
        else:
            super().keyPressEvent(event)


# ===========================================================================
# Windows AppBar API Constants and Structures
# ===========================================================================
ABM_NEW = 0x00000000
ABM_REMOVE = 0x00000001
ABM_QUERYPOS = 0x00000002
ABM_SETPOS = 0x00000003
ABE_RIGHT = 2  # Lado derecho de la pantalla


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]


class SimpleBrowserWindow(QWidget):
    """
    Ventana flotante con navegador embebido QWebEngineView.

    Características:
    - Una sola instancia de QWebEngineView
    - Barra de navegación mínima (URL + Reload)
    - Ventana AppBar que reserva espacio en el escritorio
    - Ocupa toda la altura de la pantalla
    - Timeout de carga para prevenir cuelgues
    - Tema futurista simple
    """

    # Señales
    closed = pyqtSignal()

    def __init__(self, url: str = "https://www.google.com", db_manager=None, profile_manager=None):
        """
        Inicializa la ventana del navegador.

        Args:
            url: URL inicial a cargar
            db_manager: Instancia de DBManager para manejar marcadores y sesiones
            profile_manager: Instancia de BrowserProfileManager para perfiles persistentes
        """
        super().__init__()
        self.url = url
        self.db = db_manager
        self.profile_manager = profile_manager
        self.appbar_registered = False  # Estado del AppBar

        # Variables para redimensionamiento
        self.resizing = False
        self.resize_edge_width = 10  # Ancho del área sensible en el borde izquierdo
        self.resize_start_pos = None
        self.resize_start_width = None
        self.resize_start_x = None

        # Sistema de pestañas
        self.tabs = []  # Lista de QWebEngineView (una por pestaña)
        self.tab_widget = None  # QTabWidget
        self.is_loading = False  # Estado de carga

        # Perfil de navegador persistente
        self.web_profile = None
        if self.profile_manager:
            self.web_profile = self.profile_manager.get_or_create_profile()
            if self.web_profile:
                logger.info("Perfil persistente cargado - cookies y sesiones se guardarán")
            else:
                logger.warning("No se pudo cargar perfil persistente - usando perfil temporal")

        # Gestor de sesiones
        self.session_manager = None
        if self.db:
            from src.core.browser_session_manager import BrowserSessionManager
            self.session_manager = BrowserSessionManager(self.db)
            logger.info("BrowserSessionManager inicializado")

        logger.info(f"Inicializando SimpleBrowserWindow con URL: {url}")

        self._setup_window()
        self._setup_ui()
        self._setup_timer()
        self._apply_styles()

        # Habilitar rastreo de mouse para detectar hover en el borde
        self.setMouseTracking(True)

        # Restaurar última sesión si existe
        if self.session_manager:
            QTimer.singleShot(200, self._restore_last_session)

        # Cargar URL inicial de forma asíncrona si no se restaura sesión
        if not self.session_manager:
            QTimer.singleShot(100, lambda: self.load_url(self.url))

    def _setup_window(self):
        """Configura propiedades de la ventana."""
        # Ventana flotante que permanece arriba
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        self.setWindowTitle("Widget Sidebar Browser")

        # Calcular tamaño para ocupar toda la altura de la pantalla (excepto taskbar)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Altura: 100% del área disponible (excluye automáticamente la barra de tareas)
        window_height = screen_geometry.height()
        window_width = 500  # Ancho inicial (redimensionable)

        self.resize(window_width, window_height)

    def _setup_ui(self):
        """Configura la interfaz de usuario con sistema de pestañas."""
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de navegación principal
        nav_bar = self._create_nav_bar()
        main_layout.addLayout(nav_bar)

        # Barra de herramientas secundaria (marcadores, sesiones, etc)
        tools_bar = self._create_tools_bar()
        main_layout.addLayout(tools_bar)

        # Barra de búsqueda (inicialmente oculta)
        self.search_bar = BrowserSearchBar(self)
        self.search_bar.hide()
        self.search_bar.search_requested.connect(self.on_search_text)
        self.search_bar.closed.connect(self.on_search_closed)
        main_layout.addWidget(self.search_bar)

        # QTabWidget para pestañas
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)  # Permitir cerrar pestañas
        self.tab_widget.setMovable(True)  # Permitir mover pestañas
        self.tab_widget.setDocumentMode(True)  # Apariencia más limpia

        # Conectar señales del tab widget
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab)

        main_layout.addWidget(self.tab_widget)

        # Botón "+" para agregar nueva pestaña (colocado en la esquina del tab widget)
        self.tab_widget.setCornerWidget(self._create_new_tab_button())

        self.setLayout(main_layout)

        # Crear primera pestaña con la URL inicial
        self.add_new_tab(self.url, "Nueva pestaña")

    def _create_nav_bar(self) -> QHBoxLayout:
        """Crea la barra de navegación principal."""
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(5)

        # Botón atrás
        self.back_btn = QPushButton("◀")
        self.back_btn.setFixedWidth(40)
        self.back_btn.setToolTip("Atrás")
        self.back_btn.clicked.connect(self.go_back)
        nav_layout.addWidget(self.back_btn)

        # Botón adelante
        self.forward_btn = QPushButton("▶")
        self.forward_btn.setFixedWidth(40)
        self.forward_btn.setToolTip("Adelante")
        self.forward_btn.clicked.connect(self.go_forward)
        nav_layout.addWidget(self.forward_btn)

        # Botón home
        self.home_btn = QPushButton("⌂")
        self.home_btn.setFixedWidth(40)
        self.home_btn.setToolTip("Inicio (Speed Dial)")
        self.home_btn.clicked.connect(self.go_home)
        nav_layout.addWidget(self.home_btn)

        # Label de estado
        self.status_label = QLabel("●")
        self.status_label.setFixedWidth(20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.status_label)

        # Campo URL
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Ingresa una URL...")
        self.url_bar.setText(self.url)
        self.url_bar.returnPressed.connect(self._on_url_entered)
        nav_layout.addWidget(self.url_bar)

        # Botón copiar URL
        self.copy_url_btn = QPushButton("📋")
        self.copy_url_btn.setFixedWidth(40)
        self.copy_url_btn.setToolTip("Copiar URL al portapapeles")
        self.copy_url_btn.clicked.connect(self.copy_current_url)
        nav_layout.addWidget(self.copy_url_btn)

        # Botón reload
        self.reload_btn = QPushButton("↻")
        self.reload_btn.setFixedWidth(40)
        self.reload_btn.setToolTip("Recargar página")
        self.reload_btn.clicked.connect(self.reload_page)
        nav_layout.addWidget(self.reload_btn)

        # Botón listado de pestañas
        self.tabs_list_btn = QPushButton("☰")
        self.tabs_list_btn.setFixedWidth(40)
        self.tabs_list_btn.setToolTip("Ver todas las pestañas")
        self.tabs_list_btn.clicked.connect(self.show_tabs_menu)
        nav_layout.addWidget(self.tabs_list_btn)

        # Botón cerrar
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(40)
        self.close_btn.setToolTip("Cerrar navegador")
        self.close_btn.clicked.connect(self.close)
        nav_layout.addWidget(self.close_btn)

        return nav_layout

    def _create_tools_bar(self) -> QHBoxLayout:
        """Crea la barra de herramientas secundaria (marcadores, sesiones, etc)."""
        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(5, 0, 5, 5)
        tools_layout.setSpacing(5)

        # Sección: Marcadores
        bookmarks_label = QLabel("Marcadores:")
        bookmarks_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 11px;")
        tools_layout.addWidget(bookmarks_label)

        # Botón marcador (estrella)
        self.bookmark_btn = QPushButton("☆")
        self.bookmark_btn.setFixedWidth(35)
        self.bookmark_btn.setFixedHeight(30)
        self.bookmark_btn.setToolTip("Agregar a marcadores")
        self.bookmark_btn.clicked.connect(self.toggle_bookmark)
        tools_layout.addWidget(self.bookmark_btn)

        # Botón ver marcadores
        self.bookmarks_list_btn = QPushButton("≡")
        self.bookmarks_list_btn.setFixedWidth(35)
        self.bookmarks_list_btn.setFixedHeight(30)
        self.bookmarks_list_btn.setToolTip("Ver marcadores")
        self.bookmarks_list_btn.clicked.connect(self.show_bookmarks_panel)
        tools_layout.addWidget(self.bookmarks_list_btn)

        # Separador
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #0f3460;")
        separator1.setFixedWidth(15)
        separator1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tools_layout.addWidget(separator1)

        # Sección: Sesiones
        sessions_label = QLabel("Sesiones:")
        sessions_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 11px;")
        tools_layout.addWidget(sessions_label)

        # Botón guardar sesión
        self.save_session_btn = QPushButton("💾")
        self.save_session_btn.setFixedWidth(35)
        self.save_session_btn.setFixedHeight(30)
        self.save_session_btn.setToolTip("Guardar sesión actual")
        self.save_session_btn.clicked.connect(self.save_current_session)
        tools_layout.addWidget(self.save_session_btn)

        # Botón gestionar sesiones
        self.manage_sessions_btn = QPushButton("🗂️")
        self.manage_sessions_btn.setFixedWidth(35)
        self.manage_sessions_btn.setFixedHeight(30)
        self.manage_sessions_btn.setToolTip("Gestionar sesiones")
        self.manage_sessions_btn.clicked.connect(self.show_session_manager)
        tools_layout.addWidget(self.manage_sessions_btn)

        # Separador
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #0f3460;")
        separator2.setFixedWidth(15)
        separator2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tools_layout.addWidget(separator2)

        # Botón guardar URL como item
        self.save_url_btn = QPushButton("💾📌")
        self.save_url_btn.setFixedWidth(45)
        self.save_url_btn.setFixedHeight(30)
        self.save_url_btn.setToolTip("Guardar URL actual como item")
        self.save_url_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #000000;
                border: none;
                border-radius: 3px;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b8d4;
            }
            QPushButton:pressed {
                background-color: #0091a6;
            }
        """)
        self.save_url_btn.clicked.connect(self.save_url_as_item)
        tools_layout.addWidget(self.save_url_btn)

        # Espacio flexible
        tools_layout.addStretch()

        return tools_layout

    def _setup_timer(self):
        """Configura timer de timeout para prevenir cuelgues."""
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._on_load_timeout)

    def _apply_styles(self):
        """Aplica estilos futuristas simples."""
        self.setStyleSheet("""
            SimpleBrowserWindow {
                background-color: #1a1a2e;
                border: 2px solid #00d4ff;
            }

            QLineEdit {
                background-color: #16213e;
                color: #00d4ff;
                border: 1px solid #0f3460;
                border-radius: 5px;
                padding: 5px;
                font-size: 11px;
            }

            QLineEdit:focus {
                border: 1px solid #00d4ff;
            }

            QPushButton {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #16213e;
                border: 2px solid #00d4ff;
            }

            QPushButton:pressed {
                background-color: #00d4ff;
                color: #1a1a2e;
            }

            QLabel {
                color: #00ff00;
                font-size: 14px;
            }

            /* Estilos para QTabWidget */
            QTabWidget::pane {
                background-color: #1a1a2e;
                border: 1px solid #0f3460;
                border-top: 2px solid #00d4ff;
            }

            QTabBar::tab {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 12px;
                margin-right: 2px;
                font-size: 11px;
                min-width: 100px;
                max-width: 200px;
            }

            QTabBar::tab:selected {
                background-color: #16213e;
                border: 2px solid #00d4ff;
                border-bottom: none;
                color: #00d4ff;
                font-weight: bold;
            }

            QTabBar::tab:hover:!selected {
                background-color: #16213e;
                border: 1px solid #00d4ff;
            }

            QTabBar::close-button {
                image: none;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px 2px;
            }

            QTabBar::close-button:hover {
                background-color: #ff0000;
                border-radius: 3px;
            }

            /* Botón de cerrar pestaña personalizado */
            QTabBar QToolButton {
                background-color: transparent;
                border: none;
                color: #00d4ff;
            }

            QTabBar QToolButton:hover {
                background-color: rgba(255, 0, 0, 0.5);
                border-radius: 3px;
            }
        """)

    # ==================== Sistema de Pestañas ====================

    def _create_new_tab_button(self) -> QPushButton:
        """Crea el botón '+' para agregar nuevas pestañas."""
        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedSize(30, 30)
        new_tab_btn.setToolTip("Nueva pestaña")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab("https://www.google.com", "Nueva pestaña"))
        new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16213e;
                border: 2px solid #00d4ff;
            }
        """)
        return new_tab_btn

    def add_new_tab(self, url: str = "https://www.google.com", title: str = "Nueva pestaña"):
        """
        Agrega una nueva pestaña al navegador.

        Args:
            url: URL inicial de la pestaña
            title: Título de la pestaña
        """
        # Crear nuevo CustomWebEngineView con perfil persistente
        browser = CustomWebEngineView()

        # Si tenemos perfil persistente, crear página con ese perfil
        if self.web_profile:
            page = QWebEnginePage(self.web_profile, browser)
            browser.setPage(page)
            logger.debug("Pestaña creada con perfil persistente")
        else:
            logger.debug("Pestaña creada con perfil temporal (por defecto)")

        # Configurar el navegador
        settings = browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)

        # Conectar señales
        browser.loadStarted.connect(lambda: self._on_load_started())
        browser.loadProgress.connect(lambda progress: self._on_load_progress(progress))
        browser.loadFinished.connect(lambda success: self._on_load_finished(success))
        browser.urlChanged.connect(lambda url: self._on_url_changed(url))
        browser.titleChanged.connect(lambda title: self._on_title_changed(title))
        browser.save_snippet_requested.connect(self.save_snippet_as_item)

        # Agregar a la lista de pestañas
        self.tabs.append(browser)

        # Agregar pestaña al widget
        tab_index = self.tab_widget.addTab(browser, title)

        # Activar la nueva pestaña
        self.tab_widget.setCurrentIndex(tab_index)

        # Cargar URL o Speed Dial
        if url and url != "https://www.google.com":
            browser.setUrl(QUrl(url if url.startswith(('http://', 'https://')) else 'https://' + url))
        else:
            # Cargar Speed Dial por defecto en nuevas pestañas
            QTimer.singleShot(100, lambda: self._load_speed_dial_in_browser(browser))

        logger.info(f"Nueva pestaña agregada: {title} ({url})")

    def _on_tab_changed(self, index: int):
        """Handler cuando cambia la pestaña activa."""
        if index >= 0 and index < len(self.tabs):
            browser = self.tabs[index]
            # Actualizar barra de URL con la URL de la pestaña activa
            current_url = browser.url().toString()
            if current_url:
                self.url_bar.setText(current_url)
            logger.debug(f"Pestaña activa cambiada a índice {index}")

    def _on_close_tab(self, index: int):
        """
        Handler para cerrar una pestaña.

        Args:
            index: Índice de la pestaña a cerrar
        """
        if self.tab_widget.count() == 1:
            # Si es la última pestaña, no permitir cerrarla (o cerrar la ventana)
            logger.warning("No se puede cerrar la última pestaña")
            return

        # Remover de la lista
        if 0 <= index < len(self.tabs):
            browser = self.tabs.pop(index)
            browser.deleteLater()

        # Remover del widget
        self.tab_widget.removeTab(index)

        logger.info(f"Pestaña cerrada en índice {index}")

    def get_current_browser(self) -> QWebEngineView:
        """
        Obtiene el QWebEngineView de la pestaña actualmente activa.

        Returns:
            QWebEngineView de la pestaña activa, o None si no hay pestañas
        """
        current_index = self.tab_widget.currentIndex()
        if 0 <= current_index < len(self.tabs):
            return self.tabs[current_index]
        return None

    # ==================== Métodos Públicos ====================

    def load_url(self, url: str):
        """
        Carga una URL en la pestaña activa.

        Args:
            url: URL a cargar
        """
        browser = self.get_current_browser()
        if not browser:
            return

        # Asegurar que la URL tenga protocolo
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Cargando URL: {url}")

        # Iniciar timer de timeout (10 segundos)
        self.load_timer.start(10000)

        # Cargar URL en la pestaña activa
        browser.setUrl(QUrl(url))

    def reload_page(self):
        """Recarga la página de la pestaña activa."""
        browser = self.get_current_browser()
        if browser:
            logger.info("Recargando página")
            browser.reload()

    def copy_current_url(self):
        """Copia la URL actual al portapapeles."""
        try:
            import pyperclip

            # Obtener URL actual del campo de texto
            current_url = self.url_bar.text()

            if current_url:
                # Copiar al portapapeles
                pyperclip.copy(current_url)
                logger.info(f"URL copiada al portapapeles: {current_url}")

                # Feedback visual: cambiar icono temporalmente
                original_text = self.copy_url_btn.text()
                self.copy_url_btn.setText("✓")
                self.copy_url_btn.setStyleSheet("color: #00ff00;")

                # Restaurar después de 1 segundo
                QTimer.singleShot(1000, lambda: self._restore_copy_button(original_text))
            else:
                logger.warning("No hay URL para copiar")

        except Exception as e:
            logger.error(f"Error al copiar URL: {e}", exc_info=True)

    def _restore_copy_button(self, original_text):
        """Restaura el botón de copiar a su estado original."""
        self.copy_url_btn.setText(original_text)
        self.copy_url_btn.setStyleSheet("")

    def go_back(self):
        """Navega hacia atrás en el historial de la pestaña activa."""
        browser = self.get_current_browser()
        if browser and browser.history().canGoBack():
            logger.info("Navegando hacia atrás")
            browser.back()
        else:
            logger.debug("No se puede navegar hacia atrás")

    def go_forward(self):
        """Navega hacia adelante en el historial de la pestaña activa."""
        browser = self.get_current_browser()
        if browser and browser.history().canGoForward():
            logger.info("Navegando hacia adelante")
            browser.forward()
        else:
            logger.debug("No se puede navegar hacia adelante")

    def go_home(self):
        """Navega a la página de inicio (Speed Dial)."""
        logger.info("Navegando a Speed Dial (Home)")
        self.load_speed_dial()

    def load_speed_dial(self):
        """Carga la página Speed Dial en la pestaña activa."""
        if not self.db:
            logger.warning("No hay DBManager disponible para Speed Dial")
            return

        try:
            # Importar el generador de Speed Dial
            from src.core.speed_dial_generator import SpeedDialGenerator

            # Generar HTML del Speed Dial
            generator = SpeedDialGenerator(self.db)
            html_content = generator.generate_html()

            # Cargar el HTML en la pestaña activa
            browser = self.get_current_browser()
            if browser:
                browser.setHtml(html_content)
                self.url_bar.setText("speed-dial://home")
                logger.info("Speed Dial cargado")

        except Exception as e:
            logger.error(f"Error al cargar Speed Dial: {e}")

    def _load_speed_dial_in_browser(self, browser: QWebEngineView):
        """
        Carga Speed Dial en un browser específico (helper para nuevas pestañas).

        Args:
            browser: Instancia de QWebEngineView donde cargar el Speed Dial
        """
        if not self.db:
            return

        try:
            from src.core.speed_dial_generator import SpeedDialGenerator

            generator = SpeedDialGenerator(self.db)
            html_content = generator.generate_html()
            browser.setHtml(html_content)
            logger.debug("Speed Dial cargado en nueva pestaña")

        except Exception as e:
            logger.error(f"Error al cargar Speed Dial en nueva pestaña: {e}")

    def open_speed_dial_dialog(self):
        """Abre el dialog para agregar un nuevo speed dial."""
        if not self.db:
            logger.warning("No hay DBManager disponible")
            return

        try:
            from src.views.speed_dial_dialog import SpeedDialDialog

            dialog = SpeedDialDialog(self.db, parent=self)
            dialog.speed_dial_added.connect(self._on_speed_dial_added)

            if dialog.exec():
                logger.info("Dialog de speed dial cerrado con éxito")

        except Exception as e:
            logger.error(f"Error al abrir dialog de speed dial: {e}")

    def _on_speed_dial_added(self, speed_dial_data: dict):
        """Handler cuando se agrega un nuevo speed dial."""
        logger.info(f"Nuevo speed dial agregado: {speed_dial_data['title']}")
        # Recargar la página de Speed Dial para mostrar el nuevo
        self.load_speed_dial()

    def toggle_bookmark(self):
        """Agrega o quita la página actual de marcadores."""
        if not self.db:
            logger.warning("No hay DBManager disponible para marcadores")
            return

        browser = self.get_current_browser()
        if not browser:
            return

        current_url = browser.url().toString()
        current_title = browser.title() or "Nueva pestaña"

        # Verificar si ya existe el marcador
        if self.db.is_bookmark_exists(current_url):
            # Eliminar marcador
            bookmarks = self.db.get_bookmarks()
            for bookmark in bookmarks:
                if bookmark['url'] == current_url:
                    self.db.delete_bookmark(bookmark['id'])
                    logger.info(f"Marcador eliminado: {current_title}")
                    self.update_bookmark_button()
                    return
        else:
            # Agregar marcador
            bookmark_id = self.db.add_bookmark(current_title, current_url)
            if bookmark_id:
                logger.info(f"Marcador agregado: {current_title}")
                self.update_bookmark_button()

    def update_bookmark_button(self):
        """Actualiza el icono del botón de marcador según si la página actual está guardada."""
        if not self.db:
            return

        browser = self.get_current_browser()
        if not browser:
            return

        current_url = browser.url().toString()

        if self.db.is_bookmark_exists(current_url):
            self.bookmark_btn.setText("★")
            self.bookmark_btn.setToolTip("Quitar de marcadores")
        else:
            self.bookmark_btn.setText("☆")
            self.bookmark_btn.setToolTip("Agregar a marcadores")

    def show_bookmarks_panel(self):
        """Muestra el panel flotante con la lista de marcadores."""
        if not self.db:
            logger.warning("No hay DBManager disponible para marcadores")
            return

        # Importar aquí para evitar importación circular
        from src.views.bookmarks_panel import BookmarksPanel

        # Crear panel si no existe
        if not hasattr(self, 'bookmarks_panel') or self.bookmarks_panel is None:
            self.bookmarks_panel = BookmarksPanel(self.db, self)
            self.bookmarks_panel.bookmark_selected.connect(self._on_bookmark_selected)

        # Mostrar y posicionar el panel
        self.bookmarks_panel.refresh_bookmarks()
        self.bookmarks_panel.show()
        self.bookmarks_panel.raise_()
        self.bookmarks_panel.activateWindow()

    def _on_bookmark_selected(self, url: str):
        """Handler cuando se selecciona un marcador del panel."""
        logger.info(f"Navegando a marcador: {url}")
        self.load_url(url)

    def show_tabs_menu(self):
        """Muestra un menú desplegable con todas las pestañas abiertas."""
        if len(self.tabs) == 0:
            logger.debug("No hay pestañas para mostrar")
            return

        # Crear menú
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
                border: 2px solid #00d4ff;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: #00d4ff;
                padding: 8px 20px;
                border-radius: 3px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #0f3460;
                border: 1px solid #00d4ff;
            }
            QMenu::item:disabled {
                background-color: #16213e;
                color: #ffffff;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background-color: #0f3460;
                margin: 5px 0px;
            }
        """)

        # Obtener índice de pestaña activa
        current_index = self.tab_widget.currentIndex()

        # Agregar cada pestaña al menú
        for i, browser in enumerate(self.tabs):
            # Obtener título y URL de la pestaña
            title = browser.title() or "Nueva pestaña"
            url = browser.url().toString()

            # Limitar el título a 50 caracteres
            if len(title) > 50:
                title = title[:47] + "..."

            # Crear texto del item del menú
            if i == current_index:
                # Pestaña activa: marcar con ✓ y deshabilitarla
                item_text = f"✓ {title}"
                action = menu.addAction(item_text)
                action.setEnabled(False)  # Deshabilitar pestaña activa
            else:
                # Otras pestañas
                item_text = f"  {title}"
                action = menu.addAction(item_text)
                action.setData(i)  # Guardar el índice en los datos de la acción
                action.triggered.connect(lambda checked, idx=i: self._switch_to_tab(idx))

            # Agregar tooltip con la URL completa
            action.setToolTip(url)

        # Agregar separador y opción de cerrar todas las pestañas (excepto activa)
        if len(self.tabs) > 1:
            menu.addSeparator()
            close_others_action = menu.addAction("Cerrar otras pestañas")
            close_others_action.triggered.connect(self._close_other_tabs)

        # Mostrar el menú debajo del botón
        button_pos = self.tabs_list_btn.mapToGlobal(self.tabs_list_btn.rect().bottomLeft())
        menu.exec(button_pos)

        logger.debug(f"Menú de pestañas mostrado con {len(self.tabs)} pestañas")

    def _switch_to_tab(self, index: int):
        """
        Cambia a una pestaña específica.

        Args:
            index: Índice de la pestaña
        """
        if 0 <= index < len(self.tabs):
            self.tab_widget.setCurrentIndex(index)
            logger.debug(f"Cambiado a pestaña {index}")

    def _close_other_tabs(self):
        """Cierra todas las pestañas excepto la activa."""
        current_index = self.tab_widget.currentIndex()

        # Cerrar pestañas desde el final hacia el principio (para no afectar índices)
        for i in range(len(self.tabs) - 1, -1, -1):
            if i != current_index:
                self._on_close_tab(i)

        logger.info(f"Cerradas todas las pestañas excepto la activa")

    # ==================== Slots ====================

    def _on_url_entered(self):
        """Handler cuando se presiona Enter en el campo URL."""
        url = self.url_bar.text().strip()
        if url:
            self.load_url(url)

    def _on_load_started(self):
        """Handler cuando inicia la carga de la página."""
        self.is_loading = True
        self.status_label.setText("●")
        self.status_label.setStyleSheet("color: #ffaa00;")  # Naranja
        self.reload_btn.setEnabled(False)
        logger.debug("Carga iniciada")

    def _on_load_progress(self, progress: int):
        """Handler del progreso de carga."""
        logger.debug(f"Progreso de carga: {progress}%")

    def _on_load_finished(self, success: bool):
        """Handler cuando termina la carga."""
        self.is_loading = False
        self.load_timer.stop()
        self.reload_btn.setEnabled(True)

        if success:
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #00ff00;")  # Verde
            logger.info("Página cargada exitosamente")
        else:
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #ff0000;")  # Rojo
            logger.warning("Error al cargar la página")

    def _on_url_changed(self, url: QUrl):
        """Handler cuando cambia la URL."""
        self.url_bar.setText(url.toString())
        self.update_bookmark_button()  # Actualizar estado del botón de marcador
        logger.debug(f"URL cambiada a: {url.toString()}")

    def _on_title_changed(self, title: str):
        """
        Handler cuando cambia el título de una página.
        Actualiza el título de la pestaña correspondiente.
        También detecta señales especiales para Speed Dial.
        """
        # Detectar señal especial para agregar Speed Dial
        if title == '__SPEED_DIAL_ADD_NEW__':
            logger.debug("Señal detectada para agregar nuevo Speed Dial")
            QTimer.singleShot(50, self.open_speed_dial_dialog)
            return

        # Encontrar qué pestaña emitió la señal
        sender_browser = self.sender()
        if sender_browser in self.tabs:
            index = self.tabs.index(sender_browser)
            # Limitar el título a 20 caracteres para que no sea muy largo
            short_title = title[:20] + "..." if len(title) > 20 else title
            self.tab_widget.setTabText(index, short_title or "Nueva pestaña")
            logger.debug(f"Título de pestaña {index} actualizado a: {short_title}")

    def _on_load_timeout(self):
        """Handler para timeout de carga."""
        if self.is_loading:
            logger.warning("Timeout de carga alcanzado")
            browser = self.get_current_browser()
            if browser:
                browser.stop()
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #ff0000;")
            self.reload_btn.setEnabled(True)

    # ==================== Posicionamiento ====================

    def position_near_sidebar(self, sidebar_window):
        """
        Posiciona la ventana del navegador al lado del sidebar.
        Ocupa toda la altura disponible de la pantalla.

        Args:
            sidebar_window: Referencia a la ventana del sidebar (MainWindow)
        """
        # Obtener geometría del sidebar
        sidebar_x = sidebar_window.x()

        # Obtener área disponible de la pantalla (excluye taskbar)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Posicionar a la izquierda del sidebar con un gap de 10px
        panel_x = sidebar_x - self.width() - 10  # 10px gap
        panel_y = screen_geometry.y()  # Inicio del área disponible (normalmente 0)

        # Ajustar altura para que ocupe todo el espacio disponible
        panel_height = screen_geometry.height()

        # Aplicar posición y tamaño
        self.setGeometry(int(panel_x), panel_y, self.width(), panel_height)
        logger.debug(f"Navegador posicionado en ({panel_x}, {panel_y}) con altura {panel_height}px")

    # ==================== Redimensionamiento ====================

    def is_on_left_edge(self, pos):
        """
        Verifica si el mouse está en el borde izquierdo para redimensionar.

        Args:
            pos: Posición del mouse (QPoint)

        Returns:
            bool: True si está en el borde izquierdo
        """
        return pos.x() <= self.resize_edge_width

    def mouseMoveEvent(self, event):
        """Maneja el movimiento del mouse para redimensionamiento."""
        pos = event.pos()

        if self.resizing:
            # Redimensionar mientras se arrastra
            delta_x = event.globalPosition().x() - self.resize_start_pos.x()
            new_width = max(300, self.resize_start_width - int(delta_x))  # Mínimo 300px
            new_x = self.resize_start_x + (self.resize_start_width - new_width)

            # Aplicar nuevo tamaño y posición
            self.setGeometry(int(new_x), self.y(), new_width, self.height())
            event.accept()
        elif self.is_on_left_edge(pos):
            # Cambiar cursor a resize horizontal
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            # Restaurar cursor normal
            self.setCursor(Qt.CursorShape.ArrowCursor)

        event.accept()

    def mousePressEvent(self, event):
        """Inicia el redimensionamiento al hacer click en el borde."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            if self.is_on_left_edge(pos):
                # Iniciar redimensionamiento
                self.resizing = True
                self.resize_start_pos = event.globalPosition()
                self.resize_start_width = self.width()
                self.resize_start_x = self.x()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Finaliza el redimensionamiento."""
        if event.button() == Qt.MouseButton.LeftButton and self.resizing:
            self.resizing = False

            # Actualizar AppBar con el nuevo tamaño
            if self.appbar_registered:
                self.unregister_appbar()
                self.register_appbar()
                logger.info(f"AppBar actualizado - nuevo ancho: {self.width()}px")

            event.accept()
            return

        super().mouseReleaseEvent(event)

    # ==================== AppBar Management ====================

    def register_appbar(self):
        """
        Registra la ventana como AppBar de Windows para reservar espacio permanentemente.
        Esto empuja las ventanas maximizadas para que no cubran el navegador.
        """
        try:
            if sys.platform != 'win32':
                logger.warning("AppBar solo funciona en Windows")
                return

            if self.appbar_registered:
                logger.debug("AppBar ya está registrada")
                return

            # Obtener handle de la ventana
            hwnd = int(self.winId())

            # Obtener geometría de la pantalla
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()

            # Crear estructura APPBARDATA
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = hwnd
            abd.uCallbackMessage = 0
            abd.uEdge = ABE_RIGHT  # Lado derecho de la pantalla (junto al sidebar)

            # Definir el rectángulo del AppBar (para ABE_RIGHT: desde el navegador hasta el borde derecho)
            abd.rc.left = self.x()  # Borde izquierdo del navegador
            abd.rc.top = screen_geometry.y()
            abd.rc.right = screen_geometry.x() + screen_geometry.width()  # Borde derecho de la pantalla
            abd.rc.bottom = screen_geometry.y() + screen_geometry.height()

            # Registrar el AppBar
            result = ctypes.windll.shell32.SHAppBarMessage(ABM_NEW, ctypes.byref(abd))
            if result:
                logger.info("Navegador registrado como AppBar - espacio reservado en el escritorio")
                self.appbar_registered = True

                # Consultar y establecer posición para reservar espacio
                ctypes.windll.shell32.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
                ctypes.windll.shell32.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
            else:
                logger.warning("No se pudo registrar el navegador como AppBar")

        except Exception as e:
            logger.error(f"Error al registrar navegador como AppBar: {e}")

    def unregister_appbar(self):
        """
        Desregistra la ventana como AppBar al cerrar u ocultar.
        Esto libera el espacio reservado en el escritorio.
        """
        try:
            if not self.appbar_registered:
                return

            # Obtener handle de la ventana
            hwnd = int(self.winId())

            # Crear estructura APPBARDATA
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = hwnd

            # Desregistrar el AppBar
            ctypes.windll.shell32.SHAppBarMessage(ABM_REMOVE, ctypes.byref(abd))
            self.appbar_registered = False
            logger.info("Navegador desregistrado como AppBar - espacio liberado")

        except Exception as e:
            logger.error(f"Error al desregistrar navegador como AppBar: {e}")

    # ==================== Session Management ====================

    def _get_current_tabs_data(self) -> list:
        """
        Obtiene los datos de todas las pestañas actuales.

        Returns:
            Lista de diccionarios con datos de pestañas
        """
        tabs_data = []

        for i, browser in enumerate(self.tabs):
            url = browser.url().toString()
            title = browser.title() or "Nueva pestaña"
            is_active = (i == self.tab_widget.currentIndex())

            tabs_data.append({
                'url': url,
                'title': title,
                'position': i,
                'is_active': is_active
            })

        return tabs_data

    def save_current_session(self):
        """Guarda la sesión actual con un nombre personalizado."""
        if not self.session_manager:
            logger.warning("Session manager no disponible")
            return

        if len(self.tabs) == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Sin pestañas",
                "No hay pestañas para guardar en la sesión"
            )
            return

        try:
            from src.views.save_session_dialog import SaveSessionDialog

            dialog = SaveSessionDialog(self)
            if dialog.exec():
                session_name = dialog.get_session_name()
                tabs_data = self._get_current_tabs_data()

                session_id = self.session_manager.save_current_session(
                    tabs_data,
                    name=session_name,
                    is_auto_save=False
                )

                if session_id:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        "Sesión Guardada",
                        f"Sesión '{session_name}' guardada con {len(tabs_data)} pestaña(s)"
                    )
                    logger.info(f"Sesión guardada manualmente: {session_name}")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo guardar la sesión"
                    )

        except Exception as e:
            logger.error(f"Error al guardar sesión: {e}")

    def show_session_manager(self):
        """Muestra el dialog de gestión de sesiones."""
        if not self.session_manager:
            logger.warning("Session manager no disponible")
            return

        try:
            from src.views.session_dialog import SessionDialog

            dialog = SessionDialog(self.session_manager, self)
            dialog.session_restored.connect(self._restore_session_tabs)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error al mostrar gestor de sesiones: {e}")

    def save_url_as_item(self):
        """Guarda la URL actual como un item en una categoría."""
        if not self.db:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "No hay conexión a la base de datos"
            )
            return

        try:
            # Obtener navegador actual
            browser = self.get_current_browser()
            if not browser:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Sin pestaña",
                    "No hay ninguna pestaña activa"
                )
                return

            # Obtener URL y título actual
            current_url = browser.url().toString()
            page_title = browser.title() or "Sin título"

            if not current_url or current_url == "about:blank":
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Sin URL",
                    "No hay URL para guardar"
                )
                return

            # Obtener categorías de la base de datos
            from models.category import Category
            categories_data = self.db.get_categories()

            # Mapear correctamente los datos (id -> category_id)
            categories = []
            for cat in categories_data:
                category = Category(
                    category_id=cat['id'],
                    name=cat['name'],
                    icon=cat.get('icon', ''),
                    order_index=cat.get('order_index', 0),
                    is_active=cat.get('is_active', True),
                    is_predefined=cat.get('is_predefined', False),
                    color=cat.get('color'),
                    badge=cat.get('badge')
                )
                categories.append(category)

            if not categories:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Sin categorías",
                    "No hay categorías disponibles. Crea una categoría primero."
                )
                return

            # Mostrar dialog
            from src.views.dialogs.save_url_dialog import SaveUrlDialog

            dialog = SaveUrlDialog(
                current_url=current_url,
                page_title=page_title,
                categories=categories,
                parent=self
            )

            if dialog.exec():
                # Obtener datos del dialog
                data = dialog.get_data()

                # Guardar item en la base de datos
                item_id = self.db.add_item(
                    category_id=data['category_id'],
                    label=data['label'],
                    content=data['content'],
                    item_type=data['type'],
                    description=data['description'],
                    tags=data['tags']
                )

                if item_id:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        "Éxito",
                        f"URL guardada exitosamente como item:\n\n{data['label']}"
                    )
                    logger.info(f"URL guardada como item: {data['label']} (ID: {item_id})")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo guardar el item en la base de datos"
                    )

        except Exception as e:
            logger.error(f"Error al guardar URL como item: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar URL:\n{str(e)}"
            )

    def save_snippet_as_item(self, selected_text: str):
        """
        Guarda el texto seleccionado como snippet (item CODE o TEXT).

        Args:
            selected_text: Texto seleccionado del navegador
        """
        try:
            if not self.db:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    "No hay conexión a la base de datos"
                )
                return

            if not selected_text or not selected_text.strip():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Sin texto",
                    "No hay texto seleccionado para guardar"
                )
                return

            # Obtener categorías de la base de datos
            from models.category import Category
            categories_data = self.db.get_categories()

            # Mapear correctamente los datos (id -> category_id)
            categories = []
            for cat in categories_data:
                category = Category(
                    category_id=cat['id'],
                    name=cat['name'],
                    icon=cat.get('icon', ''),
                    order_index=cat.get('order_index', 0),
                    is_active=cat.get('is_active', True),
                    is_predefined=cat.get('is_predefined', False),
                    color=cat.get('color'),
                    badge=cat.get('badge')
                )
                categories.append(category)

            if not categories:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Sin categorías",
                    "No hay categorías disponibles. Crea una categoría primero."
                )
                return

            # Mostrar dialog
            from src.views.dialogs.save_snippet_dialog import SaveSnippetDialog

            dialog = SaveSnippetDialog(
                selected_text=selected_text,
                categories=categories,
                parent=self
            )

            if dialog.exec():
                # Obtener datos del dialog
                data = dialog.get_data()

                # Guardar item en la base de datos
                item_id = self.db.add_item(
                    category_id=data['category_id'],
                    label=data['label'],
                    content=data['content'],
                    item_type=data['type'],
                    description=data['description'],
                    tags=data['tags']
                )

                if item_id:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        "Éxito",
                        f"Snippet guardado exitosamente:\n\n{data['label']}\nTipo: {data['type']}"
                    )
                    logger.info(f"Snippet guardado como item: {data['label']} (ID: {item_id}, Tipo: {data['type']})")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo guardar el snippet en la base de datos"
                    )

        except Exception as e:
            logger.error(f"Error al guardar snippet como item: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar snippet:\n{str(e)}"
            )

    def _restore_session_tabs(self, tabs_data: list):
        """
        Restaura las pestañas de una sesión.

        Args:
            tabs_data: Lista de diccionarios con datos de pestañas
        """
        try:
            # Contar cuántas pestañas viejas hay
            old_tabs_count = len(self.tabs)

            # Restaurar cada pestaña de la sesión
            active_index = 0
            for i, tab in enumerate(tabs_data):
                url = tab.get('url', '')
                title = tab.get('title', 'Nueva pestaña')
                is_active = tab.get('is_active', False)

                if is_active:
                    active_index = i

                # Agregar pestaña nueva
                if url:
                    self.add_new_tab(url, title)

            # Cerrar las pestañas viejas (las primeras N)
            # Ahora las nuevas están al final, las viejas al principio
            # Cerrar desde el final de las viejas para no afectar índices
            for i in range(old_tabs_count - 1, -1, -1):
                if i < self.tab_widget.count() and i < len(self.tabs):
                    # Remover del widget
                    self.tab_widget.removeTab(i)
                    # Eliminar la referencia del browser
                    old_browser = self.tabs.pop(i)
                    old_browser.deleteLater()
                    logger.debug(f"Pestaña vieja {i} cerrada")

            # Activar la pestaña que estaba activa en la sesión
            if len(self.tabs) > 0 and active_index < len(self.tabs):
                self.tab_widget.setCurrentIndex(active_index)

            logger.info(f"Sesión restaurada con {len(tabs_data)} pestañas")

        except Exception as e:
            logger.error(f"Error al restaurar pestañas de sesión: {e}")

    def _restore_last_session(self):
        """Restaura la última sesión guardada automáticamente."""
        if not self.session_manager:
            return

        try:
            tabs_data = self.session_manager.restore_last_session()

            if tabs_data:
                logger.info("Restaurando última sesión...")
                self._restore_session_tabs(tabs_data)
            else:
                # No hay sesión anterior, cargar URL inicial
                logger.debug("No hay sesión anterior, cargando URL inicial")
                QTimer.singleShot(100, lambda: self.load_url(self.url))

        except Exception as e:
            logger.error(f"Error al restaurar última sesión: {e}")
            # En caso de error, cargar URL inicial
            QTimer.singleShot(100, lambda: self.load_url(self.url))

    # ==================== Search Functionality ====================

    def on_search_text(self, text: str, forward: bool):
        """
        Buscar texto en la página actual.

        Args:
            text: Texto a buscar
            forward: True para buscar hacia adelante, False para buscar hacia atrás
        """
        browser = self.get_current_browser()
        if not browser:
            return

        # Usar la API de QWebEngineView para buscar texto
        from PyQt6.QtWebEngineCore import QWebEnginePage

        if forward:
            browser.findText(text)
        else:
            # Buscar hacia atrás
            browser.findText(text, QWebEnginePage.FindFlag.FindBackward)

        logger.debug(f"Buscando: '{text}' (forward={forward})")

    def on_search_closed(self):
        """Handler cuando se cierra la barra de búsqueda"""
        # Limpiar resaltado de búsqueda
        browser = self.get_current_browser()
        if browser:
            browser.findText("")  # Limpiar búsqueda
        logger.debug("Búsqueda cerrada")

    def show_search_bar(self):
        """Mostrar barra de búsqueda"""
        self.search_bar.show_and_focus()
        logger.debug("Barra de búsqueda mostrada")

    def keyPressEvent(self, event: QKeyEvent):
        """Manejar eventos de teclado para atajos"""
        # Ctrl+F: Mostrar barra de búsqueda
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F:
            self.show_search_bar()
            event.accept()
            return

        # F3: Buscar siguiente
        elif event.key() == Qt.Key.Key_F3:
            if self.search_bar.isVisible():
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.search_bar.on_search_previous()
                else:
                    self.search_bar.on_search_next()
                event.accept()
                return

        # Esc: Cerrar búsqueda si está visible
        elif event.key() == Qt.Key.Key_Escape:
            if self.search_bar.isVisible():
                self.search_bar.close_search()
                event.accept()
                return

        super().keyPressEvent(event)

    # ==================== Eventos ====================

    def closeEvent(self, event):
        """Handler al cerrar la ventana."""
        logger.info("Cerrando SimpleBrowserWindow")

        # Auto-guardar sesión actual antes de cerrar
        if self.session_manager and len(self.tabs) > 0:
            try:
                tabs_data = self._get_current_tabs_data()
                self.session_manager.auto_save_on_close(tabs_data)
                logger.info("Sesión auto-guardada antes de cerrar")
            except Exception as e:
                logger.error(f"Error al auto-guardar sesión: {e}")

        # Desregistrar AppBar antes de cerrar
        self.unregister_appbar()

        # Detener carga en todas las pestañas si está en proceso
        if self.is_loading:
            for browser in self.tabs:
                try:
                    browser.stop()
                except:
                    pass

        # Emitir señal
        self.closed.emit()

        event.accept()
