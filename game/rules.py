"""游戏规则引擎"""
import random
from typing import Dict, Optional, Tuple
from models.resource import ResourceType, Resources
from models.building import BuildingType, Building
from game.game_state import GameState, GamePhase
from models.hexagon import HexVertex, HexEdge

class GameRules:
    """卡坦岛游戏规则引擎"""
    
    @staticmethod
    def roll_dice() -> Tuple[int, int, int]:
        """
        掷两个骰子
        
        Returns:
            (dice1, dice2, sum): 两个骰子的值和总和
        """
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        return (dice1, dice2, dice1 + dice2)
    
    @staticmethod
    def handle_dice_roll(game_state: GameState, dice_sum: int):
        """
        处理骰子结果
        
        Args:
            game_state: 游戏状态
            dice_sum: 骰子总和
        """
        game_state.last_dice_roll = dice_sum
        
        if dice_sum == 7:
            # 掷到7：需要弃牌和移动强盗
            game_state.phase = GamePhase.DISCARD
        else:
            # 分配资源
            game_state.distribute_resources(dice_sum)
            game_state.phase = GamePhase.TRADE
    
    @staticmethod
    def build(game_state: GameState, player_id: int, building_type: BuildingType, 
              position: tuple) -> Tuple[bool, str]:
        """
        建造建筑
        
        Args:
            game_state: 游戏状态
            player_id: 玩家ID
            building_type: 建筑类型
            position: 位置（顶点或边）
            
        Returns:
            (success, message): 是否成功和消息
        """
        player = game_state.get_player(player_id)
        if not player:
            print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> player not found: {player_id}")
            return False, "玩家不存在"
        
        # 检查是否是当前玩家
        current = game_state.get_current_player().player_id
        if current != player_id:
            print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> not current player: current={current}, request={player_id}")
            return False, "不是你的回合"
        
        # 检查阶段 - 允许在SETUP、TRADE、BUILD阶段建造
        if game_state.phase not in [GamePhase.SETUP, GamePhase.TRADE, GamePhase.BUILD]:
            print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> invalid phase: {game_state.phase}")
            return False, f"当前阶段不能建造: {game_state.phase}"
        
        # 获取建筑成本
        cost = Building.get_cost(building_type)
        
        # 设置阶段免费建造
        if game_state.phase != GamePhase.SETUP:
            if not player.has_resources(cost):
                print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> insufficient resources for player {player_id}, cost={cost}")
                return False, "资源不足"
        
        # 根据建筑类型放置
        if building_type == BuildingType.SETTLEMENT:
            vertex = HexVertex(*position)
            print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> attempting to place settlement for player {player_id} at {vertex.to_tuple()}")
            if not game_state.place_settlement(vertex, player_id):
                print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> place_settlement returned False")
                return False, "无法在此位置放置村庄"
            
        elif building_type == BuildingType.CITY:
            vertex = HexVertex(*position)
            if not game_state.place_city(vertex, player_id):
                return False, "无法在此位置放置城市"
            
        elif building_type == BuildingType.ROAD:
            edge = HexEdge(*position)
            if not game_state.place_road(edge, player_id):
                return False, "无法在此位置放置道路"
            if game_state.phase == GamePhase.SETUP:
                # 当前玩家在设置阶段放置道路后，进入下一个玩家
                game_state.next_turn()
        
        # 扣除资源（非设置阶段）
        if game_state.phase != GamePhase.SETUP:
            print(f"[DEBUG][Game {getattr(game_state,'game_id',None)}] build -> charging resources for player {player_id}, cost={cost}")
            player.pay_resources(cost)
        
        return True, f"成功建造{building_type.value}"
    
    @staticmethod
    def trade_with_bank(game_state: GameState, player_id: int, 
                       give: Dict[str, int], receive: Dict[str, int]) -> Tuple[bool, str]:
        """
        与银行交易（4:1比例，或港口2:1/3:1）
        
        Args:
            game_state: 游戏状态
            player_id: 玩家ID
            give: 给出的资源 {"wood": 4}
            receive: 获得的资源 {"brick": 1}
            
        Returns:
            (success, message): 是否成功和消息
        """
        player = game_state.get_player(player_id)
        if not player:
            return False, "玩家不存在"
        
        # 检查阶段
        if game_state.phase != GamePhase.TRADE:
            return False, "当前阶段不能交易"
        
        # 转换为ResourceType
        give_resources = {}
        for resource_name, amount in give.items():
            try:
                resource_type = ResourceType(resource_name)
                give_resources[resource_type] = amount
            except ValueError:
                return False, f"无效的资源类型: {resource_name}"
        
        receive_resources = {}
        for resource_name, amount in receive.items():
            try:
                resource_type = ResourceType(resource_name)
                receive_resources[resource_type] = amount
            except ValueError:
                return False, f"无效的资源类型: {resource_name}"
        
        # 检查资源
        if not player.has_resources(give_resources):
            return False, "资源不足"
        
        # 检查交易比例（简化版：4:1）
        total_give = sum(give.values())
        total_receive = sum(receive.values())
        
        if total_give < 4 or total_receive != 1:
            return False, "交易比例必须是4:1"
        
        # 执行交易
        for resource_type, amount in give_resources.items():
            player.remove_resource(resource_type, amount)
        
        for resource_type, amount in receive_resources.items():
            player.add_resource(resource_type, amount)
        
        return True, "交易成功"
    
    @staticmethod
    def trade_with_player(game_state: GameState, player1_id: int, player2_id: int,
                         player1_give: Dict[str, int], player1_receive: Dict[str, int]) -> Tuple[bool, str]:
        """
        玩家之间交易
        
        Args:
            game_state: 游戏状态
            player1_id: 发起交易的玩家ID
            player2_id: 交易对象玩家ID
            player1_give: 玩家1给出的资源
            player1_receive: 玩家1获得的资源（即玩家2给出的）
            
        Returns:
            (success, message): 是否成功和消息
        """
        player1 = game_state.get_player(player1_id)
        player2 = game_state.get_player(player2_id)
        
        if not player1 or not player2:
            return False, "玩家不存在"
        
        # 检查阶段
        if game_state.phase != GamePhase.TRADE:
            return False, "当前阶段不能交易"
        
        # 转换资源类型
        def convert_resources(res_dict):
            result = {}
            for name, amount in res_dict.items():
                try:
                    result[ResourceType(name)] = amount
                except ValueError:
                    return None
            return result
        
        p1_give = convert_resources(player1_give)
        p1_receive = convert_resources(player1_receive)
        
        if p1_give is None or p1_receive is None:
            return False, "无效的资源类型"
        
        # 检查资源
        if not player1.has_resources(p1_give):
            return False, f"{player1.name} 资源不足"
        
        if not player2.has_resources(p1_receive):
            return False, f"{player2.name} 资源不足"
        
        # 执行交易
        for resource_type, amount in p1_give.items():
            player1.remove_resource(resource_type, amount)
            player2.add_resource(resource_type, amount)
        
        for resource_type, amount in p1_receive.items():
            player2.remove_resource(resource_type, amount)
            player1.add_resource(resource_type, amount)
        
        return True, "交易成功"
    
    @staticmethod
    def move_robber(game_state: GameState, player_id: int, q: int, r: int, 
                   steal_from_player_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        移动强盗
        
        Args:
            game_state: 游戏状态
            player_id: 玩家ID
            q, r: 目标六边形坐标
            steal_from_player_id: 抢夺资源的目标玩家ID
            
        Returns:
            (success, message): 是否成功和消息
        """
        player = game_state.get_player(player_id)
        if not player:
            return False, "玩家不存在"
        
        # 移动强盗
        if not game_state.hex_map.move_robber(q, r):
            return False, "无效的位置"
        
        # 抢夺资源
        if steal_from_player_id is not None:
            target_player = game_state.get_player(steal_from_player_id)
            if target_player and target_player.resources.total() > 0:
                # 随机抢一张牌
                available_resources = [rt for rt in ResourceType if rt != ResourceType.DESERT 
                                     and target_player.resources.get(rt) > 0]
                if available_resources:
                    stolen_resource = random.choice(available_resources)
                    target_player.remove_resource(stolen_resource, 1)
                    player.add_resource(stolen_resource, 1)
        
        game_state.phase = GamePhase.TRADE
        return True, "强盗已移动"
    
    @staticmethod
    def discard_resources(game_state: GameState, player_id: int, 
                         discard: Dict[str, int]) -> Tuple[bool, str]:
        """
        弃牌（掷到7且手牌>7时）
        
        Args:
            game_state: 游戏状态
            player_id: 玩家ID
            discard: 要弃掉的资源
            
        Returns:
            (success, message): 是否成功和消息
        """
        player = game_state.get_player(player_id)
        if not player:
            return False, "玩家不存在"
        
        total = player.resources.total()
        if total <= 7:
            return False, "手牌数量不超过7，无需弃牌"
        
        # 需要弃一半（向下取整）
        need_discard = total // 2
        discard_count = sum(discard.values())
        
        if discard_count != need_discard:
            return False, f"需要弃{need_discard}张牌"
        
        # 转换并弃牌
        for resource_name, amount in discard.items():
            try:
                resource_type = ResourceType(resource_name)
                if not player.remove_resource(resource_type, amount):
                    return False, f"资源 {resource_name} 不足"
            except ValueError:
                return False, f"无效的资源类型: {resource_name}"
        
        return True, "弃牌成功"
    
    @staticmethod
    def end_turn(game_state: GameState) -> Tuple[bool, str]:
        """
        结束当前玩家的回合
        
        Args:
            game_state: 游戏状态
            
        Returns:
            (success, message): 是否成功和消息
        """
        # 检查是否有赢家
        winner = game_state.check_winner()
        if winner:
            return True, f"{winner.name} 获胜！"
        
        # 进入下一回合
        game_state.next_turn()
        return True, "回合结束"
    
    @staticmethod
    def trade_with_bank(game_state, player_id: int, give: dict, receive: dict) -> tuple[bool, str]:
        """
        处理与银行的 4:1 交易
        """
        # 1. 回合校验：只能在自己的回合交易
        current_player = game_state.get_current_player()
        if current_player.player_id != player_id:
            return False, "只能在你的回合进行交易"

        # 2. 参数格式校验：确保只涉及一种换出资源和一种换入资源
        if len(give) != 1 or len(receive) != 1:
            return False, "4:1交易必须明确一种换出资源和一种换入资源"

        give_res_str = list(give.keys())[0]
        give_amount = give[give_res_str]
        receive_res_str = list(receive.keys())[0]
        receive_amount = receive[receive_res_str]

        # 3. 交易比例校验：严格遵守 4 换 1 法则
        if give_amount != 4 or receive_amount != 1:
            return False, "必须使用 4 个相同的资源换取 1 个其他资源"

        if give_res_str == receive_res_str:
            return False, "换出和换入的资源不能是同一种"

        try:
            give_type = ResourceType(give_res_str)
            receive_type = ResourceType(receive_res_str)
        except ValueError:
            return False, "无效的资源类型"

        # 4. 资产校验：检查玩家是否有足够的资源
        if not current_player.has_resources({give_type: 4}):
            return False, f"你的 {give_res_str} 资源不足 4 个，无法交易"

        # 5. 执行交易：扣除与增加
        current_player.remove_resource(give_type, 4)
        current_player.add_resource(receive_type, 1)

        return True, f"成功使用 4 个 {give_res_str} 换取了 1 个 {receive_res_str}"