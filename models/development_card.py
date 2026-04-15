"""卡坦岛发展卡（基础版 25 张）"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from models.resource import ResourceType

# 购买成本：1 羊毛 + 1 小麦 + 1 矿石
DEVELOPMENT_CARD_COST: Dict[ResourceType, int] = {
    ResourceType.SHEEP: 1,
    ResourceType.WHEAT: 1,
    ResourceType.ORE: 1,
}


class DevelopmentCardType(str, Enum):
    """发展卡类型（与牌堆内容一致）。"""

    KNIGHT = "knight"  # 骑士：移动强盗并抢夺
    VICTORY_POINT = "victory_point"  # 胜利点：持有时 +1 分，不公开
    ROAD_BUILDING = "road_building"  # 道路建设：免费放置 2 条道路
    MONOPOLY = "monopoly"  # 垄断：指定资源，他人全交给你
    YEAR_OF_PLENTY = "year_of_plenty"  # 丰收：从银行取 2 张任意资源


def build_base_deck() -> List[DevelopmentCardType]:
    """标准 25 张：14 骑士 + 5 胜利点 + 2 道路 + 2 垄断 + 2 丰收。"""
    deck: List[DevelopmentCardType] = []
    deck.extend([DevelopmentCardType.KNIGHT] * 14)
    deck.extend([DevelopmentCardType.VICTORY_POINT] * 5)
    deck.extend([DevelopmentCardType.ROAD_BUILDING] * 2)
    deck.extend([DevelopmentCardType.MONOPOLY] * 2)
    deck.extend([DevelopmentCardType.YEAR_OF_PLENTY] * 2)
    assert len(deck) == 25
    return deck


def shuffle_deck(deck: List[DevelopmentCardType], seed: Optional[int] = None) -> None:
    if seed is not None:
        random.seed(seed)
    random.shuffle(deck)


@dataclass
class DevelopmentCardInstance:
    """玩家手中的单张发展卡实例。"""

    instance_id: str
    card_type: DevelopmentCardType
    bought_this_turn: bool = False

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "card_type": self.card_type.value,
            "bought_this_turn": self.bought_this_turn,
        }

    @staticmethod
    def new(card_type: DevelopmentCardType, bought_this_turn: bool = False) -> DevelopmentCardInstance:
        return DevelopmentCardInstance(
            instance_id=str(uuid.uuid4()),
            card_type=card_type,
            bought_this_turn=bought_this_turn,
        )
