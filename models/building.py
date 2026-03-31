"""建筑模型"""
from enum import Enum
from typing import Dict
from models.resource import ResourceType

class BuildingType(Enum):
    """建筑类型"""
    ROAD = "road"               # 道路
    SETTLEMENT = "settlement"   # 村庄
    CITY = "city"               # 城市

# 建筑成本
BUILDING_COSTS = {
    BuildingType.ROAD: {
        ResourceType.WOOD: 1,
        ResourceType.BRICK: 1,
    },
    BuildingType.SETTLEMENT: {
        ResourceType.WOOD: 1,
        ResourceType.BRICK: 1,
        ResourceType.SHEEP: 1,
        ResourceType.WHEAT: 1,
    },
    BuildingType.CITY: {
        ResourceType.WHEAT: 2,
        ResourceType.ORE: 3,
    },
}

# 建筑提供的胜利点
BUILDING_POINTS = {
    BuildingType.ROAD: 0,
    BuildingType.SETTLEMENT: 1,
    BuildingType.CITY: 2,
}

class Building:
    """建筑类"""
    
    def __init__(self, building_type: BuildingType, player_id: int, position: tuple):
        self.type = building_type
        self.player_id = player_id
        self.position = position  # (x, y) 或 (x1, y1, x2, y2) 对于道路
    
    def get_points(self) -> int:
        """获取胜利点"""
        return BUILDING_POINTS[self.type]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'type': self.type.value,
            'player_id': self.player_id,
            'position': self.position,
            'points': self.get_points()
        }
    
    @staticmethod
    def get_cost(building_type: BuildingType) -> Dict[ResourceType, int]:
        """获取建筑成本"""
        if building_type not in BUILDING_COSTS:
            raise ValueError(f"未知的建筑类型: {building_type}")
        return BUILDING_COSTS[building_type]
    
    
    def __repr__(self):
        return f"Building({self.type.value}, P{self.player_id}, {self.position})"

