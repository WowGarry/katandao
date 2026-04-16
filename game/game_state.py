"""游戏状态管理"""
from typing import List, Dict, Optional
from models.player import Player
from models.hexagon import HexMap, HexVertex, HexEdge
from models.building import Building, BuildingType
from models.resource import ResourceType, Resources

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
        self.setup_pending_road = False
        self.setup_pending_road_player_id: Optional[int] = None
        self.setup_last_settlement_vertex: Optional[HexVertex] = None
    
    def add_player(self, player: Player):
        """添加玩家"""
        # 为测试目的：初始化每个玩家大量资源（每种资源50）
        try:
            player.resources = Resources(4, 4, 4, 4, 4)
        except Exception:
            # 回退到默认构造以防导入问题
            player.resources = Resources()

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
        # 如果有待补路，不转轮，让当前玩家继续用来补路
        if self.setup_pending_road:
            return
        
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

    def _is_road_adjacent_to_vertex(self, edge: HexEdge, vertex: HexVertex) -> bool:
        """检查道路是否与顶点相邻"""
        # 简化：同一六边形上的两个相邻边即可视为连接该顶点
        if edge.q != vertex.q or edge.r != vertex.r:
            return False
        return edge.direction in {vertex.direction, (vertex.direction - 1) % 6}

    def _clear_setup_pending(self):
        self.setup_pending_road = False
        self.setup_pending_road_player_id = None
        self.setup_last_settlement_vertex = None

    def award_setup_resources(self, player_id: int, vertex: HexVertex):
        """在第二个定居点放置后立即发放资源"""
        if not self.hex_map:
            return
        player = self.get_player(player_id)
        if not player:
            return

        adjacent_hexes = self.hex_map.get_hexagons_by_vertex(vertex.q, vertex.r, vertex.direction)
        for hexagon in adjacent_hexes:
            resource = hexagon.get_resource()
            if resource != ResourceType.DESERT:
                player.add_resource(resource, 1)
    
    def can_place_settlement(self, vertex: HexVertex, player_id: int) -> bool:
        """检查是否可以放置村庄"""
        vertex_tuple = vertex.to_tuple()
        print(f"[DEBUG][Game {self.game_id}] can_place_settlement called: player={player_id}, vertex={vertex_tuple}, phase={self.phase}, setup_pending_road={self.setup_pending_road}")

        # 设置阶段未完成当前回合道路前，不允许再放置新村庄
        if self.phase == GamePhase.SETUP and self.setup_pending_road:
            print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> False: setup pending road")
            return False

        # 检查该位置是否已有建筑
        if vertex_tuple in self.vertex_buildings:
            print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> False: vertex already occupied")
            return False
        
        # 检查距离规则：相邻顶点不能有建筑
        adjacent_vertices = self._get_adjacent_vertices(vertex)
        for adj_vertex in adjacent_vertices:
            if adj_vertex.to_tuple() in self.vertex_buildings:
                print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> False: adjacent vertex occupied {adj_vertex.to_tuple()}")
                return False
        
        # 旧逻辑：在非设置阶段要求必须连接到道路。
        # 为了允许在可用节点上自由建造（测试需求），不再强制检查道路连接。
        # 如果需要恢复标准规则，请重新启用下面的道路连接检查。
        # has_road = self._has_adjacent_road(vertex, player_id)
        # if not has_road:
        #     print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> False: no adjacent road for player {player_id}")
        #     return False
        # else:
        #     print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> adjacent road found")
        
        print(f"[DEBUG][Game {self.game_id}] can_place_settlement -> True: placement allowed")
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

        if self.phase == GamePhase.SETUP:
            if not self.setup_pending_road or self.setup_pending_road_player_id != player_id:
                return False
            if not self._is_road_adjacent_to_vertex(edge, self.setup_last_settlement_vertex):
                return False
            return True
        
        # 检查是否连接到玩家的建筑或道路
        if not self._is_road_connected(edge, player_id):
            return False
        
        return True
    
    def _get_adjacent_vertices(self, vertex: HexVertex) -> List[HexVertex]:
        """获取距离为1的所有相邻顶点（距离规则约束）"""
        q, r, direction = vertex.q, vertex.r, vertex.direction
        adjacent = []
        
        # 简化策略：只返回同一六边形内的相邻顶点，加上三个相邻六边形中的对应顶点
        # 同一六边形的两个相邻顶点
        adjacent.append(HexVertex(q, r, (direction + 1) % 6))
        adjacent.append(HexVertex(q, r, (direction - 1) % 6))
        
        # 六边形网格中的相邻六边形 - 基于顶点方向判断相邻的六边形
        # 顶点 direction=0 对应的相邻六边形
        if direction == 0:
            adjacent.append(HexVertex(q + 1, r - 1, 3))  # 东侧六边形的对应顶点
            adjacent.append(HexVertex(q, r - 1, 4))      # 东北侧六边形的对应顶点
        elif direction == 1:
            adjacent.append(HexVertex(q + 1, r - 1, 4))
            adjacent.append(HexVertex(q + 1, r, 5))
        elif direction == 2:
            adjacent.append(HexVertex(q + 1, r, 5))
            adjacent.append(HexVertex(q, r + 1, 0))
        elif direction == 3:
            adjacent.append(HexVertex(q, r + 1, 0))
            adjacent.append(HexVertex(q - 1, r + 1, 1))
        elif direction == 4:
            adjacent.append(HexVertex(q - 1, r + 1, 1))
            adjacent.append(HexVertex(q - 1, r, 2))
        elif direction == 5:
            adjacent.append(HexVertex(q - 1, r, 2))
            adjacent.append(HexVertex(q, r - 1, 3))
        
        # 去重
        seen = set()
        unique = []
        for v in adjacent:
            t = v.to_tuple()
            if t not in seen:
                unique.append(v)
                seen.add(t)
        
        return unique
    
    def _has_adjacent_road(self, vertex: HexVertex, player_id: int) -> bool:
        """检查顶点是否有相邻的道路"""
        # 顶点 (q, r, d) 相邻的两条边是：
        # - 边 (q, r, d)
        # - 边 (q, r, (d-1)%6)
        adjacent_edge_tuples = [
            (vertex.q, vertex.r, vertex.direction),
            (vertex.q, vertex.r, (vertex.direction - 1) % 6)
        ]
        
        for edge_tuple in adjacent_edge_tuples:
            if edge_tuple in self.edge_buildings:
                edge = self.edge_buildings[edge_tuple]
                if edge.player_id == player_id:
                    return True
        return False
    
    def _is_road_connected(self, edge: HexEdge, player_id: int) -> bool:
        """检查道路是否连接到玩家的建筑或道路"""
        # 边 (q, r, d) 的两个端点是：
        # - 顶点1: (q, r, d)
        # - 顶点2: (q, r, (d+1)%6)
        vertex1 = HexVertex(edge.q, edge.r, edge.direction)
        vertex2 = HexVertex(edge.q, edge.r, (edge.direction + 1) % 6)
        
        # 检查顶点1或顶点2是否有玩家的建筑
        v1_tuple = vertex1.to_tuple()
        v2_tuple = vertex2.to_tuple()
        
        # 检查是否有玩家的村庄或城市
        if v1_tuple in self.vertex_buildings:
            if self.vertex_buildings[v1_tuple].player_id == player_id:
                return True
        if v2_tuple in self.vertex_buildings:
            if self.vertex_buildings[v2_tuple].player_id == player_id:
                return True
        
        # 检查是否有相邻的玩家道路
        if self._has_adjacent_road(vertex1, player_id):
            # 确保不是道路本身连到自己
            for edge_tuple in [(edge.q, edge.r, edge.direction), (edge.q, edge.r, (edge.direction - 1) % 6)]:
                if edge_tuple != edge.to_tuple() and edge_tuple in self.edge_buildings:
                    if self.edge_buildings[edge_tuple].player_id == player_id:
                        return True
        
        if self._has_adjacent_road(vertex2, player_id):
            # 确保不是道路本身连到自己
            for edge_tuple in [(edge.q, edge.r, edge.direction), (edge.q, edge.r, (edge.direction - 1) % 6)]:
                if edge_tuple != edge.to_tuple() and edge_tuple in self.edge_buildings:
                    if self.edge_buildings[edge_tuple].player_id == player_id:
                        return True
        
        return False
    
    def place_settlement(self, vertex: HexVertex, player_id: int) -> bool:
        """放置村庄"""
        print(f"[DEBUG][Game {self.game_id}] place_settlement called: player={player_id}, vertex={vertex.to_tuple()}, phase={self.phase}")
        if not self.can_place_settlement(vertex, player_id):
            print(f"[DEBUG][Game {self.game_id}] place_settlement -> False: can_place_settlement returned False")
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
            self.setup_pending_road = True
            self.setup_pending_road_player_id = player_id
            self.setup_last_settlement_vertex = vertex

            # 第二个定居点放置后立即获得资源
            if self.setup_settlements_placed[player_id] == 2:
                self.award_setup_resources(player_id, vertex)
        
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

        if self.phase == GamePhase.SETUP:
            self._clear_setup_pending()

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
        
        # 使用地图的顶点-六边形关系进行判断，确保顶点与六边形的方向也被考虑
        bq, br, bdir = building.position
        if not self.hex_map:
            return False

        adjacent_hexes = self.hex_map.get_hexagons_by_vertex(bq, br, bdir)
        for hexagon in adjacent_hexes:
            if hexagon.q == q and hexagon.r == r:
                return True
        return False
    
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
            'setup_round': self.setup_round,
            'setup_pending_road': self.setup_pending_road,
            'setup_pending_road_player_id': self.setup_pending_road_player_id,
            'setup_last_settlement_vertex': self.setup_last_settlement_vertex.to_tuple() if self.setup_last_settlement_vertex else None,
            'is_finished': self.is_finished,
            'winner_id': self.winner_id,
            'last_dice_roll': self.last_dice_roll,
            'vertex_buildings': vertex_buildings_dict,
            'edge_buildings': edge_buildings_dict,
        }

