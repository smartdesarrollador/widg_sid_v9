"""
Structure Dashboard
Main window for visualizing global structure of categories and items
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QWidget, QApplication, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QBrush, QColor, QShortcut, QKeySequence
import logging

from core.dashboard_manager import DashboardManager
from views.dashboard.search_bar_widget import SearchBarWidget
from views.dashboard.highlight_delegate import HighlightDelegate
from views.dashboard.action_bar_widget import ActionBarWidget
from views.dashboard.selection_utils_widget import SelectionUtilsWidget

logger = logging.getLogger(__name__)


class StructureDashboard(QDialog):
    """Dashboard window for viewing global structure"""

    # Signal emitted when user wants to navigate to a category
    navigate_to_category = pyqtSignal(int)  # category_id

    def __init__(self, db_manager, parent=None):
        """
        Initialize the structure dashboard

        Args:
            db_manager: DBManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db_manager
        self.dashboard_manager = DashboardManager(db_manager)
        self.structure = None
        self.current_matches = []  # Store current search matches
        self.highlight_delegate = None  # Will be set in init_ui
        self.is_custom_maximized = False  # Track custom maximize state

        # For window dragging
        self.dragging = False
        self.drag_position = None
        self.normal_geometry = None  # Store normal size for restore

        # Tracking de items seleccionados (para selección múltiple)
        self.selected_items = {
            'categories': [],  # Lista de category_ids seleccionadas
            'items': []        # Lista de (category_id, item_id) tuplas
        }

        # Tracking de filtros activos
        self.active_filter = None  # 'favorites', 'inactive', 'archived', None
        self.filter_buttons = {}  # Referencias a los botones de filtro
        self.active_type_filters = set()  # Set of active item types ('URL', 'CODE', 'PATH', 'TEXT')
        self.type_filter_buttons = {}  # Referencias a los botones de filtro de tipo

        self.init_ui()
        self.setup_shortcuts()
        self.load_data()

    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("Dashboard de Estructura - Widget Sidebar")
        self.setModal(False)  # Changed to non-modal so it doesn't block main window
        self.resize(1200, 800)

        # Set window flags to stay behind the main sidebar
        self.setWindowFlags(
            Qt.WindowType.Window |  # Normal window
            Qt.WindowType.CustomizeWindowHint  # Allow custom buttons
        )

        # Center window on screen
        self.center_on_screen()

        # Apply dark theme
        self.apply_dark_theme()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Search Bar
        self.search_bar = SearchBarWidget()
        self.search_bar.search_changed.connect(self.on_search_changed)
        self.search_bar.navigate_to_result.connect(self.navigate_to_result)
        main_layout.addWidget(self.search_bar)

        # Selection Utilities
        self.selection_utils = SelectionUtilsWidget()
        self.selection_utils.select_all_requested.connect(self.select_all)
        self.selection_utils.select_none_requested.connect(self.clear_selection)
        self.selection_utils.invert_selection_requested.connect(self.invert_selection)
        main_layout.addWidget(self.selection_utils)

        # TreeView
        self.tree_widget = self.create_tree_widget()
        main_layout.addWidget(self.tree_widget)

        # Action Bar (for bulk operations)
        self.action_bar = ActionBarWidget()
        self.action_bar.favorite_requested.connect(self.bulk_set_favorite)
        self.action_bar.unfavorite_requested.connect(self.bulk_unset_favorite)
        self.action_bar.activate_requested.connect(self.bulk_activate)
        self.action_bar.deactivate_requested.connect(self.bulk_deactivate)
        self.action_bar.archive_requested.connect(self.bulk_archive)
        self.action_bar.unarchive_requested.connect(self.bulk_unarchive)
        self.action_bar.delete_requested.connect(self.bulk_delete)
        self.action_bar.clear_selection_requested.connect(self.clear_selection)
        main_layout.addWidget(self.action_bar)

        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)

        logger.info("StructureDashboard UI initialized")

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+F to focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_bar.focus_search)

        # F3 to navigate to next result
        next_shortcut = QShortcut(QKeySequence("F3"), self)
        next_shortcut.activated.connect(self.search_bar.navigate_next)

        # Shift+F3 to navigate to previous result
        prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        prev_shortcut.activated.connect(self.search_bar.navigate_previous)

        # Escape to clear search
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.search_bar.clear_search)

        # Ctrl+A to select all
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self.select_all)

        # Ctrl+Shift+A to deselect all
        deselect_all_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        deselect_all_shortcut.activated.connect(self.clear_selection)

        # Ctrl+I to invert selection
        invert_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        invert_shortcut.activated.connect(self.invert_selection)

        # Delete to delete selected items
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.bulk_delete)

        logger.info("Keyboard shortcuts configured: Ctrl+F, F3, Shift+F3, Esc, Ctrl+A, Ctrl+Shift+A, Ctrl+I, Delete")

    def center_on_screen(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def apply_dark_theme(self):
        """Apply dark theme stylesheet"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:checked {
                background-color: #00cc44;
                border: 2px solid #00ff55;
            }
            QTreeWidget {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QTreeWidget::item:hover {
                background-color: #2d2d2d;
            }
            QTreeWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QTreeWidget::branch {
                background-color: #252525;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                image: url(none);
                border-image: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                image: url(none);
                border-image: none;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-right: 1px solid #3d3d3d;
                font-weight: bold;
            }
        """)

    def create_header(self) -> QWidget:
        """Create header widget with title and buttons"""
        header = QWidget()
        header.setFixedHeight(100)  # Aumentado para 2 filas
        header.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #3d3d3d;
            }
        """)

        # Layout principal vertical para 2 filas
        main_layout = QVBoxLayout(header)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)

        # ========== FILA 1: Título + Controles de ventana ==========
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)

        # Draggable title area
        self.title_label = QLabel("📊 Dashboard de Estructura")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setCursor(Qt.CursorShape.SizeAllCursor)  # Show move cursor
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                padding: 5px;
            }
        """)

        # Install event filter to capture mouse events on title
        self.title_label.mousePressEvent = self.header_mouse_press
        self.title_label.mouseMoveEvent = self.header_mouse_move
        self.title_label.mouseReleaseEvent = self.header_mouse_release

        row1_layout.addWidget(self.title_label)
        row1_layout.addStretch()

        # Window control buttons - with better visibility
        window_controls_style = """
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 18pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """

        # Minimize button
        minimize_btn = QPushButton("─")
        minimize_btn.setToolTip("Minimizar")
        minimize_btn.setFixedSize(40, 35)
        minimize_btn.setStyleSheet(window_controls_style)
        minimize_btn.clicked.connect(self.showMinimized)
        row1_layout.addWidget(minimize_btn)

        # Maximize/Restore button
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setToolTip("Maximizar")
        self.maximize_btn.setFixedSize(40, 35)
        self.maximize_btn.setStyleSheet(window_controls_style)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        row1_layout.addWidget(self.maximize_btn)

        # Close button - with red hover
        close_btn = QPushButton("✕")
        close_btn.setToolTip("Cerrar")
        close_btn.setFixedSize(40, 35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 18pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #e81123;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #c50d1d;
            }
        """)
        close_btn.clicked.connect(self.close)
        row1_layout.addWidget(close_btn)

        main_layout.addLayout(row1_layout)

        # ========== FILA 2: Filtros de estado + Filtros de tipo + Acciones ==========
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(8)

        # Filtros de estado
        self.fav_btn = QPushButton("⭐ Favoritos")
        self.fav_btn.setToolTip("Mostrar solo items favoritos")
        self.fav_btn.clicked.connect(self.filter_favorites)
        self.fav_btn.setCheckable(True)
        row2_layout.addWidget(self.fav_btn)
        self.filter_buttons['favorites'] = self.fav_btn

        self.inactive_btn = QPushButton("🚫 Desactivados")
        self.inactive_btn.setToolTip("Mostrar solo items/categorías desactivados")
        self.inactive_btn.clicked.connect(self.filter_inactive)
        self.inactive_btn.setCheckable(True)
        row2_layout.addWidget(self.inactive_btn)
        self.filter_buttons['inactive'] = self.inactive_btn

        self.archived_btn = QPushButton("📦 Archivados")
        self.archived_btn.setToolTip("Mostrar solo items archivados")
        self.archived_btn.clicked.connect(self.filter_archived)
        self.archived_btn.setCheckable(True)
        row2_layout.addWidget(self.archived_btn)
        self.filter_buttons['archived'] = self.archived_btn

        # Separador visual
        row2_layout.addSpacing(15)

        # Filtros de tipo (múltiple selección permitida)
        self.url_type_btn = QPushButton("🔗 URL")
        self.url_type_btn.setToolTip("Filtrar items de tipo URL")
        self.url_type_btn.clicked.connect(lambda: self.toggle_type_filter('URL'))
        self.url_type_btn.setCheckable(True)
        row2_layout.addWidget(self.url_type_btn)
        self.type_filter_buttons['URL'] = self.url_type_btn

        self.code_type_btn = QPushButton("💻 CODE")
        self.code_type_btn.setToolTip("Filtrar items de tipo CODE")
        self.code_type_btn.clicked.connect(lambda: self.toggle_type_filter('CODE'))
        self.code_type_btn.setCheckable(True)
        row2_layout.addWidget(self.code_type_btn)
        self.type_filter_buttons['CODE'] = self.code_type_btn

        self.path_type_btn = QPushButton("📂 PATH")
        self.path_type_btn.setToolTip("Filtrar items de tipo PATH")
        self.path_type_btn.clicked.connect(lambda: self.toggle_type_filter('PATH'))
        self.path_type_btn.setCheckable(True)
        row2_layout.addWidget(self.path_type_btn)
        self.type_filter_buttons['PATH'] = self.path_type_btn

        self.text_type_btn = QPushButton("📝 TEXT")
        self.text_type_btn.setToolTip("Filtrar items de tipo TEXT")
        self.text_type_btn.clicked.connect(lambda: self.toggle_type_filter('TEXT'))
        self.text_type_btn.setCheckable(True)
        row2_layout.addWidget(self.text_type_btn)
        self.type_filter_buttons['TEXT'] = self.text_type_btn

        # Separador visual
        row2_layout.addSpacing(15)

        # Botones de acción
        sort_btn = QPushButton("🔢 +Items")
        sort_btn.setToolTip("Ordenar por cantidad de items (desc)")
        sort_btn.clicked.connect(self.sort_by_items)
        row2_layout.addWidget(sort_btn)

        reset_btn = QPushButton("↺ Todo")
        reset_btn.setToolTip("Mostrar todo sin filtros")
        reset_btn.clicked.connect(self.reset_filters)
        row2_layout.addWidget(reset_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refrescar")
        refresh_btn.clicked.connect(self.refresh_data)
        row2_layout.addWidget(refresh_btn)

        row2_layout.addStretch()

        main_layout.addLayout(row2_layout)

        return header

    def create_tree_widget(self) -> QTreeWidget:
        """Create the main tree widget"""
        tree = QTreeWidget()
        tree.setHeaderLabels(["☐", "Nombre", "Tipo", "Info"])
        tree.setColumnWidth(0, 70)   # Checkbox column (aumentado para que no tape el header)
        tree.setColumnWidth(1, 340)  # Name column (reducido un poco para compensar)
        tree.setColumnWidth(2, 100)  # Type column
        tree.setColumnWidth(3, 600)  # Info column

        # Enable alternating row colors
        tree.setAlternatingRowColors(True)

        # Enable animations
        tree.setAnimated(True)

        # Set custom delegate for highlighting
        self.highlight_delegate = HighlightDelegate(tree)
        tree.setItemDelegateForColumn(1, self.highlight_delegate)  # Highlight in column 1 (Name)
        tree.setItemDelegateForColumn(3, self.highlight_delegate)  # Highlight in column 3 (Info)

        # Connect checkbox change signal
        tree.itemChanged.connect(self.on_item_check_changed)

        # Double click to copy content
        tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Enable context menu
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_context_menu)

        return tree

    def create_footer(self) -> QWidget:
        """Create footer widget with statistics"""
        footer = QWidget()
        footer.setFixedHeight(40)
        footer.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-top: 1px solid #3d3d3d;
            }
        """)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 10, 20, 10)

        # Statistics label
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.stats_label)

        layout.addStretch()

        # Action buttons
        expand_btn = QPushButton("Expandir Todo")
        expand_btn.clicked.connect(self.tree_widget.expandAll)
        expand_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        layout.addWidget(expand_btn)

        collapse_btn = QPushButton("Colapsar Todo")
        collapse_btn.clicked.connect(self.tree_widget.collapseAll)
        collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        layout.addWidget(collapse_btn)

        return footer

    def load_data(self):
        """Load data from database and populate tree"""
        logger.info("Loading dashboard data...")

        try:
            # Get structure
            self.structure = self.dashboard_manager.get_full_structure()

            # Clear tree
            self.tree_widget.clear()

            # Populate tree
            self.populate_tree(self.structure)

            # Update statistics
            self.update_statistics()

            logger.info("Dashboard data loaded successfully")

        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}", exc_info=True)
            self.stats_label.setText("❌ Error al cargar datos")

    def populate_tree(self, structure: dict):
        """
        Populate tree widget with structure data

        Args:
            structure: Structure dict from DashboardManager
        """
        categories = structure.get('categories', [])

        logger.info(f"Populating tree with {len(categories)} categories...")

        for category in categories:
            # Create category item (Level 1)
            category_item = QTreeWidgetItem(self.tree_widget)

            # Column 0: Checkbox
            category_item.setFlags(category_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            category_item.setCheckState(0, Qt.CheckState.Unchecked)

            # Column 1: Name with icon and item count
            status_indicator = ""
            if not category.get('is_active', 1):  # Si is_active es 0 o False
                status_indicator = "🚫 "  # Icono que coincide con el botón Desactivar
            category_name = f"{status_indicator}{category['icon']} {category['name']} ({len(category['items'])} items)"
            category_item.setText(1, category_name)
            category_item.setFont(1, self.get_bold_font())

            # Aplicar estilo visual adicional para categorías desactivadas
            if not category.get('is_active', 1):
                # Cambiar el color del texto para categorías desactivadas
                for col in range(4):
                    category_item.setForeground(col, QBrush(QColor('#888888')))  # Texto gris

            # Column 2: Type
            category_item.setText(2, "Categoría")

            # Column 3: Tags
            if category['tags']:
                tags_str = ", ".join([f"#{tag}" for tag in category['tags']])
                category_item.setText(3, tags_str)

            # Build tooltip for category
            category_tooltip_parts = []
            category_tooltip_parts.append(f"<b>{category['name']}</b>")
            category_tooltip_parts.append(f"<b>Items:</b> {len(category['items'])}")

            # Mostrar estado de categoría
            if not category.get('is_active', 1):
                category_tooltip_parts.append("🚫 <b><span style='color: #f44336;'>CATEGORÍA DESACTIVADA</span></b>")

            if category['tags']:
                tags_str = ", ".join([f"#{tag}" for tag in category['tags']])
                category_tooltip_parts.append(f"<b>Tags:</b> {tags_str}")

            if category.get('is_predefined'):
                category_tooltip_parts.append("📌 <b>Categoría predefinida</b>")

            category_tooltip_parts.append("<br><i>Click para expandir/colapsar | Click derecho para opciones</i>")

            category_tooltip_html = "<br>".join(category_tooltip_parts)
            category_item.setToolTip(1, category_tooltip_html)
            category_item.setToolTip(2, category_tooltip_html)
            category_item.setToolTip(3, category_tooltip_html)

            # Store category ID in user data (column 0 for identification)
            category_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'category',
                'id': category['id']
            })

            # Add items under this category (Level 2)
            for item in category['items']:
                item_widget = QTreeWidgetItem(category_item)

                # Column 0: Checkbox
                item_widget.setFlags(item_widget.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item_widget.setCheckState(0, Qt.CheckState.Unchecked)

                # Column 1: Item name with indicators
                indicators = ""
                # Estado de archivo/activo (primero para mayor visibilidad)
                if item.get('is_archived'):
                    indicators += "📦 "  # Icono que coincide con el botón Archivar
                if not item.get('is_active', 1):  # Si is_active es 0 o False
                    indicators += "🚫 "  # Icono que coincide con el botón Desactivar
                # Otros indicadores
                if item.get('is_list'):
                    indicators += "📝 "
                if item['is_favorite']:
                    indicators += "⭐ "
                if item['is_sensitive']:
                    indicators += "🔒 "

                item_name = f"{indicators}{item['label']}"
                item_widget.setText(1, item_name)

                # Aplicar estilo visual adicional para items desactivados o archivados
                if item.get('is_archived') or not item.get('is_active', 1):
                    # Cambiar el color del texto para items desactivados/archivados
                    for col in range(4):
                        item_widget.setForeground(col, QBrush(QColor('#888888')))  # Texto gris

                # Column 2: Item type
                type_icons = {
                    'CODE': '💻',
                    'URL': '🔗',
                    'PATH': '📂',
                    'TEXT': '📝'
                }
                type_icon = type_icons.get(item['type'], '📄')
                item_widget.setText(2, f"{type_icon} {item['type']}")

                # Column 3: Tags + list_group + preview
                info_parts = []

                # List group (if is_list)
                if item.get('is_list') and item.get('list_group'):
                    info_parts.append(f"📝 Lista: {item['list_group']}")

                # Tags
                if item['tags']:
                    tags_str = ", ".join([f"#{tag}" for tag in item['tags']])
                    info_parts.append(tags_str)

                # Content preview (first 50 chars)
                if not item['is_sensitive'] and item['content']:
                    preview = item['content'][:50]
                    if len(item['content']) > 50:
                        preview += "..."
                    info_parts.append(f"Preview: {preview}")

                item_widget.setText(3, " | ".join(info_parts))

                # Build tooltip with detailed information
                tooltip_parts = []
                tooltip_parts.append(f"<b>{item['label']}</b>")
                tooltip_parts.append(f"<b>Tipo:</b> {item['type']}")

                # Mostrar estado de archivo/activo
                if item.get('is_archived'):
                    tooltip_parts.append("📦 <b><span style='color: #ff9800;'>ARCHIVADO</span></b>")
                if not item.get('is_active', 1):
                    tooltip_parts.append("🚫 <b><span style='color: #f44336;'>DESACTIVADO</span></b>")

                if item['description']:
                    tooltip_parts.append(f"<b>Descripción:</b> {item['description']}")

                if item.get('is_list') and item.get('list_group'):
                    tooltip_parts.append(f"📝 <b>Pertenece a la lista:</b> {item['list_group']}")

                if item['tags']:
                    tags_str = ", ".join([f"#{tag}" for tag in item['tags']])
                    tooltip_parts.append(f"<b>Tags:</b> {tags_str}")

                if item['is_favorite']:
                    tooltip_parts.append("⭐ <b>Favorito</b>")

                if item['is_sensitive']:
                    tooltip_parts.append("🔒 <b>Contenido sensible (encriptado)</b>")
                else:
                    # Show content preview for non-sensitive items
                    if item['content']:
                        content_preview = item['content'][:100]
                        if len(item['content']) > 100:
                            content_preview += "..."
                        tooltip_parts.append(f"<b>Contenido:</b><br><code>{content_preview}</code>")

                tooltip_parts.append("<br><i>Doble click para copiar | Click derecho para más opciones</i>")

                tooltip_html = "<br>".join(tooltip_parts)
                item_widget.setToolTip(1, tooltip_html)
                item_widget.setToolTip(2, tooltip_html)
                item_widget.setToolTip(3, tooltip_html)

                # Store item data (column 0 for identification)
                item_widget.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'item',
                    'id': item['id'],
                    'content': item['content'],
                    'item_type': item['type']
                })

        logger.info("Tree populated successfully")

    def update_statistics(self):
        """Update statistics label"""
        if not self.structure:
            return

        stats = self.dashboard_manager.calculate_statistics(self.structure)

        # Build detailed statistics text
        stats_parts = [
            f"📊 {stats['total_categories']} cat.",
            f"📄 {stats['total_items']} items",
            f"⭐ {stats['total_favorites']} fav.",
            f"🔒 {stats['total_sensitive']} sens.",
            f"🏷️ {stats['total_unique_tags']} tags"
        ]

        # Add inactive and archived counts
        if stats.get('total_inactive', 0) > 0:
            stats_parts.append(f"🚫 {stats['total_inactive']} inact.")
        if stats.get('total_archived', 0) > 0:
            stats_parts.append(f"📦 {stats['total_archived']} arch.")

        # Add most used tag if available
        if stats.get('most_used_tag'):
            stats_parts.append(f"🔥 #{stats['most_used_tag']}")

        # Add average items per category
        if stats.get('avg_items_per_category', 0) > 0:
            stats_parts.append(f"📈 {stats['avg_items_per_category']} prom/cat")

        stats_text = " | ".join(stats_parts)
        self.stats_label.setText(stats_text)

    def get_bold_font(self) -> QFont:
        """Get bold font for categories"""
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        return font

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on tree item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        if data['type'] == 'item':
            # Copy item content to clipboard
            content = data.get('content', '')
            if content:
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                logger.info(f"Copied item content to clipboard")
                self.stats_label.setText("✅ Contenido copiado al portapapeles")
                # Reset message after 2 seconds
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, lambda: self.update_statistics())

    def on_item_check_changed(self, item: QTreeWidgetItem, column: int):
        """
        Handle checkbox state change for tree items

        Args:
            item: QTreeWidgetItem that changed
            column: Column index (0 is checkbox column)
        """
        # Only handle changes in checkbox column
        if column != 0:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        check_state = item.checkState(0)
        is_checked = (check_state == Qt.CheckState.Checked)

        # Temporarily block signals to avoid recursion
        self.tree_widget.blockSignals(True)

        try:
            if data['type'] == 'category':
                # Handle category selection
                category_id = data['id']
                self.update_category_selection(item, category_id, is_checked)

            elif data['type'] == 'item':
                # Handle item selection
                item_id = data['id']
                # Get parent category
                parent_item = item.parent()
                if parent_item:
                    parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
                    if parent_data and parent_data['type'] == 'category':
                        category_id = parent_data['id']
                        self.update_item_selection(parent_item, category_id, item_id, is_checked)
        finally:
            # Re-enable signals
            self.tree_widget.blockSignals(False)

        logger.debug(f"Selection updated - Categories: {self.selected_items['categories']}, Items: {len(self.selected_items['items'])}")

        # Update action bar to reflect new selection
        self.update_action_bar()

    def update_category_selection(self, category_item: QTreeWidgetItem, category_id: int, is_checked: bool):
        """
        Update selection state for a category and all its items

        Args:
            category_item: QTreeWidgetItem for the category
            category_id: Category ID
            is_checked: Whether category is checked
        """
        # Update category tracking
        if is_checked:
            if category_id not in self.selected_items['categories']:
                self.selected_items['categories'].append(category_id)
        else:
            if category_id in self.selected_items['categories']:
                self.selected_items['categories'].remove(category_id)

        # Update all child items
        for i in range(category_item.childCount()):
            child_item = category_item.child(i)
            child_data = child_item.data(0, Qt.ItemDataRole.UserRole)

            if child_data and child_data['type'] == 'item':
                item_id = child_data['id']

                # Set checkbox state
                child_item.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)

                # Update items tracking
                item_tuple = (category_id, item_id)
                if is_checked:
                    if item_tuple not in self.selected_items['items']:
                        self.selected_items['items'].append(item_tuple)
                else:
                    if item_tuple in self.selected_items['items']:
                        self.selected_items['items'].remove(item_tuple)

    def update_item_selection(self, parent_item: QTreeWidgetItem, category_id: int, item_id: int, is_checked: bool):
        """
        Update selection state for an item and check parent category if needed

        Args:
            parent_item: Parent category QTreeWidgetItem
            category_id: Category ID
            item_id: Item ID
            is_checked: Whether item is checked
        """
        # Update items tracking
        item_tuple = (category_id, item_id)
        if is_checked:
            if item_tuple not in self.selected_items['items']:
                self.selected_items['items'].append(item_tuple)
        else:
            if item_tuple in self.selected_items['items']:
                self.selected_items['items'].remove(item_tuple)

        # Check if all items in category are selected
        total_items = parent_item.childCount()
        checked_items = sum(1 for i in range(total_items)
                           if parent_item.child(i).checkState(0) == Qt.CheckState.Checked)

        # Update parent category checkbox state
        if checked_items == 0:
            # No items checked - uncheck category
            parent_item.setCheckState(0, Qt.CheckState.Unchecked)
            if category_id in self.selected_items['categories']:
                self.selected_items['categories'].remove(category_id)
        elif checked_items == total_items:
            # All items checked - check category
            parent_item.setCheckState(0, Qt.CheckState.Checked)
            if category_id not in self.selected_items['categories']:
                self.selected_items['categories'].append(category_id)
        else:
            # Some items checked - partial check (PartiallyChecked state)
            parent_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
            if category_id in self.selected_items['categories']:
                self.selected_items['categories'].remove(category_id)

    def update_action_bar(self):
        """Update action bar visibility and state based on current selection"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])
        total_count = items_count + categories_count

        # Update action bar widget
        self.action_bar.update_selection(total_count, items_count, categories_count)

        logger.debug(f"Action bar updated: {total_count} total ({items_count} items, {categories_count} categories)")

    def clear_selection(self):
        """Clear all checkboxes and reset selection tracking"""
        logger.info("Clearing all selections...")

        # Block signals to avoid triggering on_item_check_changed multiple times
        self.tree_widget.blockSignals(True)

        try:
            # Iterate through all top-level items (categories)
            for i in range(self.tree_widget.topLevelItemCount()):
                category_item = self.tree_widget.topLevelItem(i)
                category_item.setCheckState(0, Qt.CheckState.Unchecked)

                # Uncheck all child items
                for j in range(category_item.childCount()):
                    item_widget = category_item.child(j)
                    item_widget.setCheckState(0, Qt.CheckState.Unchecked)

            # Clear tracking arrays
            self.selected_items['categories'].clear()
            self.selected_items['items'].clear()

            logger.info("All selections cleared")
        finally:
            # Re-enable signals
            self.tree_widget.blockSignals(False)

        # Update action bar (will hide it)
        self.update_action_bar()

    def select_all(self):
        """Select all categories and items in the tree"""
        logger.info("Selecting all elements...")

        # Block signals to avoid triggering on_item_check_changed multiple times
        self.tree_widget.blockSignals(True)

        try:
            # Iterate through all top-level items (categories)
            for i in range(self.tree_widget.topLevelItemCount()):
                category_item = self.tree_widget.topLevelItem(i)
                category_data = category_item.data(0, Qt.ItemDataRole.UserRole)

                if category_data and category_data['type'] == 'category':
                    category_id = category_data['id']

                    # Check category
                    category_item.setCheckState(0, Qt.CheckState.Checked)

                    # Add to tracking
                    if category_id not in self.selected_items['categories']:
                        self.selected_items['categories'].append(category_id)

                    # Check all child items
                    for j in range(category_item.childCount()):
                        item_widget = category_item.child(j)
                        item_widget.setCheckState(0, Qt.CheckState.Checked)

                        # Add to tracking
                        item_data = item_widget.data(0, Qt.ItemDataRole.UserRole)
                        if item_data and item_data['type'] == 'item':
                            item_id = item_data['id']
                            item_tuple = (category_id, item_id)
                            if item_tuple not in self.selected_items['items']:
                                self.selected_items['items'].append(item_tuple)

            logger.info(f"Selected all: {len(self.selected_items['categories'])} categories, {len(self.selected_items['items'])} items")
        finally:
            # Re-enable signals
            self.tree_widget.blockSignals(False)

        # Update action bar
        self.update_action_bar()

    def invert_selection(self):
        """Invert current selection (checked become unchecked and vice versa)"""
        logger.info("Inverting selection...")

        # Block signals to avoid triggering on_item_check_changed multiple times
        self.tree_widget.blockSignals(True)

        try:
            # Create new tracking dictionaries
            new_categories = []
            new_items = []

            # Iterate through all top-level items (categories)
            for i in range(self.tree_widget.topLevelItemCount()):
                category_item = self.tree_widget.topLevelItem(i)
                category_data = category_item.data(0, Qt.ItemDataRole.UserRole)

                if category_data and category_data['type'] == 'category':
                    category_id = category_data['id']
                    current_state = category_item.checkState(0)

                    # Invert category state
                    if current_state == Qt.CheckState.Checked:
                        # Was checked, uncheck it
                        category_item.setCheckState(0, Qt.CheckState.Unchecked)
                    else:
                        # Was unchecked (or partial), check it
                        category_item.setCheckState(0, Qt.CheckState.Checked)
                        new_categories.append(category_id)

                    # Invert all child items
                    for j in range(category_item.childCount()):
                        item_widget = category_item.child(j)
                        item_data = item_widget.data(0, Qt.ItemDataRole.UserRole)

                        if item_data and item_data['type'] == 'item':
                            item_id = item_data['id']
                            current_item_state = item_widget.checkState(0)

                            # Invert item state
                            if current_item_state == Qt.CheckState.Checked:
                                item_widget.setCheckState(0, Qt.CheckState.Unchecked)
                            else:
                                item_widget.setCheckState(0, Qt.CheckState.Checked)
                                new_items.append((category_id, item_id))

                    # Update category state based on children
                    checked_count = sum(1 for j in range(category_item.childCount())
                                       if category_item.child(j).checkState(0) == Qt.CheckState.Checked)
                    total_count = category_item.childCount()

                    if checked_count == 0:
                        category_item.setCheckState(0, Qt.CheckState.Unchecked)
                        if category_id in new_categories:
                            new_categories.remove(category_id)
                    elif checked_count == total_count:
                        category_item.setCheckState(0, Qt.CheckState.Checked)
                        if category_id not in new_categories:
                            new_categories.append(category_id)
                    else:
                        category_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
                        if category_id in new_categories:
                            new_categories.remove(category_id)

            # Update tracking
            self.selected_items['categories'] = new_categories
            self.selected_items['items'] = new_items

            logger.info(f"Inverted selection: {len(new_categories)} categories, {len(new_items)} items now selected")
        finally:
            # Re-enable signals
            self.tree_widget.blockSignals(False)

        # Update action bar
        self.update_action_bar()

    # ========== BULK OPERATIONS (Fase 3 - Implemented) ==========

    def bulk_set_favorite(self):
        """Mark selected items as favorites"""
        items_count = len(self.selected_items['items'])
        if items_count == 0:
            logger.warning("No items selected for favorite operation")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            f"¿Marcar {items_count} item{'s' if items_count != 1 else ''} como favorito{'s' if items_count != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Update each item in database
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_favorite=1)
                        success_count += 1
                        logger.debug(f"Item {item_id} marked as favorite")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error marking item {item_id} as favorite: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} marcado{'s' if success_count != 1 else ''} como favorito{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully marked {success_count} items as favorites")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} actualizado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Marked {success_count} items as favorites with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_set_favorite: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al marcar favoritos:\n{str(e)}"
                )

    def bulk_unset_favorite(self):
        """Remove selected items from favorites"""
        items_count = len(self.selected_items['items'])
        if items_count == 0:
            logger.warning("No items selected for unfavorite operation")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            f"¿Quitar marca de favorito de {items_count} item{'s' if items_count != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Update each item in database
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_favorite=0)
                        success_count += 1
                        logger.debug(f"Item {item_id} unmarked as favorite")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error unmarking item {item_id} as favorite: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} actualizado{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully unmarked {success_count} items as favorites")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} actualizado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Unmarked {success_count} items as favorites with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_unset_favorite: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al quitar favoritos:\n{str(e)}"
                )

    def bulk_activate(self):
        """Activate selected categories and items"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])
        total_count = items_count + categories_count

        if total_count == 0:
            logger.warning("No elements selected for activate operation")
            return

        # Confirmation dialog
        message = f"¿Activar {total_count} elemento{'s' if total_count != 1 else ''}?"
        if items_count > 0 and categories_count > 0:
            message += f"\n\n• {categories_count} categoría{'s' if categories_count != 1 else ''}\n• {items_count} item{'s' if items_count != 1 else ''}"

        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Activate categories
                for category_id in self.selected_items['categories']:
                    try:
                        self.db.update_category(category_id, is_active=1)
                        success_count += 1
                        logger.debug(f"Category {category_id} activated")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error activating category {category_id}: {e}")

                # Activate items (and unarchive them)
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_active=1, is_archived=0)
                        success_count += 1
                        logger.debug(f"Item {item_id} activated")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error activating item {item_id}: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} activado{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully activated {success_count} elements")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} activado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Activated {success_count} elements with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_activate: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al activar elementos:\n{str(e)}"
                )

    def bulk_archive(self):
        """Archive selected categories and items"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])
        total_count = items_count + categories_count

        if total_count == 0:
            logger.warning("No elements selected for archive operation")
            return

        # Confirmation dialog
        message = f"¿Archivar {total_count} elemento{'s' if total_count != 1 else ''}?"
        if items_count > 0 and categories_count > 0:
            message += f"\n\n• {categories_count} categoría{'s' if categories_count != 1 else ''} (se desactivarán)\n• {items_count} item{'s' if items_count != 1 else ''}"

        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Archive categories (deactivate them)
                for category_id in self.selected_items['categories']:
                    try:
                        self.db.update_category(category_id, is_active=0)
                        success_count += 1
                        logger.debug(f"Category {category_id} archived (deactivated)")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error archiving category {category_id}: {e}")

                # Archive items
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_archived=1)
                        success_count += 1
                        logger.debug(f"Item {item_id} archived")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error archiving item {item_id}: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} archivado{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully archived {success_count} elements")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} archivado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Archived {success_count} elements with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_archive: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al archivar elementos:\n{str(e)}"
                )

    def bulk_deactivate(self):
        """Deactivate selected categories and items"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])
        total_count = items_count + categories_count

        if total_count == 0:
            logger.warning("No elements selected for deactivate operation")
            return

        # Confirmation dialog
        message = f"¿Desactivar {total_count} elemento{'s' if total_count != 1 else ''}?"
        if items_count > 0 and categories_count > 0:
            message += f"\n\n• {categories_count} categoría{'s' if categories_count != 1 else ''}\n• {items_count} item{'s' if items_count != 1 else ''}"

        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Deactivate categories
                for category_id in self.selected_items['categories']:
                    try:
                        self.db.update_category(category_id, is_active=0)
                        success_count += 1
                        logger.debug(f"Category {category_id} deactivated")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error deactivating category {category_id}: {e}")

                # Deactivate items
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_active=0)
                        success_count += 1
                        logger.debug(f"Item {item_id} deactivated")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error deactivating item {item_id}: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} desactivado{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully deactivated {success_count} elements")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} desactivado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Deactivated {success_count} elements with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_deactivate: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al desactivar elementos:\n{str(e)}"
                )

    def bulk_unarchive(self):
        """Unarchive selected items"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])

        if items_count == 0:
            logger.warning("No items selected for unarchive operation")
            QMessageBox.information(
                self,
                "Sin Elementos",
                "No hay items seleccionados para desarchivar.\nNota: Solo los items pueden ser archivados/desarchivados."
            )
            return

        # Confirmation dialog
        message = f"¿Desarchivar {items_count} item{'s' if items_count != 1 else ''}?"
        if categories_count > 0:
            message += f"\n\nNota: {categories_count} categoría{'s' if categories_count != 1 else ''} seleccionada{'s' if categories_count != 1 else ''} no se verá{'n' if categories_count != 1 else ''} afectada{'s' if categories_count != 1 else ''}\n(las categorías no tienen estado de archivo)"

        reply = QMessageBox.question(
            self,
            "Confirmar Operación",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Unarchive items
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.update_item(item_id, is_archived=0)
                        success_count += 1
                        logger.debug(f"Item {item_id} unarchived")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error unarchiving item {item_id}: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} desarchivado{'s' if success_count != 1 else ''}"
                    )
                    logger.info(f"Successfully unarchived {success_count} items")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} item{'s' if success_count != 1 else ''} desarchivado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Unarchived {success_count} items with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_unarchive: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al desarchivar items:\n{str(e)}"
                )

    def bulk_delete(self):
        """Delete selected categories and items"""
        items_count = len(self.selected_items['items'])
        categories_count = len(self.selected_items['categories'])
        total_count = items_count + categories_count

        if total_count == 0:
            logger.warning("No elements selected for delete operation")
            return

        # Warning confirmation dialog with detailed message
        message = f"⚠️ ¿Estás SEGURO de eliminar {total_count} elemento{'s' if total_count != 1 else ''}?\n\n"
        message += "⚠️ Esta acción NO se puede deshacer.\n\n"

        if categories_count > 0:
            message += f"• {categories_count} categoría{'s' if categories_count != 1 else ''}"
            if categories_count == 1:
                message += " (se eliminarán también todos sus items)"
            else:
                message += " (se eliminarán también todos sus items)"
            message += "\n"

        if items_count > 0:
            message += f"• {items_count} item{'s' if items_count != 1 else ''}\n"

        reply = QMessageBox.warning(
            self,
            "⚠️ ADVERTENCIA - Eliminar Permanentemente",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            error_count = 0

            try:
                # Delete categories (this also deletes their items via CASCADE)
                for category_id in self.selected_items['categories']:
                    try:
                        self.db.delete_category(category_id)
                        success_count += 1
                        logger.debug(f"Category {category_id} deleted (with all its items)")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error deleting category {category_id}: {e}")

                # Delete items
                for category_id, item_id in self.selected_items['items']:
                    try:
                        self.db.delete_item(item_id)
                        success_count += 1
                        logger.debug(f"Item {item_id} deleted")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error deleting item {item_id}: {e}")

                # Clear selection and reload
                self.clear_selection()
                self.load_data()

                # Show result
                if error_count == 0:
                    QMessageBox.information(
                        self,
                        "Operación Exitosa",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} eliminado{'s' if success_count != 1 else ''} permanentemente"
                    )
                    logger.info(f"Successfully deleted {success_count} elements")
                else:
                    QMessageBox.warning(
                        self,
                        "Operación Completada con Errores",
                        f"✅ {success_count} elemento{'s' if success_count != 1 else ''} eliminado{'s' if success_count != 1 else ''}\n"
                        f"❌ {error_count} error{'es' if error_count != 1 else ''}"
                    )
                    logger.warning(f"Deleted {success_count} elements with {error_count} errors")

            except Exception as e:
                logger.error(f"Critical error in bulk_delete: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error Crítico",
                    f"❌ Error al eliminar elementos:\n{str(e)}"
                )

    # ========== FILTERS AND SORTING ==========

    def filter_favorites(self):
        """Show only favorite items"""
        logger.info("Filtering favorites...")

        # Actualizar estado de filtro
        self.set_active_filter('favorites')

        # Filtrar estructura
        import copy
        filtered_structure = copy.deepcopy(self.structure)

        # Filter favorite items
        for category in filtered_structure['categories']:
            category['items'] = [
                item for item in category['items']
                if item.get('is_favorite', False)
            ]

        # Also apply type filters if active
        if self.active_type_filters:
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if item.get('type') in self.active_type_filters
                ]

        self.tree_widget.clear()
        self.populate_tree(filtered_structure)

        # Update stats label
        msg = "🔍 Mostrando solo favoritos"
        if self.active_type_filters:
            types_str = ', '.join(sorted(self.active_type_filters))
            msg += f" (tipos: {types_str})"
        self.stats_label.setText(msg)

    def filter_inactive(self):
        """Show only inactive items/categories"""
        logger.info("Filtering inactive...")

        # Actualizar estado de filtro
        self.set_active_filter('inactive')

        # Filtrar estructura manualmente
        import copy
        filtered_structure = copy.deepcopy(self.structure)

        # Filtrar categorías y items inactivos
        for category in filtered_structure['categories']:
            # Filtrar items inactivos en esta categoría
            category['items'] = [
                item for item in category['items']
                if not item.get('is_active', 1)  # Solo items con is_active=0
            ]

        # Also apply type filters if active
        if self.active_type_filters:
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if item.get('type') in self.active_type_filters
                ]

        self.tree_widget.clear()
        self.populate_tree(filtered_structure)

        # Update stats label
        msg = "🚫 Mostrando solo desactivados"
        if self.active_type_filters:
            types_str = ', '.join(sorted(self.active_type_filters))
            msg += f" (tipos: {types_str})"
        self.stats_label.setText(msg)

    def filter_archived(self):
        """Show only archived items"""
        logger.info("Filtering archived...")

        # Actualizar estado de filtro
        self.set_active_filter('archived')

        # Filtrar estructura manualmente
        import copy
        filtered_structure = copy.deepcopy(self.structure)

        # Filtrar items archivados
        for category in filtered_structure['categories']:
            category['items'] = [
                item for item in category['items']
                if item.get('is_archived', False)  # Solo items con is_archived=True
            ]

        # Also apply type filters if active
        if self.active_type_filters:
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if item.get('type') in self.active_type_filters
                ]

        self.tree_widget.clear()
        self.populate_tree(filtered_structure)

        # Update stats label
        msg = "📦 Mostrando solo archivados"
        if self.active_type_filters:
            types_str = ', '.join(sorted(self.active_type_filters))
            msg += f" (tipos: {types_str})"
        self.stats_label.setText(msg)

    def set_active_filter(self, filter_name):
        """
        Set active filter and update button states

        Args:
            filter_name: 'favorites', 'inactive', 'archived', or None
        """
        # Desmarcar todos los botones primero
        for btn in self.filter_buttons.values():
            btn.setChecked(False)

        # Marcar el botón activo
        if filter_name and filter_name in self.filter_buttons:
            self.filter_buttons[filter_name].setChecked(True)

        self.active_filter = filter_name
        logger.info(f"Active filter set to: {filter_name}")

    def sort_by_items(self):
        """Sort by item count descending"""
        logger.info("Sorting by items count...")
        sorted_structure = self.dashboard_manager.filter_and_sort_structure(
            structure=self.structure,
            sort_by='items_desc'
        )
        self.tree_widget.clear()
        self.populate_tree(sorted_structure)
        self.stats_label.setText("🔢 Ordenado por cantidad de items")

    def toggle_type_filter(self, item_type: str):
        """
        Toggle type filter on/off (allows multiple types to be selected)

        Args:
            item_type: Item type ('URL', 'CODE', 'PATH', 'TEXT')
        """
        if item_type in self.active_type_filters:
            # Remove type filter
            self.active_type_filters.remove(item_type)
            self.type_filter_buttons[item_type].setChecked(False)
            logger.info(f"Type filter '{item_type}' removed")
        else:
            # Add type filter
            self.active_type_filters.add(item_type)
            self.type_filter_buttons[item_type].setChecked(True)
            logger.info(f"Type filter '{item_type}' added")

        # Apply filters
        self.apply_type_filters()

    def apply_type_filters(self):
        """Apply active type filters to the tree"""
        if not self.active_type_filters:
            # No type filters active, show all (or apply other active filter)
            if self.active_filter:
                # Re-apply the active state filter
                if self.active_filter == 'favorites':
                    self.filter_favorites()
                elif self.active_filter == 'inactive':
                    self.filter_inactive()
                elif self.active_filter == 'archived':
                    self.filter_archived()
            else:
                # Show all
                self.tree_widget.clear()
                self.populate_tree(self.structure)
                self.update_statistics()
            return

        # Filter structure by types
        import copy
        filtered_structure = copy.deepcopy(self.structure)

        # Filter items by type
        for category in filtered_structure['categories']:
            category['items'] = [
                item for item in category['items']
                if item.get('type') in self.active_type_filters
            ]

        # Also apply state filter if active
        if self.active_filter == 'favorites':
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if item.get('is_favorite', False)
                ]
        elif self.active_filter == 'inactive':
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if not item.get('is_active', 1)
                ]
        elif self.active_filter == 'archived':
            for category in filtered_structure['categories']:
                category['items'] = [
                    item for item in category['items']
                    if item.get('is_archived', False)
                ]

        self.tree_widget.clear()
        self.populate_tree(filtered_structure)

        # Update stats label
        types_str = ', '.join(sorted(self.active_type_filters))
        filter_msg = f"🔍 Mostrando tipos: {types_str}"
        if self.active_filter:
            filter_msg += f" (y {self.active_filter})"
        self.stats_label.setText(filter_msg)

        logger.info(f"Type filters applied: {self.active_type_filters}")

    def reset_filters(self):
        """Reset all filters and show all data"""
        logger.info("Resetting filters...")
        # Clear search
        self.search_bar.clear_search()
        # Desmarcar todos los filtros
        self.set_active_filter(None)
        # Clear type filters
        self.active_type_filters.clear()
        for btn in self.type_filter_buttons.values():
            btn.setChecked(False)
        # Reload full structure
        self.tree_widget.clear()
        self.populate_tree(self.structure)
        self.update_statistics()

    def refresh_data(self):
        """Refresh data from database"""
        logger.info("Refreshing dashboard data...")
        self.stats_label.setText("🔄 Refrescando datos...")
        self.load_data()

    def on_search_changed(self, query: str, scope_filters: dict):
        """Handle search query change"""
        logger.info(f"Search changed - Query: '{query}', Filters: {scope_filters}")

        # Update highlight delegate with search query
        if self.highlight_delegate:
            self.highlight_delegate.set_search_query(query)

        # Clear previous highlighting
        self.clear_highlighting()

        if not query:
            # If empty query, show all items
            self.show_all_items()
            self.search_bar.set_results_count(0)
            self.current_matches = []
            # Refresh tree to remove highlights
            self.tree_widget.viewport().update()
            return

        # Perform search
        matches = self.dashboard_manager.search(query, scope_filters, self.structure)
        self.current_matches = matches

        # Filter tree to show only matches
        self.filter_tree_by_matches(matches)

        # Update results counter
        self.search_bar.set_results_count(len(matches))

        # Refresh tree to apply highlights
        self.tree_widget.viewport().update()

        # Navigate to first result
        if matches:
            self.navigate_to_result(0)

        logger.info(f"Search found {len(matches)} matches")

    def clear_highlighting(self):
        """Clear all highlighting in tree"""
        root = self.tree_widget.invisibleRootItem()

        for cat_idx in range(root.childCount()):
            category_item = root.child(cat_idx)

            # Reset category background
            for col in range(3):
                category_item.setBackground(col, QBrush(QColor('#252525')))

            # Reset items background
            for item_idx in range(category_item.childCount()):
                item_widget = category_item.child(item_idx)
                for col in range(3):
                    item_widget.setBackground(col, QBrush(QColor('#252525')))

    def highlight_matches(self, matches: list):
        """
        Highlight matching items in tree

        Args:
            matches: List of (match_type, category_index, item_index) tuples
        """
        root = self.tree_widget.invisibleRootItem()
        highlight_color = QColor('#3d5a80')  # Dark blue for highlights

        for match_type, cat_idx, item_idx in matches:
            if cat_idx >= root.childCount():
                continue

            category_item = root.child(cat_idx)

            if item_idx == -1:
                # Highlight category
                for col in range(3):
                    category_item.setBackground(col, QBrush(highlight_color))
                # Expand category to show items
                category_item.setExpanded(True)
            else:
                # Highlight item
                if item_idx < category_item.childCount():
                    item_widget = category_item.child(item_idx)
                    for col in range(3):
                        item_widget.setBackground(col, QBrush(highlight_color))
                    # Expand category to show highlighted item
                    category_item.setExpanded(True)

    def show_all_items(self):
        """Show all items in tree"""
        root = self.tree_widget.invisibleRootItem()

        for cat_idx in range(root.childCount()):
            category_item = root.child(cat_idx)
            category_item.setHidden(False)

            # Show all items in category
            for item_idx in range(category_item.childCount()):
                item_widget = category_item.child(item_idx)
                item_widget.setHidden(False)

    def navigate_to_result(self, result_index: int):
        """
        Navigate to specific search result by scrolling and selecting it

        Args:
            result_index: Index of the result to navigate to (0-based)
        """
        if result_index < 0 or result_index >= len(self.current_matches):
            logger.warning(f"Invalid result index: {result_index}")
            return

        match_type, cat_idx, item_idx = self.current_matches[result_index]
        root = self.tree_widget.invisibleRootItem()

        if cat_idx >= root.childCount():
            logger.warning(f"Invalid category index: {cat_idx}")
            return

        category_item = root.child(cat_idx)

        # Clear previous selection
        self.tree_widget.clearSelection()

        if item_idx == -1:
            # Navigate to category
            category_item.setExpanded(True)
            category_item.setSelected(True)
            self.tree_widget.scrollToItem(category_item, QTreeWidget.ScrollHint.PositionAtCenter)
            logger.debug(f"Navigated to category at index {cat_idx}")
        else:
            # Navigate to item
            if item_idx < category_item.childCount():
                category_item.setExpanded(True)
                item_widget = category_item.child(item_idx)
                item_widget.setSelected(True)
                self.tree_widget.scrollToItem(item_widget, QTreeWidget.ScrollHint.PositionAtCenter)
                logger.debug(f"Navigated to item at cat:{cat_idx}, item:{item_idx}")
            else:
                logger.warning(f"Invalid item index: {item_idx}")

    def filter_tree_by_matches(self, matches: list):
        """
        Filter tree to show only matching items

        Args:
            matches: List of (match_type, category_index, item_index) tuples
        """
        root = self.tree_widget.invisibleRootItem()

        # Create set of matching category and item indices for quick lookup
        matching_categories = set()
        matching_items = {}  # {cat_idx: set(item_indices)}

        for match_type, cat_idx, item_idx in matches:
            matching_categories.add(cat_idx)
            if item_idx != -1:
                if cat_idx not in matching_items:
                    matching_items[cat_idx] = set()
                matching_items[cat_idx].add(item_idx)

        # Hide/show categories and items based on matches
        for cat_idx in range(root.childCount()):
            category_item = root.child(cat_idx)

            # Check if this category has any matches
            if cat_idx in matching_categories:
                # Category has matches - show it
                category_item.setHidden(False)
                category_item.setExpanded(True)

                # If category itself matched, show all its items
                category_matched = any(
                    m[1] == cat_idx and m[2] == -1
                    for m in matches
                )

                if category_matched:
                    # Show all items in this category
                    for item_idx in range(category_item.childCount()):
                        item_widget = category_item.child(item_idx)
                        item_widget.setHidden(False)
                else:
                    # Only show matching items
                    cat_matching_items = matching_items.get(cat_idx, set())
                    for item_idx in range(category_item.childCount()):
                        item_widget = category_item.child(item_idx)
                        item_widget.setHidden(item_idx not in cat_matching_items)
            else:
                # No matches in this category - hide it
                category_item.setHidden(True)

    def show_context_menu(self, position):
        """Show context menu on right-click"""
        item = self.tree_widget.itemAt(position)

        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #007acc;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3d3d3d;
                margin: 5px 10px;
            }
        """)

        if data['type'] == 'item':
            # Item context menu
            copy_action = menu.addAction("📋 Copiar contenido")
            copy_action.triggered.connect(lambda: self.copy_item_content(data))

            menu.addSeparator()

            details_action = menu.addAction("ℹ️ Ver detalles")
            details_action.triggered.connect(lambda: self.show_item_details(item, data))

        elif data['type'] == 'category':
            # Category context menu
            if item.isExpanded():
                collapse_action = menu.addAction("➖ Colapsar")
                collapse_action.triggered.connect(lambda: item.setExpanded(False))
            else:
                expand_action = menu.addAction("➕ Expandir")
                expand_action.triggered.connect(lambda: item.setExpanded(True))

            menu.addSeparator()

            expand_all_action = menu.addAction("⬇️ Expandir todo")
            expand_all_action.triggered.connect(self.tree_widget.expandAll)

            collapse_all_action = menu.addAction("⬆️ Colapsar todo")
            collapse_all_action.triggered.connect(self.tree_widget.collapseAll)

        # Show menu at cursor position
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
        logger.debug(f"Context menu shown for {data['type']}")

    def copy_item_content(self, data: dict):
        """Copy item content to clipboard"""
        content = data.get('content', '')
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            self.stats_label.setText("✅ Contenido copiado al portapapeles")
            logger.info(f"Copied item content to clipboard")

            # Reset message after 2 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.update_statistics())

    def show_item_details(self, item: QTreeWidgetItem, data: dict):
        """Show detailed information about an item"""
        from PyQt6.QtWidgets import QMessageBox

        details = []
        details.append(f"<b>Tipo:</b> {data.get('item_type', 'N/A')}")
        details.append(f"<b>ID:</b> {data.get('id', 'N/A')}")

        # Get item text from tree
        item_name = item.text(0)
        details.append(f"<b>Nombre:</b> {item_name}")

        # Content preview
        content = data.get('content', '')
        if content:
            preview = content[:200]
            if len(content) > 200:
                preview += "..."
            details.append(f"<b>Contenido:</b><br><code>{preview}</code>")

        details_html = "<br><br>".join(details)

        msg = QMessageBox(self)
        msg.setWindowTitle("Detalles del Item")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(details_html)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
                min-width: 400px;
            }
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        msg.exec()
        logger.info(f"Showed details for item {data.get('id')}")

    def header_mouse_press(self, event):
        """Handle mouse press on header for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def header_mouse_move(self, event):
        """Handle mouse move on header for dragging"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            # If maximized, restore to normal size first
            if self.is_custom_maximized:
                self.is_custom_maximized = False
                self.showNormal()
                self.maximize_btn.setText("□")
                self.maximize_btn.setToolTip("Maximizar")

            # Move window
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def header_mouse_release(self, event):
        """Handle mouse release after dragging"""
        self.dragging = False
        event.accept()

    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.is_custom_maximized:
            # Restore to saved normal size
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
                logger.debug(f"Restored to saved geometry: {self.normal_geometry}")
            else:
                self.showNormal()
                logger.debug("Restored to normal size (no saved geometry)")

            self.is_custom_maximized = False
            self.maximize_btn.setText("□")
            self.maximize_btn.setToolTip("Maximizar")
        else:
            # Save current geometry before maximizing
            self.normal_geometry = self.geometry()
            logger.debug(f"Saved normal geometry: {self.normal_geometry}")

            # Maximize window, but leave space for the main sidebar
            screen = QApplication.primaryScreen()
            if screen:
                # Get screen geometry
                screen_rect = screen.availableGeometry()

                # Reserve space for sidebar (70px width + some margin)
                sidebar_width = 85  # 70px sidebar + 15px margin

                # Set geometry to cover screen except sidebar area (leave space on the right)
                maximized_rect = screen_rect.adjusted(0, 0, -sidebar_width, 0)
                self.setGeometry(maximized_rect)

                # Set flag
                self.is_custom_maximized = True

                # Update button
                self.maximize_btn.setText("❐")
                self.maximize_btn.setToolTip("Restaurar")
                logger.debug(f"Dashboard maximized with sidebar space: {maximized_rect}")
            else:
                # Fallback to normal maximize if screen not available
                self.showMaximized()
                self.maximize_btn.setText("❐")
                self.maximize_btn.setToolTip("Restaurar")
                logger.debug("Dashboard maximized (fallback)")

    def closeEvent(self, event):
        """Handle window close"""
        logger.info("Structure Dashboard closed")
        event.accept()
