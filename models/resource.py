"""资源定义"""
from enum import Enum
from typing import Dict

class ResourceType(Enum):
    """资源类型"""
    WOOD = "wood"           # 木材
    BRICK = "brick"         # 砖块
    SHEEP = "sheep"         # 羊毛
    WHEAT = "wheat"         # 小麦
    ORE = "ore"             # 矿石
    DESERT = "desert"       # 沙漠（无资源）

class TerrainType(Enum):
    """地形类型"""
    FOREST = "forest"       # 森林 -> 木材
    HILLS = "hills"         # 山丘 -> 砖块
    PASTURE = "pasture"     # 牧场 -> 羊毛
    FIELDS = "fields"       # 农田 -> 小麦
    MOUNTAINS = "mountains" # 山脉 -> 矿石
    DESERT = "desert"       # 沙漠 -> 无资源

# 地形与资源的映射
TERRAIN_TO_RESOURCE = {
    TerrainType.FOREST: ResourceType.WOOD,
    TerrainType.HILLS: ResourceType.BRICK,
    TerrainType.PASTURE: ResourceType.SHEEP,
    TerrainType.FIELDS: ResourceType.WHEAT,
    TerrainType.MOUNTAINS: ResourceType.ORE,
    TerrainType.DESERT: ResourceType.DESERT,
}

class Resources:
    """资源集合类"""
    
    def __init__(self, wood=0, brick=0, sheep=0, wheat=0, ore=0):
        self.resources = {
            ResourceType.WOOD: wood,
            ResourceType.BRICK: brick,
            ResourceType.SHEEP: sheep,
            ResourceType.WHEAT: wheat,
            ResourceType.ORE: ore,
        }
    
    def add(self, resource_type: ResourceType, amount: int = 1):
        """添加资源"""
        if resource_type == ResourceType.DESERT:
            return
        self.resources[resource_type] += amount
    
    def remove(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """移除资源，返回是否成功"""
        if resource_type == ResourceType.DESERT:
            return False
        if self.resources[resource_type] >= amount:
            self.resources[resource_type] -= amount
            return True
        return False
    
    def has(self, resource_dict: Dict[ResourceType, int]) -> bool:
        """检查是否有足够的资源"""
        for resource_type, amount in resource_dict.items():
            if resource_type == ResourceType.DESERT:
                continue
            if self.resources[resource_type] < amount:
                return False
        return True
    
    def get(self, resource_type: ResourceType) -> int:
        """获取资源数量"""
        if resource_type == ResourceType.DESERT:
            return 0
        return self.resources[resource_type]
    
    def total(self) -> int:
        """获取资源总数"""
        return sum(self.resources.values())
    
    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {rt.value: amount for rt, amount in self.resources.items()}
    
    @staticmethod
    def from_dict(data: Dict[str, int]) -> 'Resources':
        """从字典创建"""
        return Resources(
            wood=data.get('wood', 0),
            brick=data.get('brick', 0),
            sheep=data.get('sheep', 0),
            wheat=data.get('wheat', 0),
            ore=data.get('ore', 0)
        )
    
    def __repr__(self):
        return f"Resources({self.to_dict()})"

