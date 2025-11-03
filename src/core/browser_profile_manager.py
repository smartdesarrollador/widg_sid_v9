"""
Browser Profile Manager - Gestión de perfiles persistentes del navegador
Author: Widget Sidebar Team
Date: 2025-11-03

Este manager gestiona los perfiles de QWebEngine para persistir cookies,
LocalStorage, cache y sesiones de autenticación entre ejecuciones.
"""

import logging
from pathlib import Path
from typing import Optional, Dict
import sys

from PyQt6.QtWebEngineCore import QWebEngineProfile

logger = logging.getLogger(__name__)


class BrowserProfileManager:
    """
    Manager para gestionar perfiles persistentes del navegador.

    Un perfil de navegador contiene:
    - Cookies (autenticación, sesiones)
    - LocalStorage y SessionStorage
    - Cache de archivos
    - Historial de navegación
    - Configuraciones del sitio

    Características:
    - Persistencia automática en disco
    - Múltiples perfiles (similar a Chrome profiles)
    - Perfil por defecto
    - Directorio configurable
    """

    def __init__(self, db_manager):
        """
        Inicializa el manager.

        Args:
            db_manager: Instancia de DBManager para persistencia
        """
        self.db = db_manager
        self.current_profile: Optional[QWebEngineProfile] = None
        self.current_profile_id: Optional[int] = None

        # Determinar directorio base para almacenamiento
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:
            self.base_dir = Path(__file__).parent.parent.parent

        logger.info("BrowserProfileManager inicializado")

    def get_or_create_profile(self, profile_id: int = None) -> Optional[QWebEngineProfile]:
        """
        Obtiene o crea un perfil de navegador persistente.

        Args:
            profile_id: ID del perfil a cargar (None = perfil por defecto)

        Returns:
            QWebEngineProfile: Perfil persistente o None si falla
        """
        try:
            # Si no se especifica ID, usar perfil por defecto
            if profile_id is None:
                profile_data = self.db.get_default_profile()
                if not profile_data:
                    logger.error("No se encontró perfil por defecto")
                    return None
                profile_id = profile_data['id']
            else:
                profile_data = self.db.get_profile_by_id(profile_id)
                if not profile_data:
                    logger.error(f"Perfil {profile_id} no encontrado")
                    return None

            # Si ya tenemos el perfil cargado, reutilizarlo
            if self.current_profile and self.current_profile_id == profile_id:
                logger.debug(f"Reutilizando perfil cargado: {profile_data['name']}")
                return self.current_profile

            # Crear nuevo perfil persistente
            profile_name = profile_data['name']
            storage_path = profile_data['storage_path']

            # Crear directorio de almacenamiento si no existe
            full_storage_path = self.base_dir / storage_path
            full_storage_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Creando perfil persistente: {profile_name}")
            logger.info(f"  Storage path: {full_storage_path}")

            # Crear QWebEngineProfile persistente
            # IMPORTANTE: El nombre del perfil debe ser único
            profile = QWebEngineProfile(profile_name)

            # Configurar path de almacenamiento persistente
            profile.setPersistentStoragePath(str(full_storage_path))
            profile.setCachePath(str(full_storage_path / "cache"))

            # Habilitar persistencia de cookies
            profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
            )

            # Configurar user agent (opcional)
            # profile.setHttpUserAgent("Custom User Agent")

            # Actualizar last_used en la base de datos
            self.db.update_profile_last_used(profile_id)

            # Guardar referencia
            self.current_profile = profile
            self.current_profile_id = profile_id

            logger.info(f"Perfil '{profile_name}' cargado exitosamente")
            return profile

        except Exception as e:
            logger.error(f"Error al crear perfil: {e}", exc_info=True)
            return None

    def get_current_profile(self) -> Optional[QWebEngineProfile]:
        """
        Obtiene el perfil actualmente cargado.

        Returns:
            QWebEngineProfile: Perfil actual o None
        """
        return self.current_profile

    def switch_profile(self, profile_id: int) -> Optional[QWebEngineProfile]:
        """
        Cambia a un perfil diferente.

        Args:
            profile_id: ID del nuevo perfil

        Returns:
            QWebEngineProfile: Nuevo perfil o None si falla
        """
        logger.info(f"Cambiando a perfil {profile_id}")

        # Limpiar perfil actual
        if self.current_profile:
            # El perfil anterior se liberará automáticamente
            # cuando no haya más referencias a él
            pass

        # Cargar nuevo perfil
        return self.get_or_create_profile(profile_id)

    def create_new_profile(self, name: str) -> Optional[int]:
        """
        Crea un nuevo perfil de navegador.

        Args:
            name: Nombre del perfil

        Returns:
            int: ID del perfil creado o None si falla
        """
        try:
            profile_id = self.db.add_browser_profile(name)

            if profile_id:
                logger.info(f"Nuevo perfil creado: {name} (ID: {profile_id})")
            else:
                logger.error(f"Error al crear perfil: {name}")

            return profile_id

        except Exception as e:
            logger.error(f"Error al crear perfil: {e}")
            return None

    def delete_profile(self, profile_id: int, delete_data: bool = True) -> bool:
        """
        Elimina un perfil.

        Args:
            profile_id: ID del perfil a eliminar
            delete_data: Si True, elimina también los datos en disco

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # Verificar que no sea el perfil actual
            if self.current_profile_id == profile_id:
                logger.warning("No se puede eliminar el perfil actual")
                return False

            # Obtener datos del perfil antes de eliminar
            if delete_data:
                profile_data = self.db.get_profile_by_id(profile_id)
                if profile_data:
                    storage_path = self.base_dir / profile_data['storage_path']
                    if storage_path.exists():
                        import shutil
                        shutil.rmtree(storage_path)
                        logger.info(f"Datos del perfil eliminados: {storage_path}")

            # Eliminar de la base de datos
            success = self.db.delete_browser_profile(profile_id)

            if success:
                logger.info(f"Perfil {profile_id} eliminado")

            return success

        except Exception as e:
            logger.error(f"Error al eliminar perfil: {e}")
            return False

    def get_all_profiles(self) -> list:
        """
        Obtiene lista de todos los perfiles.

        Returns:
            list: Lista de diccionarios con datos de perfiles
        """
        return self.db.get_browser_profiles()

    def set_default_profile(self, profile_id: int) -> bool:
        """
        Establece un perfil como predeterminado.

        Args:
            profile_id: ID del perfil

        Returns:
            bool: True si se estableció correctamente
        """
        return self.db.set_default_profile(profile_id)

    def clear_profile_data(self, profile_id: int = None) -> bool:
        """
        Limpia los datos de un perfil (cookies, cache, etc).

        Args:
            profile_id: ID del perfil (None = perfil actual)

        Returns:
            bool: True si se limpió correctamente
        """
        try:
            if profile_id is None:
                profile_id = self.current_profile_id

            if profile_id is None:
                logger.warning("No hay perfil para limpiar")
                return False

            profile_data = self.db.get_profile_by_id(profile_id)
            if not profile_data:
                logger.error(f"Perfil {profile_id} no encontrado")
                return False

            storage_path = self.base_dir / profile_data['storage_path']

            if storage_path.exists():
                import shutil
                # Eliminar y recrear el directorio
                shutil.rmtree(storage_path)
                storage_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Datos del perfil limpiados: {storage_path}")

            return True

        except Exception as e:
            logger.error(f"Error al limpiar datos del perfil: {e}")
            return False

    def get_profile_size(self, profile_id: int) -> int:
        """
        Calcula el tamaño en disco de un perfil.

        Args:
            profile_id: ID del perfil

        Returns:
            int: Tamaño en bytes
        """
        try:
            profile_data = self.db.get_profile_by_id(profile_id)
            if not profile_data:
                return 0

            storage_path = self.base_dir / profile_data['storage_path']

            if not storage_path.exists():
                return 0

            total_size = 0
            for item in storage_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size

            return total_size

        except Exception as e:
            logger.error(f"Error al calcular tamaño del perfil: {e}")
            return 0

    def cleanup(self):
        """Limpieza de recursos al cerrar la aplicación."""
        logger.info("Limpiando BrowserProfileManager")

        if self.current_profile:
            # El perfil se liberará automáticamente
            self.current_profile = None
            self.current_profile_id = None

        logger.info("BrowserProfileManager limpiado")
