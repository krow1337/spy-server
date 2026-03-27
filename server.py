import asyncio
import websockets
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import logging
import os
import base64
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

connected_clients = set()

# Создаём папки для данных
os.makedirs('frames', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# ========== HTTP ЭНДПОИНТЫ ==========

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "online",
        "services": ["sms", "notification", "camera"],
        "endpoints": {
            "sms": "/sms (POST)",
            "notification": "/notification (POST)",
            "camera": "ws://server:port (WebSocket)"
        }
    })

@app.route('/sms', methods=['POST'])
def sms():
    try:
        data = request.json
        sender = data.get('sender', 'unknown')
        message = data.get('message', '')
        timestamp = data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        logger.info(f"📱 SMS от {sender}: {message}")
        
        with open('logs/sms.txt', 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {sender}: {message}\n")
        
        return jsonify({"status": "ok", "received": True})
    except Exception as e:
        logger.error(f"SMS error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/notification', methods=['POST'])
def notification():
    try:
        data = request.json
        app_name = data.get('app', 'unknown')
        title = data.get('title', '')
        text = data.get('text', '')
        
        logger.info(f"🔔 Уведомление от {app_name}: {title}")
        
        with open('logs/notifications.txt', 'a', encoding='utf-8') as f:
            f.write(f"[{app_name}] {title}: {text}\n")
        
        return jsonify({"status": "ok", "received": True})
    except Exception as e:
        logger.error(f"Notification error: {e}")
        return jsonify({"status": "error"}), 500

# ========== WEBSOCKET ДЛЯ КАМЕРЫ ==========

async def handle_camera(websocket, path):
    client_id = id(websocket)
    logger.info(f"📸 Камера #{client_id} подключена")
    connected_clients.add(websocket)
    
    try:
        async for message in websocket:
            logger.info(f"📸 Кадр от #{client_id}, размер: {len(message)} байт")
            
            # Сохраняем кадр
            try:
                image_data = base64.b64decode(message)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"frames/frame_{timestamp}.jpg"
                with open(filename, "wb") as f:
                    f.write(image_data)
                logger.info(f"💾 Сохранён: {filename}")
            except:
                pass  # не base64 или не изображение
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"📸 Камера #{client_id} отключилась")
    finally:
        connected_clients.remove(websocket)

async def start_websocket():
    async with websockets.serve(handle_camera, "0.0.0.0", 8765):
        logger.info("🚀 WebSocket сервер на порту 8765")
        await asyncio.Future()

# ========== ЗАПУСК ==========

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def run_websocket():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_websocket())
    
    threading.Thread(target=run_websocket, daemon=True).start()
    
    logger.info("🌐 HTTP сервер на порту 8080")
    app.run(host="0.0.0.0", port=8080)