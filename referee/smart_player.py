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
        print(f"[SmartPlayer] 初始化玩家 {player_id} - {self.player_name}")
    
    def decide_build(self, game_state: dict) -> Tuple[Optional[str], Optional[tuple]]:
        """
        简化的建造决策，主要生成发言
        """
        print(f"[SmartPlayer] {self.player_name} 开始决策建造...")
        
        # 设置游戏上下文
        set_game_context(game_state, None)
        
        # 获取当前玩家状态
        player_state = self._get_my_state(game_state)
        if not player_state:
            print(f"[SmartPlayer] 未找到玩家状态")
            return (None, None)
        
        # 读取资源
        resources = player_state.get('resources', {})
        normalized_resources = self._normalize_resources(resources)
        
        print(f"[SmartPlayer] {self.player_name} 资源: {normalized_resources}")
        
        # 获取可用的建造位置
        available_vertices = self._get_available_vertices(game_state)
        available_edges = self._get_available_edges(game_state)
        
        print(f"[SmartPlayer] 可用顶点数: {len(available_vertices)}, 可用边数: {len(available_edges)}")
        
        # 生成当前局势发言
        self._generate_situation_speech(game_state, normalized_resources)
        
        # 简化的建造逻辑 - 主要使用随机选择
        build_decision = self._simple_build_decision(game_state, normalized_resources, available_vertices, available_edges)
        
        if build_decision[0]:
            print(f"[SmartPlayer] {self.player_name} 决定建造: {build_decision}")
            # 生成建造发言
            self._generate_build_speech(build_decision[0], build_decision[1], game_state)
        
        return build_decision
    
    def _simple_build_decision(self, game_state: dict, resources: dict, 
                             available_vertices: List[tuple], available_edges: List[tuple]) -> Tuple[Optional[str], Optional[tuple]]:
        """简化的建造决策逻辑"""
        player_state = self._get_my_state(game_state)
        
        # 1. 优先尝试建造村庄
        if self._can_build_settlement(resources, player_state) and available_vertices:
            # 随机选择一个可用位置
            position = random.choice(available_vertices) if available_vertices else None
            if position:
                return ("settlement", position)
        
        # 2. 尝试建造道路
        if self._can_build_road(resources, player_state) and available_edges:
            position = random.choice(available_edges) if available_edges else None
            if position:
                return ("road", position)
        
        # 3. 尝试建造城市
        if self._can_build_city(resources, player_state):
            settlements = self._get_my_settlements(game_state)
            if settlements:
                position = random.choice(settlements)
                return ("city", position)
        
        return (None, None)
    
    def _generate_situation_speech(self, game_state: dict, resources: dict):
        """生成当前局势发言"""
        try:
            # 获取游戏基本信息
            players = game_state.get('players', [])
            current_player_id = game_state.get('current_player_id', 0)
            
            # 构建局势描述
            situation = f"""
当前游戏局势分析：
我是{self.player_name}，当前{"是" if current_player_id == self.player_id else "不是"}我的回合。
我的资源状况：木材{resources.get('wood', 0)}，砖块{resources.get('brick', 0)}，羊毛{resources.get('sheep', 0)}，小麦{resources.get('wheat', 0)}，矿石{resources.get('ore', 0)}。
"""
            
            # 添加其他玩家信息
            other_players = []
            for player in players:
                if player.get('player_id') != self.player_id:
                    other_players.append(f"玩家{player.get('player_id')}")
            
            if other_players:
                situation += f"其他玩家：{', '.join(other_players)}。\n"
            
            prompt = f"""
基于以下游戏局势：
{situation}

请以{self.player_name}的身份生成一段简短的发言（30-50字），表达对当前游戏局势的看法。
发言应该自然、有趣，展现个性，可以是：
- 对资源的评论
- 对游戏进展的看法  
- 对其他玩家的调侃
- 对自己策略的简短说明

请直接返回发言内容，不要额外解释。
"""
            
            speech = askLLM(prompt, max_tokens=100)
            if speech and len(speech) > 10:  # 确保有实际内容
                print(f"🎤 {self.player_name} 局势发言: {speech}")
                # 这里应该将发言记录到游戏日志中
                self._log_speech(speech)
                
        except Exception as e:
            print(f"生成局势发言失败: {e}")
    
    def _generate_build_speech(self, build_type: str, position: tuple, game_state: dict):
        """生成建造相关发言"""
        try:
            build_names = {
                "settlement": "村庄",
                "road": "道路", 
                "city": "城市"
            }
            
            build_name = build_names.get(build_type, build_type)
            
            prompt = f"""
我是{self.player_name}，正在卡坦岛游戏中建造{build_name}。
建造位置：{position}

请以{self.player_name}的身份生成一段简短的建造宣言（20-40字）。
发言应该有趣、有个性，可以是：
- 表达兴奋或策略意图
- 对位置的评论
- 对未来发展的展望
- 幽默的自我鼓励

请直接返回发言内容。
"""
            
            speech = askLLM(prompt, max_tokens=80)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 建造发言: {speech}")
                self._log_speech(speech)
                
        except Exception as e:
            print(f"生成建造发言失败: {e}")
    
    def _generate_trade_speech(self, offer: dict, request: dict):
        """生成交易相关发言"""
        try:
            offer_str = ", ".join([f"{v}个{k}" for k, v in offer.items()])
            request_str = ", ".join([f"{v}个{k}" for k, v in request.items()])
            
            prompt = f"""
我是{self.player_name}，正在卡坦岛游戏中提出交易：
我愿意用 {offer_str} 交换 {request_str}

请以{self.player_name}的身份生成一段交易提议发言（20-40字）。
发言应该：
- 有说服力或幽默
- 解释为什么这个交易公平
- 展现个性特点

请直接返回发言内容。
"""
            
            speech = askLLM(prompt, max_tokens=80)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 交易发言: {speech}")
                self._log_speech(speech)
                
        except Exception as e:
            print(f"生成交易发言失败: {e}")
    
    def _generate_dice_reaction(self, dice_result: int):
        """生成骰子反应发言"""
        try:
            prompt = f"""
我是{self.player_name}，在卡坦岛游戏中掷出了骰子点数：{dice_result}

请以{self.player_name}的身份生成对骰子点数的反应发言（15-30字）。
反应应该：
- 符合点数好坏（{dice_result}点{'很好' if dice_result in [6,8] else '一般' if dice_result in [5,9] else '不太好'}）
- 展现个性
- 简短有趣

请直接返回发言内容。
"""
            
            speech = askLLM(prompt, max_tokens=60)
            if speech and len(speech) > 10:
                print(f"🎤 {self.player_name} 骰子反应: {speech}")
                self._log_speech(speech)
                
        except Exception as e:
            print(f"生成骰子反应失败: {e}")
    
    def _log_speech(self, speech: str):
        """记录发言到游戏日志"""
        # 这里应该将发言保存到游戏日志系统中
        # 暂时先打印到控制台
        self.speech_count += 1
        print(f"💬 [{self.player_name} 的第{self.speech_count}次发言] {speech}")
    
    # 保持原有的辅助方法，但简化逻辑
    def _normalize_resources(self, resources: dict) -> dict:
        """标准化资源键名"""
        normalized = {}
        resource_mapping = {
            'wood': ['wood', 'lumber'],
            'brick': ['brick', 'clay'], 
            'sheep': ['sheep', 'wool'],
            'wheat': ['wheat', 'grain'],
            'ore': ['ore', 'stone']
        }
        
        for standard_name, variants in resource_mapping.items():
            count = 0
            for variant in variants:
                if variant in resources:
                    count = resources[variant]
                    break
            normalized[standard_name] = count
        
        return normalized
    
    def _can_build_settlement(self, resources: dict, player_state: dict) -> bool:
        """检查是否有足够资源建造村庄"""
        return (resources.get('wood', 0) >= 1 and resources.get('brick', 0) >= 1 and
                resources.get('sheep', 0) >= 1 and resources.get('wheat', 0) >= 1 and
                player_state.get('settlements_left', 0) > 0)
    
    def _can_build_city(self, resources: dict, player_state: dict) -> bool:
        """检查是否有足够资源建造城市"""
        return (resources.get('wheat', 0) >= 2 and resources.get('ore', 0) >= 3 and
                player_state.get('cities_left', 0) > 0)
    
    def _can_build_road(self, resources: dict, player_state: dict) -> bool:
        """检查是否有足够资源建造道路"""
        return (resources.get('wood', 0) >= 1 and resources.get('brick', 0) >= 1 and
                player_state.get('roads_left', 0) > 0)
    
    def _get_available_vertices(self, game_state: dict) -> List[tuple]:
        """获取可用的顶点位置"""
        hexagons = game_state.get('hex_map', {}).get('hexagons', [])
        vertex_buildings = game_state.get('vertex_buildings', {})
        
        available = []
        for hex_tile in hexagons:
            q, r = hex_tile['q'], hex_tile['r']
            for direction in range(6):
                vertex = (q, r, direction)
                vertex_key = f"{q},{r},{direction}"
                if vertex_key not in vertex_buildings:
                    available.append(vertex)
        
        return available
    
    def _get_available_edges(self, game_state: dict) -> List[tuple]:
        """获取可用的边位置"""
        hexagons = game_state.get('hex_map', {}).get('hexagons', [])
        edge_buildings = game_state.get('edge_buildings', {})
        
        available = []
        for hex_tile in hexagons:
            q, r = hex_tile['q'], hex_tile['r']
            for direction in range(6):
                edge = (q, r, direction)
                edge_key = f"{q},{r},{direction}"
                if edge_key not in edge_buildings:
                    available.append(edge)
        
        return available
    
    def _get_my_settlements(self, game_state: dict) -> List[tuple]:
        """获取当前玩家的所有村庄位置"""
        vertex_buildings = game_state.get('vertex_buildings', {})
        settlements = []
        
        for key, building in vertex_buildings.items():
            if (building.get('player_id') == self.player_id and 
                building.get('type') == 'settlement'):
                parts = key.split(',')
                if len(parts) == 3:
                    position = (int(parts[0]), int(parts[1]), int(parts[2]))
                    settlements.append(position)
        
        return settlements
    
    def _get_my_state(self, game_state: dict) -> dict:
        """获取当前玩家的状态"""
        players = game_state.get('players', [])
        for player in players:
            if player.get('player_id') == self.player_id:
                return player
        return {}
    
    def decide_trade(self, game_state: dict) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        """决定是否交易，并生成交易发言"""
        set_game_context(game_state, None)
        
        player_state = self._get_my_state(game_state)
        if not player_state:
            return (False, {}, {})
        
        resources = self._normalize_resources(player_state.get('resources', {}))
        
        # 简化的交易逻辑
        max_resource = max(resources.items(), key=lambda x: x[1], default=(None, 0))
        if max_resource[1] >= 4:
            min_resource = min(resources.items(), key=lambda x: x[1])
            if min_resource[0] != max_resource[0]:
                # 生成交易发言
                self._generate_trade_speech(
                    {max_resource[0]: 4}, 
                    {min_resource[0]: 1}
                )
                return (True, {max_resource[0]: 4}, {min_resource[0]: 1})
        
        return (False, {}, {})
    
    def decide_trade_with_player(self, game_state: dict, 
                                 offer_player_id: int,
                                 offer_give: Dict[str, int],
                                 offer_receive: Dict[str, int]) -> bool:
        """决定是否接受其他玩家的交易提议"""
        # 简化逻辑：随机决定
        return random.choice([True, False])