"""
Equipment Service - Mock version
"""

from typing import Dict, List, Optional, Tuple

class EquipmentService:
    def __init__(self, db=None):
        self.db = db
    
    async def get_equipments(self, page: int = 1, size: int = 10, status_filter: str = None, manufacturer_filter: str = None) -> Tuple[List[Dict], int]:
        equipments = [
            {
                "id": 1,
                "tag_reference": "21REL001",
                "serial_number": "P143-001", 
                "firmware_version": "2.15",
                "installation_date": "2023-01-15T00:00:00",
                "location": "Subestacao Principal",
                "status": "active",
                "model": {
                    "manufacturer": {"name": "Schneider Electric"},
                    "model_type": "MiCOM P143"
                }
            },
            {
                "id": 2,
                "tag_reference": "21REL002",
                "serial_number": "P3-002",
                "firmware_version": "1.8.5", 
                "installation_date": "2023-02-20T00:00:00",
                "location": "Subestacao Auxiliar",
                "status": "active",
                "model": {
                    "manufacturer": {"name": "Schneider Electric"},
                    "model_type": "Easergy P3"
                }
            }
        ]
        return equipments, len(equipments)
    
    async def get_equipment_by_id(self, equipment_id: int) -> Optional[Dict]:
        equipments, _ = await self.get_equipments()
        for eq in equipments:
            if eq["id"] == equipment_id:
                return eq
        return None
    
    async def create_equipment(self, equipment_data: Dict) -> Dict:
        return {"id": 999, "message": "Equipment created", "data": equipment_data}
    
    async def update_equipment(self, equipment_id: int, update_data: Dict) -> Optional[Dict]:
        return {"id": equipment_id, "message": "Equipment updated", "data": update_data}
    
    async def delete_equipment(self, equipment_id: int) -> bool:
        return True
    
    async def get_electrical_configuration(self, equipment_id: int) -> Optional[Dict]:
        return {
            "phase_ct_primary": 600,
            "phase_ct_secondary": 5,
            "vt_primary": 13800,
            "vt_secondary": 115,
            "nominal_voltage": 13.8,
            "frequency": 60
        }
    
    async def get_protection_functions(self, equipment_id: int) -> List[Dict]:
        return [
            {"function_code": "50", "function_name": "Instantaneous Overcurrent", "enabled": True, "pickup_value": 12.5},
            {"function_code": "51", "function_name": "Time Overcurrent", "enabled": True, "pickup_value": 8.5}
        ]
    
    async def get_io_configuration(self, equipment_id: int) -> List[Dict]:
        return [
            {"channel_number": 1, "channel_type": "digital_input", "description": "Breaker Status", "enabled": True},
            {"channel_number": 2, "channel_type": "digital_output", "description": "Trip Command", "enabled": True}
        ]
    
    async def get_equipment_summary(self, equipment_id: int) -> Optional[Dict]:
        equipment = await self.get_equipment_by_id(equipment_id)
        if not equipment:
            return None
        
        return {
            "equipment": equipment,
            "electrical_configuration": await self.get_electrical_configuration(equipment_id),
            "protection_functions": await self.get_protection_functions(equipment_id),
            "io_configuration": await self.get_io_configuration(equipment_id)
        }
