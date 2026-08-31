# src/core/aircraft_manager.py
from typing import Dict, List, Optional
from pathlib import Path
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class AircraftManager:
    """Aircraft type manager"""

    def __init__(self):
        self.aircraft_types = config.get('aircraft_types', ['c172p'])
        self.current_aircraft = self.aircraft_types[0] if self.aircraft_types else None
        logger.info(f"AircraftManager initialized, supported aircraft types: {self.aircraft_types}")

    def get_aircraft_types(self) -> List[str]:
        """Get all supported aircraft types"""
        return self.aircraft_types

    def set_current_aircraft(self, aircraft_type: str) -> bool:
        """Set the current aircraft type"""
        if aircraft_type in self.aircraft_types:
            self.current_aircraft = aircraft_type
            logger.info(f"Switched aircraft type to: {aircraft_type}")
            return True
        else:
            logger.warning(f"Unsupported aircraft type: {aircraft_type}")
            return False

    def get_current_aircraft(self) -> Optional[str]:
        """Get the current aircraft type"""
        return self.current_aircraft

    def get_aircraft_data_path(self, aircraft_type: str) -> Path:
        """Get the aircraft type data path"""
        data_root = Path(__file__).parent.parent.parent / "data"
        return data_root / "raw_documents" / aircraft_type

# Global aircraft manager instance
aircraft_manager = AircraftManager()
