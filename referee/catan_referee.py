"""
卡坦岛游戏裁判系统

负责：
1. 管理游戏流程
2. 调用玩家策略
3. 验证操作合法性
4. 记录游戏事件
"""

from typing import List, Optional
from game.game_state import GameState, GamePhase
from game.rules import GameRules
from utils.logger import GameLogger
from referee.player_interface import PlayerInterface

class CatanReferee:
    """卡坦岛游戏裁判"""
    
    def __init__(self, game_state: GameState, logger: GameLogger):
        """
        初始化裁判
        
        Args:
            game_state: 游戏状态
            logger: 游戏日志记录器
        """
        self.game_state = game_state
        self.logger = logger
        self.player_strategies: List[Optional[PlayerInterface]] = [None] * game_state.player_count
    
    def register_player_strategy(self, player_id: int, strategy: PlayerInterface):
        """
        注册玩家策略
        
        Args:
            player_id: 玩家ID
            strategy: 玩家策略实例
        """
        index = player_id - 1
        if 0 <= index < len(self.player_strategies):
            self.player_strategies[index] = strategy
    
    def run_turn(self, player_id: int) -> dict:
        """
        运行一个回合
        
        Args:
            player_id: 玩家ID
            
        Returns:
            dict: 回合结果
        """
        player = self.game_state.get_player(player_id)
        if not player:
            return {'success': False, 'error': '玩家不存在'}
        
        strategy = self.player_strategies[player_id - 1]
        
        # 回合开始回调
        if strategy:
            strategy.on_turn_start(self.game_state.to_dict())
        
        result = {'success': True, 'actions': []}
        
        # 根据阶段执行操作
        if self.game_state.phase == GamePhase.ROLL_DICE:
            dice_result = self._handle_roll_dice(player_id)
            result['actions'].append(dice_result)
        
        if self.game_state.phase == GamePhase.TRADE and strategy:
            trade_result = self._handle_trade(player_id, strategy)
            if trade_result:
                result['actions'].append(trade_result)
        
        if self.game_state.phase == GamePhase.BUILD and strategy:
            build_result = self._handle_build(player_id, strategy)
            if build_result:
                result['actions'].append(build_result)
        
        # 回合结束回调
        if strategy:
            strategy.on_turn_end(self.game_state.to_dict())
        
        return result
    
    def _handle_roll_dice(self, player_id: int) -> dict:
        """处理掷骰子"""
        dice1, dice2, total = GameRules.roll_dice()
        
        self.logger.log_dice_roll(player_id, dice1, dice2, total)
        
        GameRules.handle_dice_roll(self.game_state, total)
        
        return {
            'action': 'roll_dice',
            'dice': [dice1, dice2],
            'total': total
        }
    
    def _handle_trade(self, player_id: int, strategy: PlayerInterface) -> Optional[dict]:
        """处理交易"""
        should_trade, give, receive = strategy.decide_trade(self.game_state.to_dict())
        
        if should_trade:
            success, message = GameRules.trade_with_bank(
                self.game_state, player_id, give, receive
            )
            
            if success:
                self.logger.log_trade(player_id, 0, give, receive)
                return {
                    'action': 'trade',
                    'with': 'bank',
                    'give': give,
                    'receive': receive,
                    'success': True
                }
        
        return None
    
    def _handle_build(self, player_id: int, strategy: PlayerInterface) -> Optional[dict]:
        """处理建造"""
        building_type, position = strategy.decide_build(self.game_state.to_dict())
        
        if building_type and position:
            from models.building import BuildingType
            try:
                build_type = BuildingType(building_type)
            except ValueError:
                return None
            
            success, message = GameRules.build(
                self.game_state, player_id, build_type, position
            )
            
            if success:
                self.logger.log_build(player_id, building_type, position)
                return {
                    'action': 'build',
                    'building_type': building_type,
                    'position': position,
                    'success': True
                }
        
        return None
    
    def run_game_loop(self, max_rounds: int = 100) -> dict:
        """
        运行完整游戏循环（用于AI对战）
        
        Args:
            max_rounds: 最大回合数
            
        Returns:
            dict: 游戏结果
        """
        round_count = 0
        
        while not self.game_state.is_finished and round_count < max_rounds:
            current_player_id = self.game_state.get_current_player().player_id
            
            # 运行当前玩家的回合
            self.run_turn(current_player_id)
            
            # 结束回合
            GameRules.end_turn(self.game_state)
            
            round_count += 1
        
        # 记录游戏结束
        if self.game_state.is_finished:
            winner = self.game_state.get_player(self.game_state.winner_id)
            final_scores = {p.player_id: p.victory_points for p in self.game_state.players}
            
            self.logger.log_game_end(
                self.game_state.winner_id,
                winner.name if winner else "Unknown",
                final_scores
            )
        
        return {
            'finished': self.game_state.is_finished,
            'winner_id': self.game_state.winner_id,
            'rounds': round_count,
            'final_state': self.game_state.to_dict()
        }

