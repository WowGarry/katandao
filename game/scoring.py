"""最长道路、最大军队等特殊计分。"""
from __future__ import annotations

from typing import Dict, List, Tuple

from game.game_state import GameState
from models.building import BuildingType
from models.hexagon import HexEdge, edge_endpoints, vertex_identity_key


def _vertex_passable_for_road(
    vertex_key: Tuple[Tuple[int, int], ...], player_id: int, game_state: GameState
) -> bool:
    """该顶点是否允许己方道路「穿过」以连接相邻路段（对手定居点/城市会阻断）。"""
    b = game_state.vertex_buildings.get(vertex_key)
    if b is None:
        return True
    if b.type == BuildingType.ROAD:
        return True
    if b.player_id == player_id:
        return True
    return False


def _edge_vertex_keys(game_state: GameState, edge_key) -> Tuple[Tuple[Tuple[int, int], ...], Tuple[Tuple[int, int], ...]]:
    b = game_state.edge_buildings[edge_key]
    e = HexEdge(*b.position)
    v1, v2 = edge_endpoints(e)
    hm = game_state.hex_map
    if not hm:
        return ((), ())
    k1 = vertex_identity_key(v1.q, v1.r, v1.direction, hm)
    k2 = vertex_identity_key(v2.q, v2.r, v2.direction, hm)
    return (k1, k2)


def _edges_adjacent(
    game_state: GameState, player_id: int, ek_a, ek_b
) -> bool:
    """两条己方道路是否共享同一可穿过顶点。"""
    k1a, k1b = _edge_vertex_keys(game_state, ek_a)
    k2a, k2b = _edge_vertex_keys(game_state, ek_b)
    for k in (k1a, k1b):
        for k2 in (k2a, k2b):
            if k == k2 and _vertex_passable_for_road(k, player_id, game_state):
                return True
    return False


def _dfs_longest_path_from(
    start_edge: Tuple,
    adj: Dict[Tuple, List[Tuple]],
) -> int:
    """从 start_edge 出发的最长简单路径（边数）。"""

    def dfs(cur: Tuple, visited: set) -> int:
        best = 0
        for nxt in adj.get(cur, []):
            if nxt in visited:
                continue
            visited.add(nxt)
            best = max(best, dfs(nxt, visited))
            visited.remove(nxt)
        return best + 1

    return dfs(start_edge, {start_edge})


def compute_longest_road_length(game_state: GameState, player_id: int) -> int:
    """计算己方连续道路段数的最大值（对手定居点/城市处阻断）。"""
    edges: List[Tuple] = []
    for ek, b in game_state.edge_buildings.items():
        if b.player_id != player_id:
            continue
        edges.append(ek)
    if not edges:
        return 0

    adj: Dict[Tuple, List[Tuple]] = {e: [] for e in edges}
    for i, e1 in enumerate(edges):
        for e2 in edges[i + 1 :]:
            if _edges_adjacent(game_state, player_id, e1, e2):
                adj[e1].append(e2)
                adj[e2].append(e1)

    best = 0
    for e in edges:
        best = max(best, _dfs_longest_path_from(e, adj))
    return best


def _apply_longest_road(game_state: GameState) -> None:
    lengths = {p.player_id: compute_longest_road_length(game_state, p.player_id) for p in game_state.players}
    max_len = max(lengths.values()) if lengths else 0
    if max_len < 5:
        for p in game_state.players:
            if p.has_longest_road:
                p.has_longest_road = False
                p.update_victory_points()
        return

    leaders = [pid for pid, ln in lengths.items() if ln == max_len]
    current_holder = next((p for p in game_state.players if p.has_longest_road), None)

    if len(leaders) == 1:
        winner_id = leaders[0]
        for p in game_state.players:
            p.has_longest_road = p.player_id == winner_id
            p.update_victory_points()
        return

    if current_holder and current_holder.player_id in leaders:
        for p in game_state.players:
            p.has_longest_road = p.player_id == current_holder.player_id
            p.update_victory_points()
        return

    for p in game_state.players:
        if p.has_longest_road:
            p.has_longest_road = False
            p.update_victory_points()


def _apply_largest_army(game_state: GameState) -> None:
    counts = {p.player_id: p.knights_played for p in game_state.players}
    max_k = max(counts.values()) if counts else 0
    if max_k < 3:
        for p in game_state.players:
            if p.has_largest_army:
                p.has_largest_army = False
                p.update_victory_points()
        return

    leaders = [pid for pid, c in counts.items() if c == max_k]
    current_holder = next((p for p in game_state.players if p.has_largest_army), None)

    if len(leaders) == 1:
        winner_id = leaders[0]
        for p in game_state.players:
            p.has_largest_army = p.player_id == winner_id
            p.update_victory_points()
        return

    if current_holder and current_holder.player_id in leaders:
        for p in game_state.players:
            p.has_largest_army = p.player_id == current_holder.player_id
            p.update_victory_points()
        return

    for p in game_state.players:
        if p.has_largest_army:
            p.has_largest_army = False
            p.update_victory_points()


def update_special_scoring(game_state: GameState) -> None:
    """在道路/定居点/骑士数量变化后重算最长道路与最大军队。"""
    _apply_longest_road(game_state)
    _apply_largest_army(game_state)
