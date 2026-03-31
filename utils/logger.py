"""游戏日志系统"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any

class GameLogger:
    """游戏日志记录器"""
    
    def __init__(self, game_id: str, log_dir: str = "logs"):
        self.game_id = game_id
        self.log_dir = log_dir
        self.events: List[Dict[str, Any]] = []
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_file = os.path.join(log_dir, f"game_{game_id}.json")
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        记录一个游戏事件
        
        Args:
            event_type: 事件类型（如 'dice_roll', 'build', 'trade'等）
            data: 事件数据
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        self.events.append(event)
        self._save_to_file()
    
    def log_game_start(self, players: List[Dict], map_seed: int):
        """记录游戏开始"""
        self.log_event('game_start', {
            'players': players,
            'map_seed': map_seed
        })
    
    def log_dice_roll(self, player_id: int, dice1: int, dice2: int, total: int):
        """记录掷骰子"""
        self.log_event('dice_roll', {
            'player_id': player_id,
            'dice1': dice1,
            'dice2': dice2,
            'total': total
        })
    
    def log_resource_distribution(self, distributions: Dict[int, Dict[str, int]]):
        """记录资源分配"""
        self.log_event('resource_distribution', {
            'distributions': distributions
        })
    
    def log_build(self, player_id: int, building_type: str, position: tuple):
        """记录建造"""
        self.log_event('build', {
            'player_id': player_id,
            'building_type': building_type,
            'position': list(position)
        })
    
    def log_trade(self, player1_id: int, player2_id: int, 
                  give: Dict[str, int], receive: Dict[str, int]):
        """记录交易"""
        self.log_event('trade', {
            'player1_id': player1_id,
            'player2_id': player2_id,
            'give': give,
            'receive': receive
        })
    
    def log_robber_move(self, player_id: int, q: int, r: int, 
                       stolen_from: int = None, resource: str = None):
        """记录强盗移动"""
        self.log_event('robber_move', {
            'player_id': player_id,
            'position': [q, r],
            'stolen_from': stolen_from,
            'resource': resource
        })
    
    def log_turn_end(self, player_id: int, round_number: int):
        """记录回合结束"""
        self.log_event('turn_end', {
            'player_id': player_id,
            'round_number': round_number
        })
    
    def log_game_end(self, winner_id: int, winner_name: str, final_scores: Dict[int, int]):
        """记录游戏结束"""
        self.log_event('game_end', {
            'winner_id': winner_id,
            'winner_name': winner_name,
            'final_scores': final_scores
        })
    
    def log_player_toggle_ai(self, player_id: int, is_ai: bool):
        """记录玩家切换AI状态"""
        self.log_event('player_toggle_ai', {
            'player_id': player_id,
            'is_ai': is_ai
        })
    
    def get_events(self) -> List[Dict[str, Any]]:
        """获取所有事件"""
        return self.events
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """获取特定类型的事件"""
        return [e for e in self.events if e['type'] == event_type]
    
    def _save_to_file(self):
        """保存到文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'game_id': self.game_id,
                    'events': self.events
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存日志失败: {e}")
    
    def load_from_file(self):
        """从文件加载"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events = data.get('events', [])
        except Exception as e:
            print(f"加载日志失败: {e}")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'game_id': self.game_id,
            'event_count': len(self.events),
            'events': self.events
        }

