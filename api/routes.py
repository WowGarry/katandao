"""API routes for CatanForge backend."""
from __future__ import annotations

import traceback
import uuid

from flask import Blueprint, jsonify, request

from game.game_state import GamePhase, GameState
from game.map_generator import MapGenerator
from game.rules import GameRules
from models.building import BuildingType
from models.player import Player
from referee.player_interface import BasicPlayer, RandomPlayer
from services.guide_service import GuideService
from utils.logger import GameLogger

api_bp = Blueprint("api", __name__)

# In-memory game store (for local development only)
games = {}
loggers = {}


@api_bp.route("/game/create", methods=["POST"])
def create_game():
    """
    Create a new game.

    Body:
    {
        "player_count": 4,
        "players": [{"name": "...", "color": "#...", "is_ai": false}, ...],
        "map_type": "standard" | "balanced" | "simple"
    }
    """
    try:
        data = request.get_json() or {}
        player_count = int(data.get("player_count", 4))
        players_data = data.get("players", [])
        map_type = data.get("map_type", "standard")

        game_id = str(uuid.uuid4())
        game_state = GameState(game_id, player_count)

        # Add players
        for idx, player_data in enumerate(players_data[:player_count]):
            game_state.add_player(
                Player(
                    player_id=idx + 1,
                    name=player_data.get("name", f"Player {idx + 1}"),
                    color=player_data.get("color", "#3b82f6"),
                    is_ai=bool(player_data.get("is_ai", False)),
                )
            )

        # Ensure the table has enough players
        while len(game_state.players) < player_count:
            idx = len(game_state.players)
            game_state.add_player(
                Player(
                    player_id=idx + 1,
                    name=f"Player {idx + 1}",
                    color=["#ef4444", "#3b82f6", "#10b981", "#f59e0b"][idx % 4],
                    is_ai=False,
                )
            )

        # Map
        if map_type == "simple":
            game_state.hex_map = MapGenerator.generate_simple_map()
        elif map_type == "balanced":
            game_state.hex_map = MapGenerator.generate_balanced_map()
        else:
            game_state.hex_map = MapGenerator.generate_standard_map()

        # Start directly at roll phase for fast play in this project.
        game_state.phase = GamePhase.ROLL_DICE
        game_state.round_number = 1

        # Give initial resources to keep sessions moving quickly.
        from models.resource import ResourceType

        for player in game_state.players:
            player.add_resource(ResourceType.WOOD, 4)
            player.add_resource(ResourceType.BRICK, 4)
            player.add_resource(ResourceType.SHEEP, 2)
            player.add_resource(ResourceType.WHEAT, 2)
            player.add_resource(ResourceType.ORE, 2)

        games[game_id] = game_state
        logger = GameLogger(game_id)
        logger.log_game_start(players=[p.to_dict() for p in game_state.players], map_seed=0)
        loggers[game_id] = logger

        return jsonify({"success": True, "game_id": game_id, "game_state": game_state.to_dict()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@api_bp.route("/game/<game_id>", methods=["GET"])
def get_game(game_id):
    """Get current game state."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    return jsonify({"success": True, "game_state": games[game_id].to_dict()})


@api_bp.route("/game/<game_id>/roll_dice", methods=["POST"])
def roll_dice(game_id):
    """Roll dice for current player turn."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}
    player_id = data.get("player_id")

    if game_state.get_current_player().player_id != player_id:
        return jsonify({"success": False, "error": "Not your turn"}), 400

    if game_state.phase != GamePhase.ROLL_DICE:
        return jsonify({"success": False, "error": "Dice can only be rolled in roll_dice phase"}), 400

    dice1, dice2, total = GameRules.roll_dice()
    logger = loggers.get(game_id)
    if logger:
        logger.log_dice_roll(player_id, dice1, dice2, total)

    GameRules.handle_dice_roll(game_state, total)
    return jsonify(
        {
            "success": True,
            "dice1": dice1,
            "dice2": dice2,
            "total": total,
            "game_state": game_state.to_dict(),
        }
    )


@api_bp.route("/game/<game_id>/build", methods=["POST"])
def build(game_id):
    """Build settlement/city/road."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}

    player_id = data.get("player_id")
    building_type_str = data.get("building_type")
    position_data = data.get("position")

    if not position_data:
        return jsonify({"success": False, "error": "Please choose a position on the map"}), 400

    try:
        building_type = BuildingType(building_type_str)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid building type"}), 400

    success, message = GameRules.build(game_state, player_id, building_type, tuple(position_data))

    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_build(player_id, building_type_str, tuple(position_data))

    return jsonify(
        {
            "success": success,
            "message": message,
            "game_state": game_state.to_dict() if success else None,
        }
    )


@api_bp.route("/game/<game_id>/trade/bank", methods=["POST"])
def trade_bank(game_id):
    """Trade with the bank (4:1 by current rule implementation)."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}

    player_id = data.get("player_id")
    give = data.get("give", {})
    receive = data.get("receive", {})

    success, message = GameRules.trade_with_bank(game_state, player_id, give, receive)
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_trade(player_id, 0, give, receive)

    return jsonify(
        {
            "success": success,
            "message": message,
            "game_state": game_state.to_dict() if success else None,
        }
    )


@api_bp.route("/game/<game_id>/trade/player", methods=["POST"])
def trade_player(game_id):
    """Trade between two players."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}

    player1_id = data.get("player1_id")
    player2_id = data.get("player2_id")
    player1_give = data.get("player1_give", {})
    player1_receive = data.get("player1_receive", {})

    success, message = GameRules.trade_with_player(
        game_state, player1_id, player2_id, player1_give, player1_receive
    )

    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_trade(player1_id, player2_id, player1_give, player1_receive)

    return jsonify(
        {
            "success": success,
            "message": message,
            "game_state": game_state.to_dict() if success else None,
        }
    )


@api_bp.route("/game/<game_id>/robber/move", methods=["POST"])
def move_robber(game_id):
    """Move robber and optionally steal from target player."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}

    player_id = data.get("player_id")
    q = data.get("q")
    r = data.get("r")
    steal_from = data.get("steal_from_player_id")

    success, message = GameRules.move_robber(game_state, player_id, q, r, steal_from)

    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_robber_move(player_id, q, r, steal_from)

    return jsonify(
        {
            "success": success,
            "message": message,
            "game_state": game_state.to_dict() if success else None,
        }
    )


@api_bp.route("/game/<game_id>/end_turn", methods=["POST"])
def end_turn(game_id):
    """End current player turn."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}
    player_id = data.get("player_id")

    if game_state.get_current_player().player_id != player_id:
        return jsonify({"success": False, "error": "Not your turn"}), 400

    success, message = GameRules.end_turn(game_state)
    if success:
        logger = loggers.get(game_id)
        if logger:
            logger.log_turn_end(player_id, game_state.round_number)

    return jsonify({"success": success, "message": message, "game_state": game_state.to_dict()})


@api_bp.route("/game/<game_id>/logs", methods=["GET"])
def get_logs(game_id):
    """Return game event logs."""
    if game_id not in loggers:
        return jsonify({"success": False, "error": "Logs not found"}), 404

    return jsonify({"success": True, "logs": loggers[game_id].to_dict()})


@api_bp.route("/game/<game_id>/player/<int:player_id>/guide_hint", methods=["GET"])
def get_guide_hint(game_id, player_id):
    """Return contextual hint for onboarding and turn guidance."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    hint = GuideService.get_hint(game_state, player_id)

    return jsonify(
        {
            "success": True,
            "hint": hint,
            "meta": {
                "game_id": game_id,
                "player_id": player_id,
                "phase": game_state.phase,
                "round_number": game_state.round_number,
                "current_player_id": game_state.get_current_player().player_id,
            },
        }
    )


@api_bp.route("/game/<game_id>/player/<int:player_id>/toggle_ai", methods=["POST"])
def toggle_player_ai(game_id, player_id):
    """Toggle a player between human and AI."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    data = request.get_json() or {}
    is_ai = bool(data.get("is_ai", False))

    player = game_state.get_player(player_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"}), 404

    player.is_ai = is_ai
    logger = loggers.get(game_id)
    if logger:
        logger.log_player_toggle_ai(player_id, is_ai)

    return jsonify(
        {
            "success": True,
            "message": f"{player.name} switched to {'AI' if is_ai else 'human'} player",
            "game_state": game_state.to_dict(),
        }
    )


@api_bp.route("/game/<game_id>/player/<int:player_id>/ai_turn", methods=["POST"])
def ai_turn(game_id, player_id):
    """Execute one AI player's turn."""
    if game_id not in games:
        return jsonify({"success": False, "error": "Game not found"}), 404

    game_state = games[game_id]
    player = game_state.get_player(player_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"}), 404
    if not player.is_ai:
        return jsonify({"success": False, "error": "Target player is not AI"}), 400
    if game_state.get_current_player().player_id != player_id:
        return jsonify({"success": False, "error": "Not this AI player's turn"}), 400

    request_data = request.get_json() or {}
    strategy_type = request_data.get("strategy_type", "smart")
    logger = loggers.get(game_id)

    actions = []
    build_success = False
    ai_speeches = []

    try:
        if game_state.phase == GamePhase.ROLL_DICE:
            dice1, dice2, total = GameRules.roll_dice()
            GameRules.handle_dice_roll(game_state, total)
            actions.append({"type": "roll_dice", "dice1": dice1, "dice2": dice2, "total": total})
            if logger:
                logger.log_dice_roll(player_id, dice1, dice2, total)

        # Choose strategy implementation.
        if strategy_type == "smart":
            try:
                from referee.smart_player import SmartPlayer

                ai_player = SmartPlayer(player_id, player.name)
            except Exception:
                ai_player = BasicPlayer(player_id)
        elif strategy_type == "random":
            ai_player = RandomPlayer(player_id)
        else:
            ai_player = BasicPlayer(player_id)

        game_state_dict = game_state.to_dict()

        # Build decision
        build_decision = ai_player.decide_build(game_state_dict)
        if build_decision and build_decision[0] and build_decision[1] is not None:
            build_type_str, position = build_decision
            build_type = BuildingType(build_type_str)
            result, message = GameRules.build(game_state, player_id, build_type, tuple(position))
            actions.append(
                {
                    "type": "build",
                    "build_type": build_type_str,
                    "position": list(position),
                    "result": result,
                    "message": message,
                }
            )
            if result:
                build_success = True
                if logger:
                    logger.log_build(player_id, build_type_str, tuple(position))

        # Optional trade decision
        trade_decision, offer_give, offer_receive = ai_player.decide_trade(game_state.to_dict())
        if trade_decision and game_state.phase == GamePhase.TRADE:
            trade_result, trade_message = GameRules.trade_with_bank(
                game_state, player_id, offer_give, offer_receive
            )
            actions.append(
                {
                    "type": "trade",
                    "give": offer_give,
                    "receive": offer_receive,
                    "result": trade_result,
                    "message": trade_message,
                }
            )
            if trade_result and logger:
                logger.log_trade(player_id, 0, offer_give, offer_receive)

        # End turn
        end_success, end_message = GameRules.end_turn(game_state)
        actions.append({"type": "end_turn", "success": end_success, "message": end_message})
        if end_success and logger:
            logger.log_turn_end(player_id, game_state.round_number)

        if hasattr(ai_player, "speech_count") and getattr(ai_player, "speech_count", 0) > 0:
            ai_speeches = getattr(ai_player, "speeches", [])

        return jsonify(
            {
                "success": True,
                "message": f"AI player {player.name} finished turn ({strategy_type})",
                "strategy_type": strategy_type,
                "build_success": build_success,
                "actions": actions,
                "ai_speeches": ai_speeches,
                "game_state": game_state.to_dict(),
            }
        )
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "error": f"AI turn failed: {exc}",
                "traceback": traceback.format_exc(),
                "actions": actions,
            }
        ), 500
