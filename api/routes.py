"""API路由"""
import traceback
from flask import Blueprint, request, jsonify
from game.game_state import GameState, GamePhase
from game.map_generator import MapGenerator
from game.rules import GameRules
from referee.player_interface import BasicPlayer
from models.player import Player
from models.hexagon import HexVertex, HexEdge
from models.building import BuildingType
from utils.logger import GameLogger
import uuid

api_bp = Blueprint('api', __name__)

# 存储游戏实例（实际应用中应使用数据库）
games = {}
loggers = {}

@api_bp.route('/game/create', methods=['POST'])
def create_game():
    """
    创建新游戏
    
    Body:
    {
        "player_count": 4,
        "players": [
            {"name": "玩家1", "color": "red"},
            {"name": "玩家2", "color": "blue"},
            ...
        ],
        "map_type": "standard"  // "standard", "balanced", "simple"
    }
    """
    try:
        data = request.json
        player_count = data.get('player_count', 4)
        players_data = data.get('players', [])
        map_type = data.get('map_type', 'standard')
        
        # 创建游戏
        game_id = str(uuid.uuid4())
        game_state = GameState(game_id, player_count)
        
        # 添加玩家
        for i, player_data in enumerate(players_data[:player_count]):
            player = Player(
                player_id=i + 1,
                name=player_data.get('name', f'玩家{i+1}'),
                color=player_data.get('color', 'blue'),
                is_ai=player_data.get('is_ai', False)
            )
            game_state.add_player(player)
        
        # 生成地图
        if map_type == 'simple':
            game_state.hex_map = MapGenerator.generate_simple_map()
        elif map_type == 'balanced':
            game_state.hex_map = MapGenerator.generate_balanced_map()
        else:
            game_state.hex_map = MapGenerator.generate_standard_map()
        
        # 直接跳过初始设置，进入掷骰子阶段
        from game.game_state import GamePhase
        from models.resource import ResourceType
        
        game_state.phase = GamePhase.ROLL_DICE
        game_state.round_number = 1
        
        # 给每个玩家初始资源
        for player in game_state.players:
            player.add_resource(ResourceType.WOOD, 4)
            player.add_resource(ResourceType.BRICK, 4)
            player.add_resource(ResourceType.SHEEP, 2)
            player.add_resource(ResourceType.WHEAT, 2)
            player.add_resource(ResourceType.ORE, 2)
        
        # 保存游戏
        games[game_id] = game_state
        
        # 创建日志
        logger = GameLogger(game_id)
        logger.log_game_start(
            players=[p.to_dict() for p in game_state.players],
            map_seed=0
        )
        loggers[game_id] = logger
        
        return jsonify({
            'success': True,
            'game_id': game_id,
            'game_state': game_state.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@api_bp.route('/game/<game_id>', methods=['GET'])
def get_game(game_id):
    """获取游戏状态"""
    if game_id not in games:
        return jsonify({
            'success': False,
            'error': '游戏不存在'
        }), 404
    
    game_state = games[game_id]
    return jsonify({
        'success': True,
        'game_state': game_state.to_dict()
    })

@api_bp.route('/game/<game_id>/roll_dice', methods=['POST'])
def roll_dice(game_id):
    """
    掷骰子
    
    Body:
    {
        "player_id": 1
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    player_id = data.get('player_id')
    
    # 检查是否是当前玩家
    if game_state.get_current_player().player_id != player_id:
        return jsonify({'success': False, 'error': '不是你的回合'}), 400
    
    # 检查阶段
    if game_state.phase != GamePhase.ROLL_DICE:
        return jsonify({'success': False, 'error': '当前阶段不能掷骰子'}), 400
    
    # 掷骰子
    dice1, dice2, total = GameRules.roll_dice()
    
    # 记录日志
    logger = loggers.get(game_id)
    if logger:
        logger.log_dice_roll(player_id, dice1, dice2, total)
    
    # 处理结果
    GameRules.handle_dice_roll(game_state, total)
    
    return jsonify({
        'success': True,
        'dice1': dice1,
        'dice2': dice2,
        'total': total,
        'game_state': game_state.to_dict()
    })

@api_bp.route('/game/<game_id>/build', methods=['POST'])
def build(game_id):
    """
    建造建筑
    
    Body:
    {
        "player_id": 1,
        "building_type": "settlement",  // "settlement", "city", "road"
        "position": [0, 0, 1]  // [q, r, direction]
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    
    player_id = data.get('player_id')
    building_type_str = data.get('building_type')
    position_data = data.get('position')
    
    # 检查position是否为None
    if position_data is None or not position_data:
        return jsonify({'success': False, 'error': '请在地图上选择位置'}), 400
    
    position = tuple(position_data)
    
    try:
        building_type = BuildingType(building_type_str)
    except ValueError:
        return jsonify({'success': False, 'error': '无效的建筑类型'}), 400
    
    # 执行建造
    success, message = GameRules.build(game_state, player_id, building_type, position)
    
    if success:
        # 记录日志
        logger = loggers.get(game_id)
        if logger:
            logger.log_build(player_id, building_type_str, position)
    
    return jsonify({
        'success': success,
        'message': message,
        'game_state': game_state.to_dict() if success else None
    })

@api_bp.route('/game/<game_id>/trade/bank', methods=['POST'])
def trade_bank(game_id):
    """
    与银行交易
    
    Body:
    {
        "player_id": 1,
        "give": {"wood": 4},
        "receive": {"brick": 1}
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    
    player_id = data.get('player_id')
    give = data.get('give', {})
    receive = data.get('receive', {})
    
    success, message = GameRules.trade_with_bank(game_state, player_id, give, receive)
    
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_trade(player_id, 0, give, receive)  # 0表示银行
    
    return jsonify({
        'success': success,
        'message': message,
        'game_state': game_state.to_dict() if success else None
    })

@api_bp.route('/game/<game_id>/trade/player', methods=['POST'])
def trade_player(game_id):
    """
    玩家之间交易
    
    Body:
    {
        "player1_id": 1,
        "player2_id": 2,
        "player1_give": {"wood": 2},
        "player1_receive": {"brick": 1}
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    
    player1_id = data.get('player1_id')
    player2_id = data.get('player2_id')
    player1_give = data.get('player1_give', {})
    player1_receive = data.get('player1_receive', {})
    
    success, message = GameRules.trade_with_player(
        game_state, player1_id, player2_id, player1_give, player1_receive
    )
    
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_trade(player1_id, player2_id, player1_give, player1_receive)
    
    return jsonify({
        'success': success,
        'message': message,
        'game_state': game_state.to_dict() if success else None
    })

@api_bp.route('/game/<game_id>/robber/move', methods=['POST'])
def move_robber(game_id):
    """
    移动强盗
    
    Body:
    {
        "player_id": 1,
        "q": 0,
        "r": 1,
        "steal_from_player_id": 2
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    
    player_id = data.get('player_id')
    q = data.get('q')
    r = data.get('r')
    steal_from = data.get('steal_from_player_id')
    
    success, message = GameRules.move_robber(game_state, player_id, q, r, steal_from)
    
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_robber_move(player_id, q, r, steal_from)
    
    return jsonify({
        'success': success,
        'message': message,
        'game_state': game_state.to_dict() if success else None
    })

@api_bp.route('/game/<game_id>/end_turn', methods=['POST'])
def end_turn(game_id):
    """
    结束回合
    
    Body:
    {
        "player_id": 1
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    player_id = data.get('player_id')
    
    # 检查是否是当前玩家
    if game_state.get_current_player().player_id != player_id:
        return jsonify({'success': False, 'error': '不是你的回合'}), 400
    
    success, message = GameRules.end_turn(game_state)
    
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_turn_end(player_id, game_state.round_number)
    
    return jsonify({
        'success': success,
        'message': message,
        'game_state': game_state.to_dict()
    })

@api_bp.route('/game/<game_id>/logs', methods=['GET'])
def get_logs(game_id):
    """获取游戏日志"""
    if game_id not in loggers:
        return jsonify({'success': False, 'error': '日志不存在'}), 404
    
    logger = loggers[game_id]
    return jsonify({
        'success': True,
        'logs': logger.to_dict()
    })

@api_bp.route('/game/<game_id>/player/<int:player_id>/toggle_ai', methods=['POST'])
def toggle_player_ai(game_id, player_id):
    """
    切换玩家类型（真人/AI）
    
    Body:
    {
        "is_ai": true  // 或 false
    }
    """
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    data = request.json
    is_ai = data.get('is_ai', False)
    
    # 找到玩家并切换类型
    player = game_state.get_player(player_id)
    if not player:
        return jsonify({'success': False, 'error': '玩家不存在'}), 404
    
    player.is_ai = is_ai
    
    # 记录日志
    logger = loggers.get(game_id)
    if logger:
        logger.log_player_toggle_ai(player_id, is_ai)
    
    return jsonify({
        'success': True,
        'message': f"{player.name} 已切换为 {'AI' if is_ai else '真人'} 玩家",
        'game_state': game_state.to_dict()
    })


@api_bp.route('/game/<game_id>/player/<int:player_id>/ai_turn', methods=['POST'])
def ai_turn(game_id, player_id):
    """
    执行AI玩家的回合 - 增强发言功能
    """
    print(f"=== 开始AI回合: 游戏 {game_id}, 玩家 {player_id} ===")
    
    # 验证游戏和玩家
    if game_id not in games:
        return jsonify({'success': False, 'error': '游戏不存在'}), 404
    
    game_state = games[game_id]
    player = game_state.get_player(player_id)
    
    if not player or not getattr(player, 'is_ai', False):
        return jsonify({'success': False, 'error': '玩家不存在或不是AI玩家'}), 400
    
    # 获取策略类型
    request_data = request.get_json() or {}
    strategy_type = request_data.get('strategy_type', 'smart')
    
    print(f"使用策略类型: {strategy_type}")
    
    actions = []
    logger = loggers.get(game_id)
    ai_speeches = []  # 记录AI发言
    
    try:
        # 掷骰子阶段
        dice_total = None
        if hasattr(game_state, 'phase') and game_state.phase == GamePhase.ROLL_DICE:
            print("执行掷骰子...")
            dice1, dice2, total = GameRules.roll_dice()
            
            if logger:
                logger.log_dice_roll(player_id, dice1, dice2, total)
            
            GameRules.handle_dice_roll(game_state, total)
            
            actions.append({
                'type': 'roll_dice',
                'dice1': dice1,
                'dice2': dice2,
                'total': total
            })
            dice_total = total
            print(f"掷骰子完成: {dice1}+{dice2}={total}")
        
        # 实例化AI玩家
        print("开始实例化AI玩家...")
        ai_player = None
        if strategy_type == 'smart':
            try:
                from referee.smart_player import SmartPlayer
                ai_player = SmartPlayer(player_id, player.name)
                print(f"成功创建 SmartPlayer: {player.name}")
            except Exception as e:
                print(f"创建 SmartPlayer 失败: {e}")
                from referee.player_interface import BasicPlayer
                ai_player = BasicPlayer(player_id)
                print("回退到 BasicPlayer")
        else:
            # 其他策略...
            pass
        
        # 生成骰子反应发言
        if dice_total and hasattr(ai_player, '_generate_dice_reaction'):
            try:
                ai_player._generate_dice_reaction(dice_total)
            except Exception as e:
                print(f"生成骰子反应发言失败: {e}")
        
        # 获取建造决策
        print("获取建造决策...")
        try:
            game_state_dict = game_state.to_dict()
            build_decision = ai_player.decide_build(game_state_dict)
            print(f"建造决策: {build_decision}")
        except Exception as e:
            print(f"获取建造决策失败: {e}")
            build_decision = (None, None)
        
        # 处理建造决策
        build_success = False
        if build_decision and build_decision[0] is not None:
            build_type_str, position = build_decision
            print(f"尝试建造: {build_type_str} 在位置 {position}")
            
            try:
                if build_type_str == "settlement":
                    build_type = BuildingType.SETTLEMENT
                elif build_type_str == "road":
                    build_type = BuildingType.ROAD
                elif build_type_str == "city":
                    build_type = BuildingType.CITY
                else:
                    raise ValueError(f"未知的建筑类型: {build_type_str}")
                
                build_result, build_message = GameRules.build(game_state, player_id, build_type, position)
                actions.append({
                    'type': 'build',
                    'build_type': build_type_str,
                    'position': position,
                    'result': build_result,
                    'message': build_message
                })
                
                if logger and build_result:
                    logger.log_build(player_id, build_type_str, position)
                    build_success = True
                
                print(f"建造结果: {build_result}, {build_message}")
                    
            except Exception as e:
                actions.append({
                    'type': 'build_error',
                    'error': f'建造失败: {str(e)}'
                })
                print(f"AI建造失败: {e}")
        
        # 交易决策
        if hasattr(ai_player, 'decide_trade'):
            try:
                trade_decision, offer_give, offer_receive = ai_player.decide_trade(game_state_dict)
                if trade_decision:
                    actions.append({
                        'type': 'trade_offer',
                        'offer_give': offer_give,
                        'offer_receive': offer_receive
                    })
                    print(f"交易提议: 给出{offer_give}, 请求{offer_receive}")
            except Exception as e:
                print(f"交易决策失败: {e}")
        
        # 结束回合
        print("结束回合...")
        success, message = GameRules.end_turn(game_state)
        actions.append({
            'type': 'end_turn',
            'success': success,
            'message': message
        })
        
        if logger:
            round_number = getattr(game_state, 'round_number', 0)
            logger.log_turn_end(player_id, round_number)
        
        # 收集AI发言
        if hasattr(ai_player, 'speech_count') and ai_player.speech_count > 0:
            ai_speeches = getattr(ai_player, 'speeches', [])
        
        # 返回响应
        response_data = {
            'success': True,
            'message': f'AI玩家 {player.name} 已完成回合 (策略: {strategy_type})',
            'strategy_type': strategy_type,
            'build_success': build_success,
            'actions': actions,
            'ai_speeches': ai_speeches,
            'game_state': game_state.to_dict()
        }
        print(f"AI回合完成，返回成功响应")
        return jsonify(response_data)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"AI执行错误详情: {error_details}")
        
        return jsonify({
            'success': False,
            'error': f'AI执行回合时发生错误: {str(e)}',
            'actions': actions
        }), 500

   