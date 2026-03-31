"""地图生成器"""
import random
from typing import List
from models.hexagon import Hexagon, HexMap
from models.resource import TerrainType

class MapGenerator:
    """卡坦岛地图生成器"""
    
    # 标准卡坦岛地形配置（19个六边形）
    STANDARD_TERRAINS = [
        TerrainType.FOREST,      # 森林 x4
        TerrainType.FOREST,
        TerrainType.FOREST,
        TerrainType.FOREST,
        TerrainType.PASTURE,     # 牧场 x4
        TerrainType.PASTURE,
        TerrainType.PASTURE,
        TerrainType.PASTURE,
        TerrainType.FIELDS,      # 农田 x4
        TerrainType.FIELDS,
        TerrainType.FIELDS,
        TerrainType.FIELDS,
        TerrainType.HILLS,       # 山丘 x3
        TerrainType.HILLS,
        TerrainType.HILLS,
        TerrainType.MOUNTAINS,   # 山脉 x3
        TerrainType.MOUNTAINS,
        TerrainType.MOUNTAINS,
        TerrainType.DESERT,      # 沙漠 x1
    ]
    
    # 标准骰子点数配置（18个数字，沙漠没有）
    STANDARD_NUMBERS = [
        2,                       # 最少 x1
        3, 3,                    # x2
        4, 4,                    # x2
        5, 5,                    # x2
        6, 6,                    # x2
        8, 8,                    # x2
        9, 9,                    # x2
        10, 10,                  # x2
        11, 11,                  # x2
        12,                      # 最少 x1
    ]
    
    # 标准地图的坐标布局（轴向坐标系）
    STANDARD_POSITIONS = [
        # 中心
        (0, 0),
        # 第一圈（6个）
        (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1),
        # 第二圈（12个）
        (2, -2), (2, -1), (2, 0), (1, 1), (0, 2), (-1, 2),
        (-2, 2), (-2, 1), (-2, 0), (-1, -1), (0, -2), (1, -2),
    ]
    
    @staticmethod
    def generate_standard_map(random_seed: int = None) -> HexMap:
        """
        生成标准的卡坦岛地图（19个六边形）
        
        Args:
            random_seed: 随机种子，用于生成可复现的地图
            
        Returns:
            HexMap: 生成的地图
        """
        if random_seed is not None:
            random.seed(random_seed)
        
        # 打乱地形
        terrains = MapGenerator.STANDARD_TERRAINS.copy()
        random.shuffle(terrains)
        
        # 打乱数字
        numbers = MapGenerator.STANDARD_NUMBERS.copy()
        random.shuffle(numbers)
        
        # 创建地图
        hex_map = HexMap()
        number_index = 0
        
        for i, (q, r) in enumerate(MapGenerator.STANDARD_POSITIONS):
            terrain = terrains[i]
            
            # 沙漠没有数字
            if terrain == TerrainType.DESERT:
                number = None
            else:
                number = numbers[number_index]
                number_index += 1
            
            hexagon = Hexagon(q, r, terrain, number)
            hex_map.add_hexagon(hexagon)
        
        return hex_map
    
    @staticmethod
    def generate_balanced_map(random_seed: int = None) -> HexMap:
        """
        生成平衡的地图（确保资源和点数分布更均匀）
        
        这个版本会尝试避免高产点数（6、8）聚集在一起
        """
        if random_seed is not None:
            random.seed(random_seed)
        
        hex_map = HexMap()
        
        # 首先确定沙漠的位置（通常在中心或接近中心）
        desert_positions = [(0, 0), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]
        desert_pos = random.choice(desert_positions)
        
        # 分离高产数字（6和8）和其他数字
        high_numbers = [6, 6, 8, 8]
        normal_numbers = [2, 3, 3, 4, 4, 5, 5, 9, 9, 10, 10, 11, 11, 12]
        
        random.shuffle(high_numbers)
        random.shuffle(normal_numbers)
        
        # 非沙漠地形
        non_desert_terrains = [t for t in MapGenerator.STANDARD_TERRAINS if t != TerrainType.DESERT]
        random.shuffle(non_desert_terrains)
        
        terrain_index = 0
        high_index = 0
        normal_index = 0
        
        for q, r in MapGenerator.STANDARD_POSITIONS:
            if (q, r) == desert_pos:
                # 放置沙漠
                hexagon = Hexagon(q, r, TerrainType.DESERT, None)
            else:
                terrain = non_desert_terrains[terrain_index]
                terrain_index += 1
                
                # 高产数字不要聚集：检查相邻位置
                neighbors_high = MapGenerator._count_high_neighbors(hex_map, q, r)
                
                if neighbors_high < 2 and high_index < len(high_numbers):
                    # 可以放置高产数字
                    number = high_numbers[high_index]
                    high_index += 1
                else:
                    # 放置普通数字
                    number = normal_numbers[normal_index]
                    normal_index += 1
                
                hexagon = Hexagon(q, r, terrain, number)
            
            hex_map.add_hexagon(hexagon)
        
        # 如果还有剩余的高产数字，随机放置
        for remaining_high in high_numbers[high_index:]:
            if normal_index < len(normal_numbers):
                # 找一个位置交换
                for hexagon in hex_map.hexagons:
                    if hexagon.number == normal_numbers[normal_index]:
                        hexagon.number = remaining_high
                        normal_index += 1
                        break
        
        return hex_map
    
    @staticmethod
    def _count_high_neighbors(hex_map: HexMap, q: int, r: int) -> int:
        """计算相邻位置有多少个高产数字（6或8）"""
        neighbors = hex_map.get_neighbors(q, r)
        count = 0
        for neighbor in neighbors:
            if neighbor.number in [6, 8]:
                count += 1
        return count
    
    @staticmethod
    def generate_simple_map() -> HexMap:
        """生成一个简单的测试地图（7个六边形）"""
        hex_map = HexMap()
        
        # 中心 + 周围6个
        terrains = [
            TerrainType.DESERT,
            TerrainType.FOREST,
            TerrainType.HILLS,
            TerrainType.PASTURE,
            TerrainType.FIELDS,
            TerrainType.MOUNTAINS,
            TerrainType.FOREST,
        ]
        
        numbers = [None, 4, 5, 6, 8, 9, 10]
        positions = [(0, 0), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]
        
        for i, (q, r) in enumerate(positions):
            hexagon = Hexagon(q, r, terrains[i], numbers[i])
            hex_map.add_hexagon(hexagon)
        
        return hex_map

