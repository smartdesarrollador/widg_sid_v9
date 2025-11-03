"""
Simple Browser Manager - Gestor minimalista del navegador embebido
Author: Widget Sidebar Team
Date: 2025-11-02
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleBrowserManager:
    """
    Gestor minimalista del navegador embebido.

    Responsabilidades:
    - Crear/destruir instancia de SimpleBrowserWindow
    - Toggle show/hide del navegador
    - Cargar/guardar configuración básica (URL home)
    - Lazy loading para evitar cuelgues
    - Gestionar perfiles persistentes del navegador
    """

    def __init__(self, db_manager, main_window=None):
        """
        Inicializa el manager.

        Args:
            db_manager: Instancia de DBManager para persistencia
            main_window: Referencia a MainWindow para posicionamiento (opcional)
        """
        self.db = db_manager
        self.main_window = main_window
        self.browser_window: Optional['SimpleBrowserWindow'] = None
        self._home_url: Optional[str] = None

        # Inicializar BrowserProfileManager para persistencia de sesiones web
        from src.core.browser_profile_manager import BrowserProfileManager
        self.profile_manager = BrowserProfileManager(db_manager)

        logger.info("SimpleBrowserManager inicializado con perfil persistente")

    def toggle_browser(self):
        """
        Alterna entre mostrar y ocultar el navegador.

        Si el navegador está visible, lo oculta.
        Si está oculto o no existe, lo muestra.
        """
        if self.browser_window and self.browser_window.isVisible():
            logger.info("Ocultando navegador")
            self.hide_browser()
        else:
            logger.info("Mostrando navegador")
            self.show_browser()

    def show_browser(self):
        """
        Muestra el navegador.

        Lazy loading: crea la instancia solo cuando se necesita
        para evitar cuelgues en el inicio de la aplicación.
        """
        # Lazy loading - crear solo cuando se necesita
        if not self.browser_window:
            logger.info("Creando nueva instancia de SimpleBrowserWindow")

            # Import aquí para evitar circular imports y lazy loading
            from src.views.simple_browser_window import SimpleBrowserWindow

            # Cargar configuración completa desde DB
            config = self.db.get_browser_config()
            home_url = config.get('home_url', 'https://www.google.com')
            width = config.get('width', 500)
            height = config.get('height', 700)

            # Crear ventana pasando el DBManager y ProfileManager
            self.browser_window = SimpleBrowserWindow(
                home_url,
                db_manager=self.db,
                profile_manager=self.profile_manager
            )

            # Aplicar tamaño configurado
            self.browser_window.resize(width, height)

            # Conectar señal de cierre
            self.browser_window.closed.connect(self._on_browser_closed)

        # Posicionar al lado del sidebar si tenemos referencia a MainWindow
        if self.main_window:
            self.browser_window.position_near_sidebar(self.main_window)
            logger.debug("Navegador posicionado al lado del sidebar")

        # Mostrar y traer al frente
        self.browser_window.show()
        self.browser_window.raise_()
        self.browser_window.activateWindow()

        # Registrar como AppBar para reservar espacio en el escritorio
        self.browser_window.register_appbar()

        logger.info("Navegador mostrado")

    def hide_browser(self):
        """Oculta el navegador sin destruirlo."""
        if self.browser_window:
            # Desregistrar AppBar para liberar espacio
            self.browser_window.unregister_appbar()
            # Ocultar ventana
            self.browser_window.hide()
            logger.info("Navegador ocultado")

    def close_browser(self):
        """
        Cierra y destruye completamente el navegador.

        Libera recursos de memoria.
        """
        if self.browser_window:
            try:
                logger.info("Cerrando y destruyendo navegador")
                self.browser_window.close()
                self.browser_window.deleteLater()
            except RuntimeError:
                # El objeto ya fue eliminado
                logger.debug("Browser window already deleted")
            finally:
                self.browser_window = None

    def is_browser_visible(self) -> bool:
        """
        Verifica si el navegador está visible.

        Returns:
            True si el navegador existe y está visible
        """
        return self.browser_window is not None and self.browser_window.isVisible()

    def set_main_window(self, main_window):
        """
        Establece la referencia a MainWindow para posicionamiento.

        Args:
            main_window: Referencia a MainWindow
        """
        self.main_window = main_window
        logger.debug("MainWindow reference set in SimpleBrowserManager")

    # ==================== Configuración ====================

    def load_home_url(self) -> str:
        """
        Carga la URL home desde la configuración.

        Returns:
            URL home configurada, o default si no existe
        """
        if self._home_url:
            return self._home_url

        try:
            # Intentar cargar desde base de datos
            config = self.db.get_browser_config()
            if config and 'home_url' in config:
                self._home_url = config['home_url']
                logger.info(f"URL home cargada desde DB: {self._home_url}")
            else:
                # Usar default y guardar
                self._home_url = "https://www.google.com"
                self.save_home_url(self._home_url)
                logger.info(f"Usando URL home por defecto: {self._home_url}")

        except Exception as e:
            logger.error(f"Error al cargar home_url: {e}")
            self._home_url = "https://www.google.com"

        return self._home_url

    def save_home_url(self, url: str):
        """
        Guarda la URL home en la configuración.

        Args:
            url: Nueva URL home
        """
        try:
            self._home_url = url
            self.db.save_browser_config({'home_url': url})
            logger.info(f"URL home guardada: {url}")

        except Exception as e:
            logger.error(f"Error al guardar home_url: {e}")

    def set_home_url(self, url: str):
        """
        Establece una nueva URL home y la guarda.

        Args:
            url: Nueva URL home
        """
        self.save_home_url(url)

        # Si el navegador está abierto, actualizar
        if self.browser_window and self.browser_window.isVisible():
            self.browser_window.load_url(url)

    def get_current_url(self) -> Optional[str]:
        """
        Obtiene la URL actual del navegador.

        Returns:
            URL actual o None si el navegador no está abierto
        """
        if self.browser_window:
            return self.browser_window.url_bar.text()
        return None

    # ==================== Slots ====================

    def _on_browser_closed(self):
        """Handler cuando se cierra la ventana del navegador."""
        logger.info("Ventana del navegador cerrada por el usuario")
        # No destruir la instancia, solo ocultarla para reuso rápido
        # self.browser_window = None  # Opcional: descomentar para liberar memoria

    # ==================== Cleanup ====================

    def cleanup(self):
        """
        Limpieza de recursos al cerrar la aplicación.

        Debe llamarse desde MainController al cerrar.
        """
        logger.info("Limpiando SimpleBrowserManager")

        if self.browser_window:
            self.close_browser()

        # Limpiar profile manager
        if self.profile_manager:
            self.profile_manager.cleanup()

        logger.info("SimpleBrowserManager limpiado")
