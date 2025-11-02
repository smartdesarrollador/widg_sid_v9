"""
Sidebar View - Vertical sidebar with category buttons and scroll navigation
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont
from typing import List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.category import Category
from views.widgets.button_widget import CategoryButton
from styles.futuristic_theme import get_theme
from styles.effects import ScanLineEffect


class Sidebar(QWidget):
    """Vertical sidebar with category buttons and scroll navigation"""

    # Signal emitted when a category button is clicked
    category_clicked = pyqtSignal(str)  # category_id

    # Signal emitted when settings button is clicked
    settings_clicked = pyqtSignal()

    # Signal emitted when favorites button is clicked
    favorites_clicked = pyqtSignal()

    # Signal emitted when stats button is clicked
    stats_clicked = pyqtSignal()

    # Signal emitted when dashboard button is clicked
    dashboard_clicked = pyqtSignal()

    # Signal emitted when category filter button is clicked
    category_filter_clicked = pyqtSignal()

    # Signal emitted when global search button is clicked
    global_search_clicked = pyqtSignal()

    # Signal emitted when browser button is clicked
    browser_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.category_buttons = {}
        self.active_button = None
        self.scroll_area = None
        self.theme = get_theme()  # Obtener tema futurista

        self.init_ui()

    def init_ui(self):
        """Initialize sidebar UI"""
        # Set fixed width
        self.setFixedWidth(70)
        self.setMinimumHeight(400)

        # Set background con tema futurista
        self.setStyleSheet(self.theme.get_sidebar_style())

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # App title/logo
        title_label = QLabel("WS")
        title_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('secondary')}
                );
                color: {self.theme.get_color('text_primary')};
                padding: 10px;
                font-size: 13pt;
                font-weight: bold;
                border-bottom: 3px solid {self.theme.get_color('accent')};
                letter-spacing: 3px;
            }}
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Scroll up button
        self.scroll_up_button = QPushButton("▲")
        self.scroll_up_button.setFixedSize(70, 30)
        self.scroll_up_button.setToolTip("Desplazar arriba")
        self.scroll_up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scroll_up_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_mid')};
                color: {self.theme.get_color('primary')};
                border: none;
                border-bottom: 1px solid {self.theme.get_color('surface')};
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text_primary')};
            }}
            QPushButton:disabled {{
                color: {self.theme.get_color('text_secondary')};
                background-color: {self.theme.get_color('background_deep')};
            }}
        """)
        self.scroll_up_button.clicked.connect(self.scroll_up)
        main_layout.addWidget(self.scroll_up_button)

        # Global Search button (BG - Búsqueda Global)
        self.global_search_button = QPushButton("🔍")
        self.global_search_button.setFixedSize(70, 40)
        self.global_search_button.setToolTip("Búsqueda Global")
        self.global_search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.global_search_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('accent')}
                );
                color: {self.theme.get_color('text_primary')};
                border: none;
                border-bottom: 2px solid {self.theme.get_color('background_deep')};
                font-size: 14pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('accent')},
                    stop:1 {self.theme.get_color('primary')}
                );
                border-bottom: 2px solid {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('surface')};
                transform: scale(0.95);
            }}
        """)
        self.global_search_button.clicked.connect(self.on_global_search_clicked)
        main_layout.addWidget(self.global_search_button)

        # Category Filter button (FC)
        self.category_filter_button = QPushButton("🎯")
        self.category_filter_button.setFixedSize(70, 40)
        self.category_filter_button.setToolTip("Filtro de Categorías")
        self.category_filter_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.category_filter_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('secondary')}
                );
                color: {self.theme.get_color('text_primary')};
                border: none;
                border-bottom: 2px solid {self.theme.get_color('background_deep')};
                font-size: 14pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('secondary')},
                    stop:1 {self.theme.get_color('accent')}
                );
                border-bottom: 2px solid {self.theme.get_color('primary')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('surface')};
                transform: scale(0.95);
            }}
        """)
        self.category_filter_button.clicked.connect(self.on_category_filter_clicked)
        main_layout.addWidget(self.category_filter_button)

        # Scroll area for category buttons
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        # Container widget for buttons
        buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(buttons_container)
        self.buttons_layout.setContentsMargins(0, 5, 0, 5)
        self.buttons_layout.setSpacing(5)
        self.buttons_layout.addStretch()

        self.scroll_area.setWidget(buttons_container)
        main_layout.addWidget(self.scroll_area)

        # Scroll down button
        self.scroll_down_button = QPushButton("▼")
        self.scroll_down_button.setFixedSize(70, 30)
        self.scroll_down_button.setToolTip("Desplazar abajo")
        self.scroll_down_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scroll_down_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_mid')};
                color: {self.theme.get_color('primary')};
                border: none;
                border-top: 1px solid {self.theme.get_color('surface')};
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text_primary')};
            }}
            QPushButton:disabled {{
                color: {self.theme.get_color('text_secondary')};
                background-color: {self.theme.get_color('background_deep')};
            }}
        """)
        self.scroll_down_button.clicked.connect(self.scroll_down)
        main_layout.addWidget(self.scroll_down_button)

        # Favorites button
        self.favorites_button = QPushButton("⭐")
        self.favorites_button.setFixedSize(70, 45)
        self.favorites_button.setToolTip("Favoritos")
        self.favorites_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favorites_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_secondary')};
                border: none;
                border-top: 2px solid {self.theme.get_color('surface')};
                font-size: 16pt;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: #FFD700;
            }}
            QPushButton:pressed {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFD700,
                    stop:1 #FFA500
                );
                color: {self.theme.get_color('background_deep')};
            }}
        """)
        self.favorites_button.clicked.connect(self.on_favorites_clicked)
        main_layout.addWidget(self.favorites_button)

        # Stats button
        self.stats_button = QPushButton("📊")
        self.stats_button.setFixedSize(70, 45)
        self.stats_button.setToolTip("Estadísticas")
        self.stats_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stats_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_secondary')};
                border: none;
                border-top: 2px solid {self.theme.get_color('surface')};
                font-size: 16pt;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('success')};
            }}
            QPushButton:pressed {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('success')},
                    stop:1 {self.theme.get_color('primary')}
                );
                color: {self.theme.get_color('background_deep')};
            }}
        """)
        self.stats_button.clicked.connect(self.on_stats_clicked)
        main_layout.addWidget(self.stats_button)

        # Browser button
        self.browser_button = QPushButton("🌐")
        self.browser_button.setFixedSize(70, 45)
        self.browser_button.setToolTip("Navegador Web")
        self.browser_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browser_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_secondary')};
                border: none;
                border-top: 2px solid {self.theme.get_color('surface')};
                font-size: 14pt;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('surface')}
                );
                color: {self.theme.get_color('accent')};
                border-top: 2px solid {self.theme.get_color('accent')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('primary')};
                color: {self.theme.get_color('text_primary')};
            }}
        """)
        self.browser_button.clicked.connect(self.on_browser_clicked)
        main_layout.addWidget(self.browser_button)

        # Dashboard button
        self.dashboard_button = QPushButton("🗂️")
        self.dashboard_button.setFixedSize(70, 45)
        self.dashboard_button.setToolTip("Dashboard de Estructura")
        self.dashboard_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dashboard_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_secondary')};
                border: none;
                border-top: 2px solid {self.theme.get_color('surface')};
                font-size: 16pt;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('primary')};
            }}
            QPushButton:pressed {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('secondary')}
                );
                color: {self.theme.get_color('text_primary')};
            }}
        """)
        self.dashboard_button.clicked.connect(self.on_dashboard_clicked)
        main_layout.addWidget(self.dashboard_button)

        # Settings button at the bottom
        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(70, 45)
        self.settings_button.setToolTip("Configuración")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_secondary')};
                border: none;
                border-top: 2px solid {self.theme.get_color('surface')};
                font-size: 16pt;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('primary')};
            }}
            QPushButton:pressed {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.get_color('primary')},
                    stop:1 {self.theme.get_color('accent')}
                );
                color: {self.theme.get_color('text_primary')};
            }}
        """)
        self.settings_button.clicked.connect(self.on_settings_clicked)
        main_layout.addWidget(self.settings_button)

        # Update scroll button states
        self.update_scroll_buttons()

        # Aplicar efecto scanlines (muy sutil)
        self.scanline_effect = ScanLineEffect(self, line_spacing=6, speed=1.0)
        self.scanline_effect.setGeometry(self.rect())
        self.scanline_effect.lower()

    def scroll_up(self):
        """Scroll the category list up"""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        new_value = max(0, current_value - 50)  # Scroll by button height (45px + spacing)

        # Animate scroll
        self.animate_scroll(current_value, new_value)

    def scroll_down(self):
        """Scroll the category list down"""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        new_value = min(scrollbar.maximum(), current_value + 50)  # Scroll by button height (45px + spacing)

        # Animate scroll
        self.animate_scroll(current_value, new_value)

    def animate_scroll(self, start_value, end_value):
        """Animate scroll movement"""
        scrollbar = self.scroll_area.verticalScrollBar()

        # Create animation
        self.scroll_animation = QPropertyAnimation(scrollbar, b"value")
        self.scroll_animation.setDuration(200)
        self.scroll_animation.setStartValue(start_value)
        self.scroll_animation.setEndValue(end_value)
        self.scroll_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.scroll_animation.finished.connect(self.update_scroll_buttons)
        self.scroll_animation.start()

    def update_scroll_buttons(self):
        """Update scroll button enabled/disabled state"""
        if not self.scroll_area:
            return

        scrollbar = self.scroll_area.verticalScrollBar()

        # Disable up button if at top
        self.scroll_up_button.setEnabled(scrollbar.value() > 0)

        # Disable down button if at bottom
        self.scroll_down_button.setEnabled(scrollbar.value() < scrollbar.maximum())

    def load_categories(self, categories: List[Category]):
        """Load and create buttons for categories"""
        # Clear existing buttons
        self.clear_buttons()

        # Create button for each category
        for category in categories:
            if not category.is_active:
                continue

            button = CategoryButton(category.id, category.name)
            button.clicked.connect(lambda checked, cat_id=category.id: self.on_category_clicked(cat_id))

            self.category_buttons[category.id] = button
            # Insert before the stretch
            self.buttons_layout.insertWidget(self.buttons_layout.count() - 1, button)

        # Update scroll buttons after loading
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_scroll_buttons)
        self.update_scroll_buttons()

    def clear_buttons(self):
        """Clear all category buttons"""
        for button in self.category_buttons.values():
            button.deleteLater()
        self.category_buttons.clear()
        self.active_button = None

    def on_category_clicked(self, category_id: str):
        """Handle category button click"""
        # Update active button
        if self.active_button:
            self.active_button.set_active(False)

        clicked_button = self.category_buttons.get(category_id)
        if clicked_button:
            clicked_button.set_active(True)
            self.active_button = clicked_button

        # Emit signal
        self.category_clicked.emit(category_id)

    def set_active_category(self, category_id: str):
        """Set active category programmatically"""
        if self.active_button:
            self.active_button.set_active(False)

        button = self.category_buttons.get(category_id)
        if button:
            button.set_active(True)
            self.active_button = button

    def on_favorites_clicked(self):
        """Handle favorites button click"""
        self.favorites_clicked.emit()

    def on_stats_clicked(self):
        """Handle stats button click"""
        self.stats_clicked.emit()

    def on_browser_clicked(self):
        """Handle browser button click"""
        self.browser_clicked.emit()

    def on_settings_clicked(self):
        """Handle settings button click"""
        self.settings_clicked.emit()

    def on_category_filter_clicked(self):
        """Handle category filter button click"""
        self.category_filter_clicked.emit()

    def on_global_search_clicked(self):
        """Handle global search button click"""
        self.global_search_clicked.emit()

    def on_dashboard_clicked(self):
        """Handle dashboard button click"""
        self.dashboard_clicked.emit()
