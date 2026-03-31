"""
玩家策略接口定义

这个模块定义了玩家策略的标准接口，可用于：
1. AI玩家策略实现
2. 自定义策略代码提交
3. 游戏逻辑的统一调用

使用示例：
    class MyPlayer(PlayerInterface):
        def decide_build(self, game_state):
            # 实现建造决策
            return ("settlement", [0, 0, 1])
"""

from typing import Tuple, Dict, Optional, List
from abc import ABC, abstractmethod

from models.resource import ResourceType

class PlayerInterface(ABC):
    """玩家策略接口基类"""
    
    def __init__(self, player_id: int):
        """
        初始化玩家
        
        Args:
            player_id: 玩家ID
        """
        self.player_id = player_id
    
    @abstractmethod
    def decide_build(self, game_state: dict) -> Tuple[Optional[str], Optional[tuple]]:
        """
        决定建造什么和在哪里建造
        
        Args:
            game_state: 游戏状态字典
            
        Returns:
            (building_type, position): 建筑类型和位置
            building_type: "settlement", "city", "road" 或 None
            position: (q, r, direction) 坐标
        """
        pass
    
    @abstractmethod
    def decide_trade(self, game_state: dict) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        """
        决定是否交易
        
        Args:
            game_state: 游戏状态字典
            
        Returns:
            (should_trade, give, receive): 是否交易、给出的资源、获得的资源
        """
        pass
    
    def decide_trade_with_player(self, game_state: dict, 
                                 offer_player_id: int,
                                 offer_give: Dict[str, int],
                                 offer_receive: Dict[str, int]) -> bool:
        """
        决定是否接受其他玩家的交易提议
        
        Args:
            game_state: 游戏状态
            offer_player_id: 提议玩家ID
            offer_give: 对方给出的资源
            offer_receive: 对方要求的资源
            
        Returns:
            bool: 是否接受
        """
        return False
    
    def decide_discard(self, game_state: dict, num_to_discard: int) -> Dict[str, int]:
        """
        掷到7时决定弃掉哪些资源
        
        Args:
            game_state: 游戏状态
            num_to_discard: 需要弃掉的资源数量
            
        Returns:
            Dict[str, int]: 要弃掉的资源
        """
        return {}
    
    def decide_robber_move(self, game_state: dict) -> Tuple[int, int, Optional[int]]:
        """
        决定强盗移动到哪里，以及抢夺哪个玩家
        
        Args:
            game_state: 游戏状态
            
        Returns:
            (q, r, steal_from_player_id): 位置坐标和抢夺目标玩家ID
        """
        return (0, 0, None)
    
    def on_turn_start(self, game_state: dict):
        """
        回合开始时的回调
        
        Args:
            game_state: 游戏状态
        """
        pass
    
    def on_turn_end(self, game_state: dict):
        """
        回合结束时的回调
        
        Args:
            game_state: 游戏状态
        """
        pass


class BasicPlayer(PlayerInterface):
    """基础AI玩家（简单策略）"""
    
    def decide_build(self, game_state: dict) -> Tuple[Optional[str], Optional[tuple]]:
        """简单建造策略：优先建造村庄"""
        player = self._get_my_state(game_state)
        
        # 检查是否有足够资源建造村庄
        resources = player.get('resources', {})
        if (resources.get(ResourceType.WOOD.value, 0) >= 1 and 
            resources.get(ResourceType.BRICK.value, 0) >= 1 and
            resources.get(ResourceType.SHEEP.value, 0) >= 1 and
            resources.get(ResourceType.WHEAT.value, 0) >= 1):
            # 简化：返回一个随机位置
            return ("settlement", (0, 0, 1))
        
        # 检查是否可以建造道路
        if resources.get(ResourceType.WOOD.value, 0) >= 1 and resources.get(ResourceType.BRICK.value, 0) >= 1:
            return ("road", (0, 0, 0))
        
        return (None, None)
    
    def decide_trade(self, game_state: dict) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        """简单交易策略：资源多时用4:1交易"""
        player = self._get_my_state(game_state)
        resources = player.get('resources', {})
        
        # 找出数量最多的资源
        max_resource = max(resources.items(), key=lambda x: x[1], default=('wood', 0))
        
        if max_resource[1] >= 4:
            # 需要的资源（优先小麦和矿石）
            needed_resources = ['wheat', 'ore', 'sheep', 'brick', 'wood']
            for resource in needed_resources:
                if resources.get(resource, 0) < 2:
                    return (True, {max_resource[0]: 4}, {resource: 1})
        
        return (False, {}, {})
    
    def _get_my_state(self, game_state: dict) -> dict:
        """获取当前玩家的状态"""
        players = game_state.get('players', [])
        for player in players:
            if player.get('player_id') == self.player_id:
                return player
        return {}


class RandomPlayer(PlayerInterface):
    """随机策略玩家"""
    
    def decide_build(self, game_state: dict) -> Tuple[Optional[str], Optional[tuple]]:
        """随机建造"""
        import random
        player = self._get_my_state(game_state)
        resources = player.get('resources', {})
        
        # 可能的建造选项
        options = []
        
        if (resources.get('wood', 0) >= 1 and 
            resources.get('brick', 0) >= 1 and
            resources.get('sheep', 0) >= 1 and
            resources.get('wheat', 0) >= 1):
            options.append(("settlement", (random.randint(-2, 2), random.randint(-2, 2), random.randint(0, 5))))
        
        if resources.get('wood', 0) >= 1 and resources.get('brick', 0) >= 1:
            options.append(("road", (random.randint(-2, 2), random.randint(-2, 2), random.randint(0, 5))))
        
        if options:
            return random.choice(options)
        
        return (None, None)
    
    def decide_trade(self, game_state: dict) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        """随机交易"""
        import random
        
        if random.random() < 0.3:  # 30% 概率交易
            resources = ['wood', 'brick', 'sheep', 'wheat', 'ore']
            give_resource = random.choice(resources)
            receive_resource = random.choice([r for r in resources if r != give_resource])
            return (True, {give_resource: 4}, {receive_resource: 1})
        
        return (False, {}, {})
    
    def _get_my_state(self, game_state: dict) -> dict:
        """获取当前玩家的状态"""
        players = game_state.get('players', [])
        for player in players:
            if player.get('player_id') == self.player_id:
                return player
        return {}

