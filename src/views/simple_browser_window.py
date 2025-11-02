"""
Simple Browser Window - Ventana flotante con navegador embebido
Author: Widget Sidebar Team
Date: 2025-11-02
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

logger = logging.getLogger(__name__)


class SimpleBrowserWindow(QWidget):
    """
    Ventana flotante simple con QWebEngineView.

    Características:
    - Una sola instancia de QWebEngineView
    - Barra de navegación mínima (URL + Reload)
    - Ventana flotante (NO AppBar)
    - Timeout de carga para prevenir cuelgues
    - Tema futurista simple
    """

    # Señales
    closed = pyqtSignal()

    def __init__(self, url: str = "https://www.google.com"):
        """
        Inicializa la ventana del navegador.

        Args:
            url: URL inicial a cargar
        """
        super().__init__()
        self.url = url
        self.is_loading = False

        logger.info(f"Inicializando SimpleBrowserWindow con URL: {url}")

        self._setup_window()
        self._setup_ui()
        self._configure_webengine()
        self._setup_timer()
        self._apply_styles()

        # Cargar URL inicial
        self.load_url(self.url)

    def _setup_window(self):
        """Configura propiedades de la ventana."""
        # Ventana flotante que permanece arriba
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        self.setWindowTitle("Widget Sidebar Browser")
        self.resize(500, 700)  # Tamaño fijo inicial

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de navegación
        nav_bar = self._create_nav_bar()
        main_layout.addLayout(nav_bar)

        # QWebEngineView (navegador)
        self.browser = QWebEngineView()
        main_layout.addWidget(self.browser)

        # Conectar señales
        self.browser.loadStarted.connect(self._on_load_started)
        self.browser.loadProgress.connect(self._on_load_progress)
        self.browser.loadFinished.connect(self._on_load_finished)
        self.browser.urlChanged.connect(self._on_url_changed)

        self.setLayout(main_layout)

    def _create_nav_bar(self) -> QHBoxLayout:
        """Crea la barra de navegación."""
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(5)

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

        # Botón reload
        self.reload_btn = QPushButton("↻")
        self.reload_btn.setFixedWidth(40)
        self.reload_btn.setToolTip("Recargar página")
        self.reload_btn.clicked.connect(self.reload_page)
        nav_layout.addWidget(self.reload_btn)

        # Botón cerrar
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(40)
        self.close_btn.setToolTip("Cerrar navegador")
        self.close_btn.clicked.connect(self.close)
        nav_layout.addWidget(self.close_btn)

        return nav_layout

    def _configure_webengine(self):
        """Configura QWebEngineSettings."""
        settings = self.browser.settings()

        # Habilitar JavaScript (necesario para la mayoría de sitios)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )

        # Deshabilitar plugins innecesarios para mejor performance
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled, False
        )

        # Habilitar local storage mínimo
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
        )

        # Seguridad: no permitir acceso remoto desde contenido local
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

        logger.debug("QWebEngineSettings configurado")

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
        """)

    # ==================== Métodos Públicos ====================

    def load_url(self, url: str):
        """
        Carga una URL en el navegador.

        Args:
            url: URL a cargar
        """
        # Asegurar que la URL tenga protocolo
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        logger.info(f"Cargando URL: {url}")

        # Iniciar timer de timeout (10 segundos)
        self.load_timer.start(10000)

        # Cargar URL
        self.browser.setUrl(QUrl(url))

    def reload_page(self):
        """Recarga la página actual."""
        logger.info("Recargando página")
        self.browser.reload()

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
        logger.debug(f"URL cambiada a: {url.toString()}")

    def _on_load_timeout(self):
        """Handler para timeout de carga."""
        if self.is_loading:
            logger.warning("Timeout de carga alcanzado")
            self.browser.stop()
            self.status_label.setText("●")
            self.status_label.setStyleSheet("color: #ff0000;")
            self.reload_btn.setEnabled(True)

    # ==================== Eventos ====================

    def closeEvent(self, event):
        """Handler al cerrar la ventana."""
        logger.info("Cerrando SimpleBrowserWindow")

        # Detener carga si está en proceso
        if self.is_loading:
            self.browser.stop()

        # Emitir señal
        self.closed.emit()

        event.accept()
