from typing import Tuple, Dict, Optional, List
import random
from referee.player_interface import PlayerInterface
from services.catan_game_helper import (
    read_resource_state, askLLM, generate_trade_dialogue, set_game_context
)
from models.resource import ResourceType

class SmartPlayer(PlayerInterface):
    """智能AI玩家，主要生成沉浸式发言，简化决策逻辑"""

    def __init__(self, player_id: int, player_name: str = None):
        """初始化智能玩家"""
        super().__init__(player_id)
        self.player_name = player_name or f"玩家{player_id}"
        self.speech_count = 0
        self.speeches: List[Dict] = []  # 修改为字典列表，包含发言类型和内容
        print(f"[SmartPlayer] 初始化玩家 {player_id} - {self.player_name}")

    def _log_speech(self, speech: str, speech_type: str = "chat"):
        """记录AI发言，包含类型信息"""
        if speech:
            self.speech_count += 1
            self.speeches.append({
                "type": speech_type,
                "player_id": self.player_id,
                "player_name": self.player_name,
                "content": speech.strip()
            })

    def decide_build(self, game_state: dict) -> Tuple[Optional[str], Optional[tuple]]:
        """生成本回合的建造决策"""
        print(f"[SmartPlayer] {self.player_name} 开始决策建造...")

        set_game_context(game_state, None)
        player_state = self._get_my_state(game_state)
        if not player_state:
            print(f"[SmartPlayer] 未找到玩家状态")
            return None, None

        resources = player_state.get('resources', {})
        normalized_resources = self._normalize_resources(resources)
        print(f"[SmartPlayer] {self.player_name} 资源: {normalized_resources}")

        available_vertices = self._get_available_vertices(game_state)
        available_edges = self._get_available_edges(game_state)
        print(f"[SmartPlayer] 可用顶点数: {len(available_vertices)}, 可用边数: {len(available_edges)}")

        if self._is_setup_phase(game_state):
            # 设置阶段添加简单发言（不调用DeepSeek）
            self._generate_setup_speech(game_state)
            # 直接随机选择可用位置
            build_decision = self._setup_build_decision(game_state, available_vertices, available_edges)
        else:
            self._generate_situation_speech(game_state, normalized_resources)
            build_decision = self._simple_build_decision(game_state, normalized_resources, available_vertices, available_edges)

        if build_decision and build_decision[0]:
            print(f"[SmartPlayer] {self.player_name} 决定建造: {build_decision}")
            if not self._is_setup_phase(game_state):
                self._generate_build_speech(build_decision[0], build_decision[1], game_state)

        return build_decision

    def _get_my_state(self, game_state: dict) -> dict:
        """获取当前玩家的状态"""
        for player in game_state.get('players', []):
            if player.get('player_id') == self.player_id:
                return player
        return {}

    def _is_setup_phase(self, game_state: dict) -> bool:
        """判断当前是否处于设置阶段"""
        # 仅依赖明确的阶段或当前玩家的待补路标记来判定设置阶段，避免误判
        if game_state.get('phase') == 'setup':
            return True

        if game_state.get('setup_pending_road') and game_state.get('setup_pending_road_player_id') == self.player_id:
            return True

        return False

    def _setup_build_decision(self, game_state: dict, available_vertices: List[tuple], available_edges: List[tuple]) -> Tuple[Optional[str], Optional[tuple]]:
        """开局阶段建造决策 - 无视资源限制，优先选择高价值顶点"""
        # 检查该玩家在setup阶段是否已放置足够的settlement（最多2个）
        setup_settlements_count = game_state.get('setup_settlements_placed', {}).get(self.player_id, 0)
        if setup_settlements_count >= 2:
            # 该玩家的setup已完成，结束本轮
            print(f"[SmartPlayer] {self.player_name} setup阶段已完成（已放置{setup_settlements_count}个settlement），退出。")
            return None, None
        
        # 简化：设置阶段行为统一为——如果有待补路则补路，否则随机从可用顶点选一个建村
        if game_state.get('setup_pending_road'):
            pending_player = game_state.get('setup_pending_road_player_id')
            if pending_player != self.player_id:
                return None, None

            edge = self._choose_setup_road(game_state, available_edges)
            if edge:
                return 'road', edge
            return None, None

        # 直接从可用顶点中随机选择（上层已在设置阶段过滤合法性）
        if available_vertices:
            vertex = random.choice(available_vertices)
            return 'settlement', vertex

        return None, None

    def _simple_build_decision(self, game_state: dict, resources: dict, available_vertices: List[tuple], available_edges: List[tuple]) -> Tuple[Optional[str], Optional[tuple]]:
        """正常阶段建造决策"""
        player_state = self._get_my_state(game_state)

        if self._can_build_settlement(resources, player_state) and available_vertices:
            return 'settlement', random.choice(available_vertices)

        if self._can_build_road(resources, player_state) and available_edges:
            return 'road', random.choice(available_edges)

        if self._can_build_city(resources, player_state):
            settlements = self._get_my_settlements(game_state)
            if settlements:
                return 'city', random.choice(settlements)

        return None, None

    def _choose_best_setup_vertex(self, game_state: dict, available_vertices: List[tuple]) -> Optional[tuple]:
        """选择开局阶段最佳村庄位置 - 优先高价值/边缘顶点"""
        if not available_vertices:
            return None

        valid_vertices = [v for v in available_vertices if self._is_valid_setup_vertex(game_state, v)]
        if not valid_vertices:
            return None
        
        scored = [(self._score_setup_vertex(game_state, v), v) for v in valid_vertices]
        scored.sort(key=lambda item: item[0], reverse=True)
        
        # 取得分最高的顶点中随机选一个，以增加多样性
        if scored:
            best_score = scored[0][0]
            best_vertices = [vertex for score, vertex in scored if score >= best_score - 0.5]
            return random.choice(best_vertices) if best_vertices else random.choice(valid_vertices)
        
        return random.choice(valid_vertices)

    def _score_setup_vertex(self, game_state: dict, vertex: tuple) -> float:
        """对开局村庄顶点进行评分 - 优先高概率数字和边缘位置"""
        q, r, direction = vertex
        hexagons = game_state.get('hex_map', {}).get('hexagons', [])
        hex_map = {(hex_tile['q'], hex_tile['r']): hex_tile for hex_tile in hexagons}

        # 基础资源得分
        score = 0.0
        for hq, hr in self._get_hexes_for_vertex(q, r, direction):
            hex_tile = hex_map.get((hq, hr))
            if not hex_tile or hex_tile.get('resource') == 'desert':
                continue
            number = hex_tile.get('number', 0)
            if number in [6, 8]:
                score += 3.0
            elif number in [5, 9]:
                score += 2.0
            elif number in [4, 10]:
                score += 1.5
            elif number in [3, 11]:
                score += 1.0
            elif number in [2, 12]:
                score += 0.5
            else:
                score += 1.0
        
        # 边缘倾向加分（Q或R接近极值时加分）
        max_q = max((h['q'] for h in hexagons), default=0)
        min_q = min((h['q'] for h in hexagons), default=0)
        max_r = max((h['r'] for h in hexagons), default=0)
        min_r = min((h['r'] for h in hexagons), default=0)
        
        is_edge = (q <= min_q + 1 or q >= max_q - 1 or r <= min_r + 1 or r >= max_r - 1)
        if is_edge:
            score += 0.5  # 边缘位置轻微加分
        
        return score

    def _get_hexes_for_vertex(self, q: int, r: int, direction: int) -> List[Tuple[int, int]]:
        """返回与顶点相邻的三个六边形坐标"""
        positions = [(q, r)]
        if direction == 0:
            positions.extend([(q, r - 1), (q + 1, r - 1)])
        elif direction == 1:
            positions.extend([(q + 1, r - 1), (q + 1, r)])
        elif direction == 2:
            positions.extend([(q + 1, r), (q, r + 1)])
        elif direction == 3:
            positions.extend([(q, r + 1), (q - 1, r + 1)])
        elif direction == 4:
            positions.extend([(q - 1, r + 1), (q - 1, r)])
        elif direction == 5:
            positions.extend([(q - 1, r), (q, r - 1)])
        return positions

    def _is_valid_setup_vertex(self, game_state: dict, vertex: tuple) -> bool:
        """检查 setup 阶段村庄位置是否合法，避免重复尝试非法顶点"""
        vertex_buildings = game_state.get('vertex_buildings', {})
        key = f"{vertex[0]},{vertex[1]},{vertex[2]}"
        if key in vertex_buildings:
            return False

        for adjacent in self._get_setup_adjacent_vertices(vertex):
            if f"{adjacent[0]},{adjacent[1]},{adjacent[2]}" in vertex_buildings:
                return False

        return True

    def _get_setup_adjacent_vertices(self, vertex: tuple) -> List[tuple]:
        """返回与给定顶点距离为1的相邻顶点，用于 setup 阶段距离规则校验"""
        q, r, direction = vertex
        adjacent = [
            (q, r, (direction + 1) % 6),
            (q, r, (direction - 1) % 6)
        ]

        if direction == 0:
            adjacent.append((q + 1, r - 1, 3))
            adjacent.append((q, r - 1, 4))
        elif direction == 1:
            adjacent.append((q + 1, r - 1, 4))
            adjacent.append((q + 1, r, 5))
        elif direction == 2:
            adjacent.append((q + 1, r, 5))
            adjacent.append((q, r + 1, 0))
        elif direction == 3:
            adjacent.append((q, r + 1, 0))
            adjacent.append((q - 1, r + 1, 1))
        elif direction == 4:
            adjacent.append((q - 1, r + 1, 1))
            adjacent.append((q - 1, r, 2))
        elif direction == 5:
            adjacent.append((q - 1, r, 2))
            adjacent.append((q, r - 1, 3))

        seen = set()
        unique = []
        for item in adjacent:
            if item not in seen:
                unique.append(item)
                seen.add(item)
        return unique

    def _choose_setup_road(self, game_state: dict, available_edges: List[tuple]) -> Optional[tuple]:
        """选择与当前待补路村庄相邻的道路"""
        pending = self._get_pending_settlement_vertex(game_state)
        if pending:
            for edge in self._get_edges_adjacent_to_vertex(pending):
                if edge in available_edges:
                    return edge

        for settlement in self._get_my_settlements(game_state):
            for edge in self._get_edges_adjacent_to_vertex(settlement):
                if edge in available_edges:
                    return edge

        return None

    def _get_pending_settlement_vertex(self, game_state: dict) -> Optional[tuple]:
        """获取当前 setup 阶段需要补路的顶点"""
        pending = game_state.get('setup_last_settlement_vertex')
        if isinstance(pending, list) and len(pending) == 3:
            return tuple(pending)
        if isinstance(pending, tuple) and len(pending) == 3:
            return pending
        return None

    def _get_edges_adjacent_to_vertex(self, vertex: tuple) -> List[tuple]:
        """返回与顶点相邻的两条边"""
        q, r, direction = vertex
        return [
            (q, r, direction),
            (q, r, (direction - 1) % 6),
        ]

    def _is_edge_adjacent_to_vertex(self, edge: tuple, vertex: tuple) -> bool:
        """判断边是否与顶点相邻"""
        eq, er, edir = edge
        vq, vr, vdir = vertex
        return eq == vq and er == vr and edir in {vdir, (vdir - 1) % 6}

    def _get_my_settlements(self, game_state: dict) -> List[tuple]:
        """获取当前玩家的所有村庄位置"""
        settlements = []
        for key, building in game_state.get('vertex_buildings', {}).items():
            if building.get('player_id') == self.player_id and building.get('type') == 'settlement':
                parts = key.split(',')
                if len(parts) == 3:
                    settlements.append((int(parts[0]), int(parts[1]), int(parts[2])))
        return settlements

    def _get_available_vertices(self, game_state: dict) -> List[tuple]:
        """获取可用顶点位置"""
        available = []
        occupied = set(game_state.get('vertex_buildings', {}).keys())
        for hex_tile in game_state.get('hex_map', {}).get('hexagons', []):
            q, r = hex_tile['q'], hex_tile['r']
            for direction in range(6):
                key = f"{q},{r},{direction}"
                if key in occupied:
                    continue
                vertex = (q, r, direction)
                if self._is_setup_phase(game_state):
                    if self._is_valid_setup_vertex(game_state, vertex):
                        available.append(vertex)
                else:
                    available.append(vertex)
        return available

    def _get_available_edges(self, game_state: dict) -> List[tuple]:
        """获取可用边位置"""
        available = []
        occupied = set(game_state.get('edge_buildings', {}).keys())
        for hex_tile in game_state.get('hex_map', {}).get('hexagons', []):
            q, r = hex_tile['q'], hex_tile['r']
            for direction in range(6):
                key = f"{q},{r},{direction}"
                if key not in occupied:
                    available.append((q, r, direction))
        return available

    def _normalize_resources(self, resources: dict) -> dict:
        """标准化资源键名"""
        mapping = {
            'wood': ['wood', 'lumber'],
            'brick': ['brick', 'clay'],
            'sheep': ['sheep', 'wool'],
            'wheat': ['wheat', 'grain'],
            'ore': ['ore', 'stone'],
        }
        normalized = {}
        for standard, variants in mapping.items():
            normalized[standard] = next((resources.get(v, 0) for v in variants if v in resources), 0)
        return normalized

    def _can_build_settlement(self, resources: dict, player_state: dict) -> bool:
        return (resources.get('wood', 0) >= 1 and resources.get('brick', 0) >= 1 and
                resources.get('sheep', 0) >= 1 and resources.get('wheat', 0) >= 1 and
                player_state.get('settlements_left', 0) > 0)

    def _can_build_city(self, resources: dict, player_state: dict) -> bool:
        return (resources.get('wheat', 0) >= 2 and resources.get('ore', 0) >= 3 and
                player_state.get('cities_left', 0) > 0)

    def _can_build_road(self, resources: dict, player_state: dict) -> bool:
        return (resources.get('wood', 0) >= 1 and resources.get('brick', 0) >= 1 and
                player_state.get('roads_left', 0) > 0)

    def _generate_situation_speech(self, game_state: dict, resources: dict):
        try:
            players = game_state.get('players', [])
            current_player_id = game_state.get('current_player_id', 0)
            situation = (
                f"当前游戏局势分析：\n"
                f"我是{self.player_name}，当前{'是' if current_player_id == self.player_id else '不是'}我的回合。\n"
                f"我的资源状况：木材{resources.get('wood', 0)}，砖块{resources.get('brick', 0)}，羊毛{resources.get('sheep', 0)}，"
                f"小麦{resources.get('wheat', 0)}，矿石{resources.get('ore', 0)}。\n"
            )
            other_players = [f"玩家{p.get('player_id')}" for p in players if p.get('player_id') != self.player_id]
            if other_players:
                situation += f"其他玩家：{', '.join(other_players)}。\n"
            prompt = (
                f"基于以下游戏局势：\n{situation}\n"
                f"请以{self.player_name}的身份生成一段简短的发言（30-50字），表达对当前游戏局势的看法。\n"
                f"发言应该自然、有趣，展现个性，可以是：\n"
                f"- 对资源的评论\n"
                f"- 对游戏进展的看法\n"
                f"- 对其他玩家的调侃\n"
                f"- 对自己策略的简短说明\n"
                f"请直接返回发言内容，不要额外解释。"
            )
            speech = askLLM(prompt, max_tokens=100)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 局势发言: {speech}")
                self._log_speech(speech, speech_type="situation")
        except Exception as e:
            print(f"生成局势发言失败: {e}")

    def _generate_build_speech(self, build_type: str, position: tuple, game_state: dict):
        try:
            build_names = {"settlement": "村庄", "road": "道路", "city": "城市"}
            build_name = build_names.get(build_type, build_type)
            prompt = (
                f"我是{self.player_name}，正在卡坦岛游戏中建造{build_name}。\n"
                f"建造位置：{position}\n"
                f"请以{self.player_name}的身份生成一段简短的建造宣言（20-40字）。\n"
                f"发言应该有趣、有个性，可以是：\n"
                f"- 表达兴奋或策略意图\n"
                f"- 对位置的评论\n"
                f"- 对未来发展的展望\n"
                f"- 幽默的自我鼓励\n"
                f"请直接返回发言内容。"
            )
            speech = askLLM(prompt, max_tokens=80)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 建造发言: {speech}")
                self._log_speech(speech, speech_type="build")
        except Exception as e:
            print(f"生成建造发言失败: {e}")

    def _generate_setup_speech(self, game_state: dict):
        """在设置阶段生成简单发言，不调用LLM"""
        setup_round = game_state.get('setup_round', 0)
        settlements_count = game_state.get('setup_settlements_placed', {}).get(self.player_id, 0)
        
        # 简单的本地发言，不依赖LLM
        setup_speeches = [
            "好的，我来选个有利位置..." if settlements_count == 0 else "第二个定居点，要策略性地放置！",
            "这片资源不错，就选这里了。" if settlements_count == 0 else "道路要连接到关键位置。",
            "初始布局很重要，不能大意。" if settlements_count == 0 else "完成了我的第二个定居点！",
            "看来我得争取好的地盘。" if settlements_count == 0 else "运气不错，资源还可以。",
        ]
        
        import random
        speech = random.choice(setup_speeches)
        print(f"🎤 {self.player_name} Setup发言: {speech}")
        self._log_speech(speech, speech_type="setup")

    def _generate_trade_speech(self, offer: dict, request: dict):
        try:
            offer_str = ", ".join([f"{v}个{k}" for k, v in offer.items()])
            request_str = ", ".join([f"{v}个{k}" for k, v in request.items()])
            prompt = (
                f"我是{self.player_name}，正在卡坦岛游戏中提出交易：\n"
                f"我愿意用 {offer_str} 交换 {request_str}\n"
                f"请以{self.player_name}的身份生成一段交易提议发言（20-40字）。\n"
                f"发言应该：\n"
                f"- 有说服力或幽默\n"
                f"- 解释为什么这个交易公平\n"
                f"- 展现个性特点\n"
                f"请直接返回发言内容。"
            )
            speech = askLLM(prompt, max_tokens=80)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 交易发言: {speech}")
                self._log_speech(speech, speech_type="trade")
        except Exception as e:
            print(f"生成交易发言失败: {e}")

    def decide_trade(self, game_state: dict) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        player_state = self._get_my_state(game_state)
        resources = self._normalize_resources(player_state.get('resources', {}))

        offer_give = {}
        offer_receive = {}
        for res, count in resources.items():
            if count >= 4:
                offer_give = {res: 4}
                break
        for res, count in resources.items():
            if count == 0:
                offer_receive = {res: 1}
                break

        if offer_give and offer_receive:
            self._generate_trade_speech(offer_give, offer_receive)
            return True, offer_give, offer_receive

        return False, {}, {}

    def decide_trade_with_player(self, game_state: dict, offer_player_id: int, offer_give: Dict[str, int], offer_receive: Dict[str, int]) -> bool:
        return random.choice([True, False])
