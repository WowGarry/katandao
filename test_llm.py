import os
import sys

# 添加项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from services.llm_service import get_llm_service
from referee.smart_player import SmartPlayer

def test_deepseek_basic():
    """测试 DeepSeek 基础功能"""
    print("=== 测试 DeepSeek 基础功能 ===")
    
    try:
        llm_service = get_llm_service()
        
        # 测试简单提问
        prompt = "请用一句话回答：卡坦岛是什么游戏？"
        response = llm_service.ask(prompt, max_tokens=50)
        
        print(f"提问: {prompt}")
        print(f"回答: {response}")
        
        if "DeepSeek API 请求失败" not in response:
            print("✓ DeepSeek 基础功能测试通过")
            return True
        else:
            print(f"✗ API 请求失败: {response}")
            return False
            
    except Exception as e:
        print(f"✗ DeepSeek 基础功能测试失败: {e}")
        return False

def test_deepseek_trade():
    """测试 DeepSeek 交易对话生成"""
    print("\n=== 测试 DeepSeek 交易对话生成 ===")
    
    try:
        llm_service = get_llm_service()
        
        # 测试交易对话
        offer = {"木材": 2, "砖块": 1}
        request = {"小麦": 1, "羊毛": 1}
        
        dialogue = llm_service.generate_trade_dialogue(offer, request)
        
        print(f"提供: {offer}")
        print(f"请求: {request}")
        print(f"生成对话: {dialogue}")
        
        if "DeepSeek API 请求失败" not in dialogue:
            print("✓ DeepSeek 交易对话测试通过")
            return True
        else:
            print(f"✗ API 请求失败: {dialogue}")
            return False
            
    except Exception as e:
        print(f"✗ DeepSeek 交易对话测试失败: {e}")
        return False

def test_smart_player():
    """测试 SmartPlayer 集成"""
    print("\n=== 测试 SmartPlayer 集成 ===")
    
    try:
        # 创建模拟游戏状态
        mock_game_state = {
            'players': [
                {
                    'player_id': 1,
                    'resources': {
                        'wood': 3,
                        'brick': 2, 
                        'sheep': 1,
                        'wheat': 1,
                        'ore': 0
                    }
                }
            ]
        }
        
        player = SmartPlayer(1)
        
        # 测试建造决策
        build_decision = player.decide_build(mock_game_state)
        print(f"建造决策: {build_decision}")
        
        # 测试交易决策  
        trade_decision = player.decide_trade(mock_game_state)
        print(f"交易决策: {trade_decision}")
        
        print("✓ SmartPlayer 集成测试通过")
        return True
        
    except Exception as e:
        print(f"✗ SmartPlayer 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始 DeepSeek LLM 服务测试...")
    
    # 检查环境变量
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 未设置 DEEPSEEK_API_KEY 环境变量")
        print("请执行: set DEEPSEEK_API_KEY=你的API密钥")
        exit(1)
    
    tests = [
        test_deepseek_basic,
        test_deepseek_trade,
        test_smart_player
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 所有测试通过！DeepSeek LLM 服务正常工作")
    else:
        print("⚠ 部分测试失败，请检查上述错误信息")