"""游戏状态管理"""
from typing import List, Dict, Optional
from models.player import Player
from models.hexagon import HexMap, HexVertex, HexEdge
from models.building import Building, BuildingType
from models.resource import ResourceType

class GamePhase:
    """游戏阶段"""
    SETUP = "setup"               # 初始放置阶段
    ROLL_DICE = "roll_dice"       # 掷骰子
    DISCARD = "discard"           # 弃牌（掷到7且手牌>7）
    MOVE_ROBBER = "move_robber"   # 移动强盗
    TRADE = "trade"               # 交易阶段
    BUILD = "build"               # 建造阶段
    END_TURN = "end_turn"         # 结束回合

class GameState:
    """游戏状态"""
    
    def __init__(self, game_id: str, player_count: int = 4):
        self.game_id = game_id
        self.player_count = player_count
        self.players: List[Player] = []
        self.hex_map: Optional[HexMap] = None
        
        # 游戏进度
        self.current_player_index = 0
        self.round_number = 0
        self.phase = GamePhase.SETUP  # 初始设置阶段
        self.is_finished = False
        self.winner_id: Optional[int] = None
        
        # 建筑位置记录（用于检查合法性）
        self.vertex_buildings: Dict[tuple, Building] = {}  # {(q,r,dir): Building}
        self.edge_buildings: Dict[tuple, Building] = {}    # {(q,r,dir): Building}
        
        # 最近的骰子结果
        self.last_dice_roll: Optional[tuple] = None
        
        # 设置阶段的特殊状态
        self.setup_round = 0  # 0: 第一轮正向, 1: 第二轮反向
        self.setup_settlements_placed = {}  # {player_id: count}
    
    def add_player(self, player: Player):
        """添加玩家"""
        self.players.append(player)
        self.setup_settlements_placed[player.player_id] = 0
    
    def get_current_player(self) -> Player:
        """获取当前玩家"""
        return self.players[self.current_player_index]
    
    def get_player(self, player_id: int) -> Optional[Player]:
        """根据ID获取玩家"""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None
    
    def next_turn(self):
        """进入下一个回合"""
        if self.phase == GamePhase.SETUP:
            self._next_setup_turn()
        else:
            self.current_player_index = (self.current_player_index + 1) % self.player_count
            if self.current_player_index == 0:
                self.round_number += 1
            self.phase = GamePhase.ROLL_DICE
    
    def _next_setup_turn(self):
        """设置阶段的下一回合"""
        current_player = self.get_current_player()
        settlements_count = self.setup_settlements_placed[current_player.player_id]
        
        if settlements_count < 1:
            # 还在放置第一个村庄+道路
            return
        
        if self.setup_round == 0:
            # 第一轮：正向
            if self.current_player_index < self.player_count - 1:
                self.current_player_index += 1
            else:
                # 最后一个玩家，进入第二轮
                self.setup_round = 1
        else:
            # 第二轮：反向
            current_player_settlements = self.setup_settlements_placed[current_player.player_id]
            if current_player_settlements >= 2:
                if self.current_player_index > 0:
                    self.current_player_index -= 1
                else:
                    # 设置阶段结束
                    self.phase = GamePhase.ROLL_DICE
                    self.current_player_index = 0
                    self.round_number = 1
    
    def check_winner(self) -> Optional[Player]:
        """检查是否有玩家获胜（10分）"""
        for player in self.players:
            if player.victory_points >= 10:
                self.is_finished = True
                self.winner_id = player.player_id
                return player
        return None
    
    def can_place_settlement(self, vertex: HexVertex, player_id: int) -> bool:
        """检查是否可以放置村庄"""
        vertex_tuple = vertex.to_tuple()
        
        # 检查该位置是否已有建筑
        if vertex_tuple in self.vertex_buildings:
            return False
        
        # 检查距离规则：相邻顶点不能有建筑
        adjacent_vertices = self._get_adjacent_vertices(vertex)
        for adj_vertex in adjacent_vertices:
            if adj_vertex.to_tuple() in self.vertex_buildings:
                return False
        
        # 非设置阶段需要检查是否连接到道路
        if self.phase != GamePhase.SETUP:
            if not self._has_adjacent_road(vertex, player_id):
                return False
        
        return True
    
    def can_place_city(self, vertex: HexVertex, player_id: int) -> bool:
        """检查是否可以将村庄升级为城市"""
        vertex_tuple = vertex.to_tuple()
        
        # 必须已有该玩家的村庄
        if vertex_tuple not in self.vertex_buildings:
            return False
        
        building = self.vertex_buildings[vertex_tuple]
        if building.player_id != player_id or building.type != BuildingType.SETTLEMENT:
            return False
        
        return True
    
    def can_place_road(self, edge: HexEdge, player_id: int) -> bool:
        """检查是否可以放置道路"""
        edge_tuple = edge.to_tuple()
        
        # 检查该位置是否已有道路
        if edge_tuple in self.edge_buildings:
            return False
        
        # 检查是否连接到玩家的建筑或道路
        if not self._is_road_connected(edge, player_id):
            return False
        
        return True
    
    def _get_adjacent_vertices(self, vertex: HexVertex) -> List[HexVertex]:
        """获取相邻的顶点"""
        # 简化实现：返回同一六边形的相邻顶点
        q, r, direction = vertex.q, vertex.r, vertex.direction
        adjacent = []
        
        # 相邻顶点（顺时针和逆时针）
        adjacent.append(HexVertex(q, r, (direction + 1) % 6))
        adjacent.append(HexVertex(q, r, (direction - 1) % 6))
        
        return adjacent
    
    def _has_adjacent_road(self, vertex: HexVertex, player_id: int) -> bool:
        """检查顶点是否有相邻的道路"""
        # 简化实现
        for edge in self.edge_buildings.values():
            if edge.player_id == player_id:
                # 简单判断：如果道路的坐标接近顶点
                if (edge.position[0] == vertex.q and edge.position[1] == vertex.r):
                    return True
        return True  # 暂时允许
    
    def _is_road_connected(self, edge: HexEdge, player_id: int) -> bool:
        """检查道路是否连接到玩家的建筑或道路"""
        # 设置阶段，必须连接到刚放置的村庄
        if self.phase == GamePhase.SETUP:
            return True  # 简化：允许放置
        
        # 正常阶段，检查连接
        return True  # 简化：允许放置
    
    def place_settlement(self, vertex: HexVertex, player_id: int) -> bool:
        """放置村庄"""
        if not self.can_place_settlement(vertex, player_id):
            return False
        
        player = self.get_player(player_id)
        if not player or not player.can_build(BuildingType.SETTLEMENT):
            return False
        
        # 创建建筑
        building = Building(BuildingType.SETTLEMENT, player_id, vertex.to_tuple())
        self.vertex_buildings[vertex.to_tuple()] = building
        player.add_building(building)
        
        # 设置阶段记录
        if self.phase == GamePhase.SETUP:
            self.setup_settlements_placed[player_id] += 1
        
        return True
    
    def place_city(self, vertex: HexVertex, player_id: int) -> bool:
        """将村庄升级为城市"""
        if not self.can_place_city(vertex, player_id):
            return False
        
        player = self.get_player(player_id)
        if not player or not player.can_build(BuildingType.CITY):
            return False
        
        vertex_tuple = vertex.to_tuple()
        old_building = self.vertex_buildings[vertex_tuple]
        
        # 移除旧建筑，添加新建筑
        player.buildings.remove(old_building)
        player.settlements_left += 1  # 归还村庄
        
        new_building = Building(BuildingType.CITY, player_id, vertex_tuple)
        self.vertex_buildings[vertex_tuple] = new_building
        player.add_building(new_building)
        
        return True
    
    def place_road(self, edge: HexEdge, player_id: int) -> bool:
        """放置道路"""
        if not self.can_place_road(edge, player_id):
            return False
        
        player = self.get_player(player_id)
        if not player or not player.can_build(BuildingType.ROAD):
            return False
        
        building = Building(BuildingType.ROAD, player_id, edge.to_tuple())
        self.edge_buildings[edge.to_tuple()] = building
        player.add_building(building)
        
        return True
    
    def distribute_resources(self, dice_sum: int):
        """根据骰子结果分配资源"""
        if not self.hex_map:
            return
        
        # 获取该点数的所有六边形
        hexagons = self.hex_map.get_hexagons_by_number(dice_sum)
        
        for hexagon in hexagons:
            # 如果有强盗，不产出资源
            if hexagon.has_robber:
                continue
            
            resource = hexagon.get_resource()
            if resource == ResourceType.DESERT:
                continue
            
            # 找到该六边形相邻的所有建筑
            for building in self.vertex_buildings.values():
                # 简化：检查建筑是否在该六边形附近
                if self._is_building_adjacent_to_hex(building, hexagon.q, hexagon.r):
                    player = self.get_player(building.player_id)
                    if building.type == BuildingType.SETTLEMENT:
                        player.add_resource(resource, 1)
                    elif building.type == BuildingType.CITY:
                        player.add_resource(resource, 2)
    
    def _is_building_adjacent_to_hex(self, building: Building, q: int, r: int) -> bool:
        """检查建筑是否在六边形旁边"""
        if building.type == BuildingType.ROAD:
            return False
        
        # 简化：检查坐标
        bq, br, _ = building.position
        return bq == q and br == r
    
    def to_dict(self) -> dict:
        """转换为字典"""
        # 将建筑位置转换为可读的格式
        vertex_buildings_dict = {}
        for pos, building in self.vertex_buildings.items():
            building_dict = building.to_dict()
            building_dict['position'] = list(pos)  # 确保position是列表
            key = f"{pos[0]},{pos[1]},{pos[2]}"
            vertex_buildings_dict[key] = building_dict
        
        edge_buildings_dict = {}
        for pos, building in self.edge_buildings.items():
            building_dict = building.to_dict()
            building_dict['position'] = list(pos)  # 确保position是列表
            key = f"{pos[0]},{pos[1]},{pos[2]}"
            edge_buildings_dict[key] = building_dict
        
        return {
            'game_id': self.game_id,
            'player_count': self.player_count,
            'players': [p.to_dict() for p in self.players],
            'hex_map': self.hex_map.to_dict() if self.hex_map else None,
            'current_player_id': self.get_current_player().player_id,
            'round_number': self.round_number,
            'phase': self.phase,
            'is_finished': self.is_finished,
            'winner_id': self.winner_id,
            'last_dice_roll': self.last_dice_roll,
            'vertex_buildings': vertex_buildings_dict,
            'edge_buildings': edge_buildings_dict,
        }

