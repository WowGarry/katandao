"""Rule-based guide hints for onboarding and turn assistance."""
from __future__ import annotations

from typing import Dict, List, Tuple

from game.game_state import GamePhase, GameState
from models.building import Building, BuildingType
from models.hexagon import HexEdge, HexVertex
from models.resource import ResourceType

RESOURCE_NAME_ZH = {
    ResourceType.WOOD: "木材",
    ResourceType.BRICK: "砖块",
    ResourceType.SHEEP: "羊毛",
    ResourceType.WHEAT: "小麦",
    ResourceType.ORE: "矿石",
    ResourceType.DESERT: "沙漠",
}


class GuideService:
    """Generate contextual hints from current game state."""

    MAX_SUGGESTED_POSITIONS = 8

    @classmethod
    def get_hint(cls, game_state: GameState, player_id: int) -> Dict:
        player = game_state.get_player(player_id)
        if not player:
            return {
                "priority": "low",
                "action": "invalid_player",
                "title": "未找到该玩家",
                "reason": "目标玩家不存在，暂时无法生成参谋建议。",
                "targets": [],
                "suggested_build_mode": None,
                "suggested_positions": [],
            }

        if game_state.is_finished:
            return {
                "priority": "low",
                "action": "game_over",
                "title": "对局已结束",
                "reason": "本局已经决出胜负，建议直接开启下一局。",
                "targets": [],
                "suggested_build_mode": None,
                "suggested_positions": [],
                "winner_id": game_state.winner_id,
            }

        current_player = game_state.get_current_player()
        if current_player.player_id != player_id:
            return {
                "priority": "low",
                "action": "wait_for_turn",
                "title": "等待你的回合",
                "reason": (
                    f"当前行动玩家是 {current_player.name}。"
                    "先观察资源与版图，提前规划下一步。"
                ),
                "targets": ["current-player-chip"],
                "suggested_build_mode": None,
                "suggested_positions": [],
            }

        phase = game_state.phase

        if phase == GamePhase.ROLL_DICE:
            return {
                "priority": "high",
                "action": "roll_dice",
                "title": "先掷骰子",
                "reason": "每回合先掷骰，再进入资源结算与后续行动。",
                "targets": ["roll-dice-btn"],
                "suggested_build_mode": None,
                "suggested_positions": [],
            }

        if phase == GamePhase.DISCARD:
            return {
                "priority": "high",
                "action": "discard",
                "title": "需要先弃牌",
                "reason": "本轮掷出 7 点，手牌超限玩家必须先完成弃牌。",
                "targets": ["help-button"],
                "suggested_build_mode": None,
                "suggested_positions": [],
            }

        if phase == GamePhase.MOVE_ROBBER:
            return {
                "priority": "high",
                "action": "move_robber",
                "title": "移动强盗",
                "reason": "请选择目标地块移动强盗，阻断该地块的资源产出。",
                "targets": ["hex-map"],
                "suggested_build_mode": None,
                "suggested_positions": [],
            }

        if phase == GamePhase.SETUP:
            setup_settlement_positions = cls._find_valid_settlement_positions(game_state, player_id)
            if setup_settlement_positions:
                return {
                    "priority": "high",
                    "action": "build_settlement",
                    "title": "先放置起始村庄",
                    "reason": "开局部署阶段村庄免费，优先抢关键点位。",
                    "targets": ["build-settlement-btn", "hex-map"],
                    "suggested_build_mode": "settlement",
                    "suggested_positions": setup_settlement_positions,
                }

            setup_road_positions = cls._find_valid_road_positions(game_state, player_id)
            if setup_road_positions:
                return {
                    "priority": "high",
                    "action": "build_road",
                    "title": "放置起始道路",
                    "reason": "开局部署阶段道路免费，为后续扩张铺路。",
                    "targets": ["build-road-btn", "hex-map"],
                    "suggested_build_mode": "road",
                    "suggested_positions": setup_road_positions,
                }

        city_positions = cls._find_valid_city_positions(game_state, player_id)
        settlement_positions = cls._find_valid_settlement_positions(game_state, player_id)
        road_positions = cls._find_valid_road_positions(game_state, player_id)

        city_cost = Building.get_cost(BuildingType.CITY)
        settlement_cost = Building.get_cost(BuildingType.SETTLEMENT)
        road_cost = Building.get_cost(BuildingType.ROAD)

        can_afford_city = player.has_resources(city_cost) and len(city_positions) > 0
        can_afford_settlement = player.has_resources(settlement_cost) and len(settlement_positions) > 0
        can_afford_road = player.has_resources(road_cost) and len(road_positions) > 0

        if can_afford_city:
            return {
                "priority": "high" if player.victory_points >= 8 else "medium",
                "action": "build_city",
                "title": "建议升级城市",
                "reason": "城市能显著提升产出效率，并直接提供 2 点胜利点。",
                "targets": ["build-city-btn", "hex-map"],
                "suggested_build_mode": "city",
                "suggested_positions": city_positions,
            }

        if can_afford_settlement:
            return {
                "priority": "high",
                "action": "build_settlement",
                "title": "建议建造村庄",
                "reason": "你已满足建造条件，建村可扩大控制并获得 1 点胜利点。",
                "targets": ["build-settlement-btn", "hex-map"],
                "suggested_build_mode": "settlement",
                "suggested_positions": settlement_positions,
            }

        if can_afford_road:
            return {
                "priority": "medium",
                "action": "build_road",
                "title": "建议延伸道路",
                "reason": "修路可以连接更多落点，为下一座村庄创造空间。",
                "targets": ["build-road-btn", "hex-map"],
                "suggested_build_mode": "road",
                "suggested_positions": road_positions,
            }

        if phase == GamePhase.TRADE:
            trade_hint = cls._build_trade_hint(player)
            if trade_hint:
                return trade_hint

        settlement_missing = cls._missing_resources(player, settlement_cost)
        if settlement_missing:
            missing_text = "、".join(
                f"{cls._resource_name_from_value(resource)} {amount}" for resource, amount in settlement_missing.items()
            )
            return {
                "priority": "medium",
                "action": "gather_for_settlement",
                "title": "先凑齐建村资源",
                "reason": f"距离下一座村庄还差: {missing_text}。可考虑交易或等待产出。",
                "targets": ["current-player-panel"],
                "suggested_build_mode": None,
                "suggested_positions": [],
                "missing_resources": settlement_missing,
            }

        return {
            "priority": "low",
            "action": "end_turn",
            "title": "可结束回合",
            "reason": "当前可执行的高收益动作较少，结束回合是稳妥选择。",
            "targets": ["end-turn-btn"],
            "suggested_build_mode": None,
            "suggested_positions": [],
        }

    @staticmethod
    def _resource_name_from_value(resource_value: str) -> str:
        for resource_type, resource_name in RESOURCE_NAME_ZH.items():
            if resource_type.value == resource_value:
                return resource_name
        return resource_value

    @staticmethod
    def _missing_resources(player, cost: Dict[ResourceType, int]) -> Dict[str, int]:
        missing: Dict[str, int] = {}
        for resource_type, required_amount in cost.items():
            current_amount = player.resources.get(resource_type)
            if current_amount < required_amount:
                missing[resource_type.value] = required_amount - current_amount
        return missing

    @classmethod
    def _build_trade_hint(cls, player) -> Dict | None:
        tradable_resource = None
        tradable_count = 0
        for resource_type in [
            ResourceType.WOOD,
            ResourceType.BRICK,
            ResourceType.SHEEP,
            ResourceType.WHEAT,
            ResourceType.ORE,
        ]:
            count = player.resources.get(resource_type)
            if count >= 4 and count > tradable_count:
                tradable_resource = resource_type
                tradable_count = count

        if tradable_resource is None:
            return None

        desired_resource = cls._best_trade_target(player)
        tradable_name = RESOURCE_NAME_ZH[tradable_resource]
        if desired_resource is None:
            reason = f"你有 4 张{tradable_name}，可向银行按 4:1 兑换任意资源。"
        else:
            desired_name = RESOURCE_NAME_ZH[desired_resource]
            reason = f"可用 4 张{tradable_name}向银行换 1 张{desired_name}，更接近关键建造。"

        return {
            "priority": "medium",
            "action": "trade_with_bank",
            "title": "建议进行 4:1 银行交易",
            "reason": reason,
            "targets": ["trade-bank-btn"],
            "suggested_build_mode": None,
            "suggested_positions": [],
            "trade_suggestion": {
                "give": {tradable_resource.value: 4},
                "receive": {desired_resource.value: 1} if desired_resource else {},
            },
        }

    @staticmethod
    def _best_trade_target(player) -> ResourceType | None:
        city_shortage = GuideService._missing_resources(player, Building.get_cost(BuildingType.CITY))
        if city_shortage:
            top = max(city_shortage.items(), key=lambda item: item[1])[0]
            return ResourceType(top)

        settlement_shortage = GuideService._missing_resources(
            player, Building.get_cost(BuildingType.SETTLEMENT)
        )
        if settlement_shortage:
            top = max(settlement_shortage.items(), key=lambda item: item[1])[0]
            return ResourceType(top)

        return None

    @classmethod
    def _find_valid_settlement_positions(
        cls, game_state: GameState, player_id: int
    ) -> List[List[int]]:
        return cls._find_valid_positions(game_state, player_id, for_city=False, for_road=False)

    @classmethod
    def _find_valid_city_positions(cls, game_state: GameState, player_id: int) -> List[List[int]]:
        return cls._find_valid_positions(game_state, player_id, for_city=True, for_road=False)

    @classmethod
    def _find_valid_road_positions(cls, game_state: GameState, player_id: int) -> List[List[int]]:
        return cls._find_valid_positions(game_state, player_id, for_city=False, for_road=True)

    @classmethod
    def _find_valid_positions(
        cls,
        game_state: GameState,
        player_id: int,
        for_city: bool,
        for_road: bool,
    ) -> List[List[int]]:
        if not game_state.hex_map or not game_state.hex_map.hexagons:
            return []

        valid_positions: List[List[int]] = []
        visited: set[Tuple[int, int, int]] = set()

        for hexagon in game_state.hex_map.hexagons:
            for direction in range(6):
                pos = (hexagon.q, hexagon.r, direction)
                if pos in visited:
                    continue
                visited.add(pos)

                is_valid = False
                if for_road:
                    edge = HexEdge(*pos)
                    is_valid = game_state.can_place_road(edge, player_id)
                elif for_city:
                    vertex = HexVertex(*pos)
                    is_valid = game_state.can_place_city(vertex, player_id)
                else:
                    vertex = HexVertex(*pos)
                    is_valid = game_state.can_place_settlement(vertex, player_id)

                if is_valid:
                    valid_positions.append([pos[0], pos[1], pos[2]])
                    if len(valid_positions) >= cls.MAX_SUGGESTED_POSITIONS:
                        return valid_positions

        return valid_positions
