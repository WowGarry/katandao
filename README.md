# CatanForge - 卡坦岛游戏后端

基于Flask的卡坦岛游戏服务器，支持AI策略对战。

## 安装依赖

```bash
cd katandao
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 运行服务器

```bash
python app.py
```

## 项目结构

```
katandao/
├── app.py                 # Flask应用入口
├── models/               # 游戏数据模型
│   ├── hexagon.py       # 六边形地图
│   ├── resource.py      # 资源定义
│   ├── player.py        # 玩家模型
│   └── building.py      # 建筑模型
├── game/                # 游戏逻辑
│   ├── map_generator.py # 地图生成
│   ├── game_state.py    # 游戏状态管理
│   └── rules.py         # 游戏规则引擎
├── referee/             # 裁判系统
│   └── catan_referee.py # 游戏裁判
├── api/                 # API接口
│   └── routes.py        # 路由定义
└── utils/               # 工具函数
    └── logger.py        # 日志系统
```

## API文档

见 API.md

