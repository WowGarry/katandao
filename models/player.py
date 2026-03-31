"""玩家模型"""
from typing import Dict, List
from models.resource import Resources, ResourceType
from models.building import Building, BuildingType

class Player:
    """玩家类"""
    
    def __init__(self, player_id: int, name: str, color: str, is_ai: bool = False):
        self.player_id = player_id
        self.name = name
        self.color = color
        self.is_ai = is_ai  # 是否为AI玩家
        self.resources = Resources()
        self.buildings: List[Building] = []
        self.victory_points = 0
        
        # 建筑数量限制
        self.roads_left = 15
        self.settlements_left = 5
        self.cities_left = 4
        
        # 特殊卡片
        self.has_longest_road = False
        self.has_largest_army = False
    
    def add_resource(self, resource_type: ResourceType, amount: int = 1):
        """添加资源"""
        self.resources.add(resource_type, amount)
    
    def remove_resource(self, resource_type: ResourceType, amount: int = 1) -> bool:
        """移除资源"""
        return self.resources.remove(resource_type, amount)
    
    def has_resources(self, cost: Dict[ResourceType, int]) -> bool:
        """检查是否有足够的资源"""
        return self.resources.has(cost)
    
    def pay_resources(self, cost: Dict[ResourceType, int]) -> bool:
        """支付资源"""
        if not self.has_resources(cost):
            return False
        for resource_type, amount in cost.items():
            self.resources.remove(resource_type, amount)
        return True
    
    def add_building(self, building: Building):
        """添加建筑"""
        self.buildings.append(building)
        
        # 减少可用建筑数量
        if building.type == BuildingType.ROAD:
            self.roads_left -= 1
        elif building.type == BuildingType.SETTLEMENT:
            self.settlements_left -= 1
        elif building.type == BuildingType.CITY:
            self.cities_left -= 1
        
        # 更新胜利点
        self.update_victory_points()
    
    def can_build(self, building_type: BuildingType) -> bool:
        """检查是否可以建造"""
        if building_type == BuildingType.ROAD:
            return self.roads_left > 0
        elif building_type == BuildingType.SETTLEMENT:
            return self.settlements_left > 0
        elif building_type == BuildingType.CITY:
            return self.cities_left > 0
        return False
    
    def update_victory_points(self):
        """更新胜利点"""
        # 计算建筑点数
        building_points = sum(b.get_points() for b in self.buildings)
        
        # 计算特殊点数
        special_points = 0
        if self.has_longest_road:
            special_points += 2
        if self.has_largest_army:
            special_points += 2
        
        self.victory_points = building_points + special_points
    
    def get_settlements(self) -> List[Building]:
        """获取所有村庄"""
        return [b for b in self.buildings if b.type == BuildingType.SETTLEMENT]
    
    def get_cities(self) -> List[Building]:
        """获取所有城市"""
        return [b for b in self.buildings if b.type == BuildingType.CITY]
    
    def get_roads(self) -> List[Building]:
        """获取所有道路"""
        return [b for b in self.buildings if b.type == BuildingType.ROAD]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'player_id': self.player_id,
            'name': self.name,
            'color': self.color,
            'is_ai': self.is_ai,
            'resources': self.resources.to_dict(),
            'resource_count': self.resources.total(),
            'buildings': [b.to_dict() for b in self.buildings],
            'victory_points': self.victory_points,
            'roads_left': self.roads_left,
            'settlements_left': self.settlements_left,
            'cities_left': self.cities_left,
            'has_longest_road': self.has_longest_road,
            'has_largest_army': self.has_largest_army
        }
    
    def __repr__(self):
        return f"Player({self.player_id}, {self.name}, VP:{self.victory_points})"

