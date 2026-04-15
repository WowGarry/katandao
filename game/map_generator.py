import random
from typing import List, Tuple, Optional
from models.hexagon import Hexagon, HexMap
from models.resource import TerrainType, ResourceType

class MapGenerator:
    """卡坦岛地图生成器"""

    # 1. 统一地形配置 (19个)
    STANDARD_TERRAINS = [
        TerrainType.FOREST] * 4 + [TerrainType.PASTURE] * 4 + \
        [TerrainType.FIELDS] * 4 + [TerrainType.HILLS] * 3 + \
        [TerrainType.MOUNTAINS] * 3 + [TerrainType.DESERT]

    # 2. 统一数字配置 (18个)
    STANDARD_NUMBERS = [2, 12] + [3, 4, 5, 6, 8, 9, 10, 11] * 2

    # 3. 统一港口配置 (9个：5个资源港，4个普通港)
    # 使用 None 表示 3:1 的普通港口
    STANDARD_PORTS = [
        ResourceType.WOOD, ResourceType.BRICK, ResourceType.SHEEP, 
        ResourceType.WHEAT, ResourceType.ORE,
        None, None, None, None 
    ]

    # 4. 标准地图坐标 (轴向坐标系)
    STANDARD_POSITIONS = [
        (0, 0), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1),
        (2, -2), (2, -1), (2, 0), (1, 1), (0, 2), (-1, 2),
        (-2, 2), (-2, 1), (-2, 0), (-1, -1), (0, -2), (1, -2)
    ]

    @staticmethod
    def generate_standard_map(random_seed: int = None) -> HexMap:
        """生成带港口的标准地图"""
        if random_seed is not None:
            random.seed(random_seed)

        # 打乱资源
        terrains = MapGenerator.STANDARD_TERRAINS.copy()
        random.shuffle(terrains)
        
        numbers = MapGenerator.STANDARD_NUMBERS.copy()
        random.shuffle(numbers)
        
        # 打乱港口
        ports_pool = MapGenerator.STANDARD_PORTS.copy()
        random.shuffle(ports_pool)

        hex_map = HexMap()
        number_index = 0
        
        # 筛选最外层坐标（用于放置港口）
        # 逻辑：在半径为 2 的六边形网格中，max(|q|, |r|, |q+r|) == 2 的是边缘
        outer_positions = [pos for pos in MapGenerator.STANDARD_POSITIONS 
                          if max(abs(pos[0]), abs(pos[1]), abs(pos[0] + pos[1])) == 2]
        
        # 随机从边缘选 9 个位置放港口
        port_locations = random.sample(outer_positions, k=len(ports_pool))
        port_assignment = dict(zip(port_locations, ports_pool))

        for q, r in MapGenerator.STANDARD_POSITIONS:
            terrain = terrains.pop()
            
            # 沙漠不分配数字
            num = None
            if terrain != TerrainType.DESERT:
                num = numbers[number_index]
                number_index += 1

            hexagon = Hexagon(q, r, terrain, num)
            
            # 注入港口逻辑
            if (q, r) in port_assignment:
                hexagon.is_port = True
                hexagon.port_type = port_assignment[(q, r)]
            
            hex_map.add_hexagon(hexagon)

        return hex_map

    @staticmethod
    def generate_balanced_map(random_seed: int = None) -> HexMap:
        """生成平衡地图。目前使用标准地图实现，保留接口兼容性。"""
        return MapGenerator.generate_standard_map(random_seed)
