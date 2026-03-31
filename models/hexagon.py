"""六边形地图模型"""
from typing import List, Tuple, Optional
from models.resource import TerrainType, ResourceType, TERRAIN_TO_RESOURCE

class Hexagon:
    """六边形格子"""
    
    def __init__(self, q: int, r: int, terrain: TerrainType, number: Optional[int] = None):
        """
        使用轴向坐标系统 (q, r)
        q: 列坐标
        r: 行坐标
        terrain: 地形类型
        number: 骰子点数 (2-12, 沙漠为None)
        """
        self.q = q
        self.r = r
        self.terrain = terrain
        self.number = number
        self.has_robber = (terrain == TerrainType.DESERT)  # 强盗初始在沙漠
    
    def get_resource(self) -> ResourceType:
        """获取该格子产出的资源"""
        return TERRAIN_TO_RESOURCE[self.terrain]
    
    def get_coordinates(self) -> Tuple[int, int]:
        """获取坐标"""
        return (self.q, self.r)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'q': self.q,
            'r': self.r,
            'terrain': self.terrain.value,
            'resource': self.get_resource().value,
            'number': self.number,
            'has_robber': self.has_robber
        }
    
    def __repr__(self):
        return f"Hex({self.q},{self.r},{self.terrain.value},{self.number})"
    
    def __eq__(self, other):
        if not isinstance(other, Hexagon):
            return False
        return self.q == other.q and self.r == other.r
    
    def __hash__(self):
        return hash((self.q, self.r))

class HexVertex:
    """六边形顶点（用于放置村庄/城市）"""
    
    def __init__(self, q: int, r: int, direction: int):
        """
        direction: 0-5 表示六个顶点
        """
        self.q = q
        self.r = r
        self.direction = direction
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """转换为元组"""
        return (self.q, self.r, self.direction)
    
    def __eq__(self, other):
        if not isinstance(other, HexVertex):
            return False
        return self.q == other.q and self.r == other.r and self.direction == other.direction
    
    def __hash__(self):
        return hash((self.q, self.r, self.direction))
    
    def __repr__(self):
        return f"Vertex({self.q},{self.r},dir{self.direction})"

class HexEdge:
    """六边形边（用于放置道路）"""
    
    def __init__(self, q: int, r: int, direction: int):
        """
        direction: 0-5 表示六条边
        """
        self.q = q
        self.r = r
        self.direction = direction
    
    def to_tuple(self) -> Tuple[int, int, int]:
        """转换为元组"""
        return (self.q, self.r, self.direction)
    
    def __eq__(self, other):
        if not isinstance(other, HexEdge):
            return False
        return self.q == other.q and self.r == other.r and self.direction == other.direction
    
    def __hash__(self):
        return hash((self.q, self.r, self.direction))
    
    def __repr__(self):
        return f"Edge({self.q},{self.r},dir{self.direction})"

class HexMap:
    """六边形地图"""
    
    def __init__(self):
        self.hexagons: List[Hexagon] = []
        self.hexagon_dict = {}  # {(q, r): Hexagon}
    
    def add_hexagon(self, hexagon: Hexagon):
        """添加六边形"""
        self.hexagons.append(hexagon)
        self.hexagon_dict[(hexagon.q, hexagon.r)] = hexagon
    
    def get_hexagon(self, q: int, r: int) -> Optional[Hexagon]:
        """获取指定坐标的六边形"""
        return self.hexagon_dict.get((q, r))
    
    def get_neighbors(self, q: int, r: int) -> List[Hexagon]:
        """获取相邻的六边形"""
        # 六边形的六个相邻方向
        directions = [
            (1, 0), (1, -1), (0, -1),
            (-1, 0), (-1, 1), (0, 1)
        ]
        neighbors = []
        for dq, dr in directions:
            neighbor = self.get_hexagon(q + dq, r + dr)
            if neighbor:
                neighbors.append(neighbor)
        return neighbors
    
    def get_hexagons_by_number(self, number: int) -> List[Hexagon]:
        """获取指定点数的所有六边形"""
        return [h for h in self.hexagons if h.number == number]
    
    def move_robber(self, q: int, r: int) -> bool:
        """移动强盗到指定位置"""
        target = self.get_hexagon(q, r)
        if not target:
            return False
        
        # 移除所有六边形的强盗
        for hexagon in self.hexagons:
            hexagon.has_robber = False
        
        # 放置强盗到新位置
        target.has_robber = True
        return True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'hexagons': [h.to_dict() for h in self.hexagons]
        }
    
    def __repr__(self):
        return f"HexMap({len(self.hexagons)} hexagons)"

