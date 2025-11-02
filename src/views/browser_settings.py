"""
Browser Settings
Widget for browser configuration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFormLayout, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class BrowserSettings(QWidget):
    """
    Browser settings widget
    Configure embedded browser options
    """

    # Signal emitted when settings change
    settings_changed = pyqtSignal()

    def __init__(self, controller=None, parent=None):
        """
        Initialize browser settings

        Args:
            controller: MainController instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.controller = controller
        self.browser_manager = controller.browser_manager if controller else None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title_label = QLabel("Configuración del Navegador Web")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00d4ff; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Browser group
        browser_group = QGroupBox("Navegador Embebido")
        browser_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        browser_layout = QFormLayout()
        browser_layout.setSpacing(15)

        # Home URL
        url_layout = QVBoxLayout()
        url_layout.setSpacing(5)

        url_label = QLabel("URL de inicio:")
        url_label.setStyleSheet("font-weight: normal; color: #cccccc;")
        url_layout.addWidget(url_label)

        self.home_url_input = QLineEdit()
        self.home_url_input.setPlaceholderText("https://www.google.com")
        self.home_url_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #00d4ff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
            }
        """)
        self.home_url_input.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.home_url_input)

        # URL suggestions
        suggestions_layout = QHBoxLayout()
        suggestions_layout.setSpacing(5)

        suggestion_label = QLabel("Sugerencias:")
        suggestion_label.setStyleSheet("font-size: 9pt; color: #888888;")
        suggestions_layout.addWidget(suggestion_label)

        self.google_btn = QPushButton("Google")
        self.google_btn.setStyleSheet(self._get_suggestion_button_style())
        self.google_btn.clicked.connect(lambda: self.set_url("https://www.google.com"))
        suggestions_layout.addWidget(self.google_btn)

        self.github_btn = QPushButton("GitHub")
        self.github_btn.setStyleSheet(self._get_suggestion_button_style())
        self.github_btn.clicked.connect(lambda: self.set_url("https://github.com"))
        suggestions_layout.addWidget(self.github_btn)

        self.docs_btn = QPushButton("Python Docs")
        self.docs_btn.setStyleSheet(self._get_suggestion_button_style())
        self.docs_btn.clicked.connect(lambda: self.set_url("https://docs.python.org"))
        suggestions_layout.addWidget(self.docs_btn)

        suggestions_layout.addStretch()
        url_layout.addLayout(suggestions_layout)

        browser_layout.addRow(url_layout)

        # Window size
        size_layout = QHBoxLayout()
        size_layout.setSpacing(10)

        width_label = QLabel("Ancho:")
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(300)
        self.width_spin.setMaximum(1200)
        self.width_spin.setValue(500)
        self.width_spin.setSuffix(" px")
        self.width_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e1e;
                color: #00d4ff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.width_spin.valueChanged.connect(self.settings_changed)

        height_label = QLabel("Alto:")
        self.height_spin = QSpinBox()
        self.height_spin.setMinimum(400)
        self.height_spin.setMaximum(1200)
        self.height_spin.setValue(700)
        self.height_spin.setSuffix(" px")
        self.height_spin.setStyleSheet(self.width_spin.styleSheet())
        self.height_spin.valueChanged.connect(self.settings_changed)

        size_layout.addWidget(width_label)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(height_label)
        size_layout.addWidget(self.height_spin)
        size_layout.addStretch()

        browser_layout.addRow("Tamaño de ventana:", size_layout)

        browser_group.setLayout(browser_layout)
        main_layout.addWidget(browser_group)

        # Info group
        info_group = QGroupBox("Información")
        info_group.setStyleSheet(browser_group.styleSheet())
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        info_text = QLabel(
            "<b>Navegador Embebido</b><br><br>"
            "Motor: Chromium (PyQt6-WebEngine)<br>"
            "Características:<br>"
            "• Navegación web completa<br>"
            "• JavaScript habilitado<br>"
            "• Ventana flotante simple<br>"
            "• Sin pestañas (una sola página)<br><br>"
            "<i>Presiona el botón 🌐 en el sidebar para abrir el navegador</i>"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("""
            QLabel {
                font-size: 9pt;
                color: #aaaaaa;
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Add stretch to push content to top
        main_layout.addStretch()

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_button = QPushButton("Guardar Configuración")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #00d4ff;
                border: 1px solid #00d4ff;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 10pt;
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
        self.save_button.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_button)

        main_layout.addLayout(save_layout)

    def _get_suggestion_button_style(self):
        """Get stylesheet for suggestion buttons"""
        return """
            QPushButton {
                background-color: #1e1e1e;
                color: #888888;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
                color: #00d4ff;
                border: 1px solid #00d4ff;
            }
            QPushButton:pressed {
                background-color: #00d4ff;
                color: #1e1e1e;
            }
        """

    def set_url(self, url: str):
        """Set the URL input field"""
        self.home_url_input.setText(url)

    def on_url_changed(self):
        """Handle URL text change"""
        self.settings_changed.emit()

    def load_settings(self):
        """Load settings from browser manager"""
        if not self.browser_manager:
            logger.warning("BrowserManager not available")
            return

        try:
            # Load home URL
            home_url = self.browser_manager.load_home_url()
            self.home_url_input.setText(home_url)

            # Load window size from DB
            config = self.browser_manager.db.get_browser_config()
            if config:
                self.width_spin.setValue(config.get('width', 500))
                self.height_spin.setValue(config.get('height', 700))

            logger.info("Browser settings loaded")

        except Exception as e:
            logger.error(f"Error loading browser settings: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Error al cargar configuración del navegador:\n{str(e)}"
            )

    def save_settings(self):
        """Save settings to browser manager"""
        if not self.browser_manager:
            logger.warning("BrowserManager not available")
            QMessageBox.warning(
                self,
                "Error",
                "BrowserManager no está disponible"
            )
            return

        try:
            # Get values
            home_url = self.home_url_input.text().strip()
            width = self.width_spin.value()
            height = self.height_spin.value()

            # Validate URL
            if not home_url:
                QMessageBox.warning(
                    self,
                    "Validación",
                    "La URL de inicio no puede estar vacía"
                )
                return

            # Basic URL validation
            if not (home_url.startswith('http://') or home_url.startswith('https://')):
                home_url = 'https://' + home_url

            # Save to database
            config = {
                'home_url': home_url,
                'width': width,
                'height': height
            }
            self.browser_manager.db.save_browser_config(config)

            # Update browser manager
            self.browser_manager.set_home_url(home_url)

            logger.info(f"Browser settings saved: {config}")

            QMessageBox.information(
                self,
                "Éxito",
                "Configuración del navegador guardada correctamente"
            )

            # Emit signal
            self.settings_changed.emit()

        except Exception as e:
            logger.error(f"Error saving browser settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar configuración:\n{str(e)}"
            )

    def get_settings(self):
        """
        Get current settings as dictionary

        Returns:
            dict: Settings dictionary
        """
        return {
            'home_url': self.home_url_input.text().strip(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value()
        }
