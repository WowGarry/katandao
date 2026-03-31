"""
游戏测试脚本 - 演示AI玩家对战
"""

from game.game_state import GameState
from game.map_generator import MapGenerator
from models.player import Player
from utils.logger import GameLogger
from referee.catan_referee import CatanReferee
from referee.player_interface import BasicPlayer, RandomPlayer

def test_ai_game():
    """测试AI玩家对战"""
    print("=" * 50)
    print("卡坦岛 AI 对战测试")
    print("=" * 50)
    
    # 创建游戏
    game_id = "test_ai_game_001"
    game_state = GameState(game_id, player_count=4)
    
    # 添加玩家
    players_info = [
        ("BasicAI-1", "red"),
        ("RandomAI-1", "blue"),
        ("BasicAI-2", "green"),
        ("RandomAI-2", "yellow"),
    ]
    
    for i, (name, color) in enumerate(players_info):
        player = Player(player_id=i+1, name=name, color=color)
        game_state.add_player(player)
    
    # 生成地图
    game_state.hex_map = MapGenerator.generate_simple_map()
    print(f"\n✓ 生成地图: {len(game_state.hex_map.hexagons)} 个六边形")
    
    # 创建日志
    logger = GameLogger(game_id)
    logger.log_game_start(
        players=[p.to_dict() for p in game_state.players],
        map_seed=0
    )
    
    # 创建裁判
    referee = CatanReferee(game_state, logger)
    
    # 注册AI策略
    referee.register_player_strategy(1, BasicPlayer(1))
    referee.register_player_strategy(2, RandomPlayer(2))
    referee.register_player_strategy(3, BasicPlayer(3))
    referee.register_player_strategy(4, RandomPlayer(4))
    
    print("\n✓ 注册玩家策略:")
    for i, (name, _) in enumerate(players_info):
        strategy_type = "基础AI" if "Basic" in name else "随机AI"
        print(f"  - 玩家 {i+1}: {name} ({strategy_type})")
    
    print("\n" + "=" * 50)
    print("开始游戏模拟...")
    print("=" * 50 + "\n")
    
    # 运行游戏（仅作为演示，实际游戏需要完善建筑放置逻辑）
    # result = referee.run_game_loop(max_rounds=50)
    
    # 由于建筑放置逻辑还需完善，这里只演示基本流程
    print("注意：完整的AI对战需要实现精确的建筑放置逻辑")
    print("当前版本演示了基本框架，可通过Web界面进行人工游戏\n")
    
    # 显示游戏状态
    print("游戏状态:")
    print(f"  - 游戏ID: {game_state.game_id}")
    print(f"  - 玩家数: {game_state.player_count}")
    print(f"  - 当前回合: {game_state.round_number}")
    print(f"  - 当前阶段: {game_state.phase}")
    
    print("\n玩家信息:")
    for player in game_state.players:
        print(f"  - {player.name}:")
        print(f"    资源: {player.resources.total()} 张")
        print(f"    胜利点: {player.victory_points}")
        print(f"    剩余建筑: 道路{player.roads_left} 村庄{player.settlements_left} 城市{player.cities_left}")
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)
    print(f"\n游戏日志已保存到: logs/{game_id}.json")

if __name__ == "__main__":
    test_ai_game()

