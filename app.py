from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from api.routes import api_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    return {
        'name': 'CatanForge API',
        'version': '1.0.0',
        'status': 'running'
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

