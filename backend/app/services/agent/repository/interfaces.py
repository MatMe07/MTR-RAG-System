# agent/repository/interfaces.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IRepository(ABC):
    """Интерфейс репозитория данных"""
    
    # ===== КАТАЛОГ =====
    @abstractmethod
    def get_catalog(self) -> List[Dict[str, Any]]:
        """Получение всего каталога"""
        pass
    
    @abstractmethod
    def get_card_by_ksm(self, ksm: str) -> Optional[Dict[str, Any]]:
        """Получение карточки по КСМ"""
        pass
    
    @abstractmethod
    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Получение карточки по ID"""
        pass
    
    # ===== СКЛАД =====
    @abstractmethod
    def get_stock_quantity(self, ksm: str) -> Optional[float]:
        """Получение остатка на складе"""
        pass
    
    @abstractmethod
    def get_stock_cost(self, ksm: str) -> Optional[float]:
        """Получение стоимости"""
        pass
    
    # ===== ГРАФ =====
    @abstractmethod
    def get_graph(self) -> Dict[str, Any]:
        """Получение графа объекта"""
        pass
    
    @abstractmethod
    def get_components_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        """Получение компонентов участка"""
        pass
    
    # ===== НОРМАТИВЫ =====
    @abstractmethod
    def get_regulation(self) -> Dict[str, Any]:
        """Получение нормативной базы"""
        pass
    
    # ===== ПОИСК =====
    @abstractmethod
    def search_candidates(self, parsed: Any, limit: int = 40) -> List[Dict[str, Any]]:
        """Поиск кандидатов в каталоге"""
        pass
    
    # ===== УПРАВЛЕНИЕ =====
    @abstractmethod
    def close(self) -> None:
        """Закрытие соединения"""
        pass
