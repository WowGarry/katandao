from services.llm_service import get_llm_service

# 全局变量
_game_state = None
_logger = None

def set_game_context(game_state, logger):
    """
    设置游戏上下文
    
    Args:
        game_state: 游戏状态对象
        logger: 日志记录器对象
    """
    global _game_state, _logger
    _game_state = game_state
    _logger = logger

def read_resource_state(player_id):
    """
    读取玩家资源状态
    
    Args:
        player_id: 玩家ID
        
    Returns:
        玩家资源字典，如果出错返回空字典
    """
    global _game_state
    
    if _game_state is None:
        return {}
    
    try:
        player = _game_state.get_player(player_id)
        if player and hasattr(player, 'resources'):
            return player.resources
        return {}
    except Exception as e:
        return {}

def read_public_lib(limit=10):
    """
    读取公共事件日志
    
    Args:
        limit: 返回的记录条数限制
        
    Returns:
        事件列表，如果出错返回空列表
    """
    global _logger
    
    if _logger is None:
        return []
    
    try:
        events = _logger.get_events()
        if events and len(events) > limit:
            return events[-limit:]
        return events or []
    except Exception as e:
        return []

def askLLM(prompt, max_tokens=100):
    """
    向LLM提问
    
    Args:
        prompt: 提示词
        max_tokens: 最大token数
        
    Returns:
        LLM响应内容，如果出错返回空字符串
    """
    try:
        print(f"[askLLM] 开始调用LLM服务，提示词长度: {len(prompt)}")
        llm_service = get_llm_service()
        response = llm_service.ask(prompt, max_tokens)
        print(f"[askLLM] LLM服务返回，响应长度: {len(response) if response else 0}")
        return response
    except Exception as e:
        error_msg = f"LLM调用失败: {str(e)}"
        print(f"[askLLM] {error_msg}")
        import traceback
        print(f"[askLLM] 错误详情: {traceback.format_exc()}")
        return error_msg
def generate_trade_dialogue(offer, request):
    """
    生成交易对话
    
    Args:
        offer: 提供的物品
        request: 请求的物品
        
    Returns:
        生成的交易对话，如果出错返回简单文本
    """
    try:
        llm_service = get_llm_service()
        return llm_service.generate_trade_dialogue(offer, request)
    except Exception as e:
        return f"交易对话：提供{offer}，请求{request}"


def log_ai_speech(game_id,player_id, player_name, speech):
    """
    记录AI发言到游戏日志
    """
    global _logger
    
    if _logger is None:
        print(f"💬 [{player_name}] {speech}")
        return
    
    try:
        # 假设logger有记录发言的方法
        if hasattr(_logger, 'log_ai_speech'):
            _logger.log_ai_speech(player_id, player_name, speech)
        else:
            # 备用方案：记录为普通事件
            _logger.log_event(f"{player_name} 发言: {speech}")
    except Exception as e:
        print(f"记录AI发言失败: {e}")
        print(f"💬 [{player_name}] {speech}")