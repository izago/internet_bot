
import asyncio
import datetime
import json
import urllib.request
import urllib.parse
import speedtest
import pytz
import time
import os

# ===== НАСТРОЙКИ =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
CHECK_INTERVAL = 60  # Проверка каждые 60 секунд (меньше нагрузка)
SPEED_THRESHOLD = 200

# ===== СОСТОЯНИЯ =====
is_connected = True
disconnect_start = None
speed_low = False
last_speed = 0

def get_moscow_time():
    return datetime.datetime.now(MOSCOW_TZ)

def format_time(dt):
    return dt.strftime("%H:%M:%S")

def format_delta(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}ч {minutes}м {secs}с"
    elif minutes > 0:
        return f"{minutes}м {secs}с"
    else:
        return f"{secs}с"

def send_telegram_message(text):
    """Отправка сообщения через urllib (встроенный модуль)"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 150:
                return True
            else:
                print(f"Ошибка HTTP: {response.getcode()}")
                return False
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

async def check_internet():
    global is_connected, disconnect_start, speed_low, last_speed
    
    try:
        print("🔄 Проверяю скорость...")
        
        # Создаём объект Speedtest с таймаутом
        st = speedtest.Speedtest()
        st.get_best_server()
        
        # Измеряем скорость с таймаутом
        download_speed = st.download() / 1_000_000
        now = get_moscow_time()
        last_speed = download_speed
        
        print(f"📊 Скорость: {download_speed:.2f} Мбит/сек")
        
        # ===== ВОССТАНОВЛЕНИЕ ПОСЛЕ РАЗРЫВА =====
        if not is_connected:
            is_connected = True
            reconnect_time = now
            delta = (reconnect_time - disconnect_start).total_seconds()
            
            send_telegram_message(
                f"✅ Интернет соединение ВОССТАНОВЛЕНО в {format_time(reconnect_time)}"
            )
            send_telegram_message(
                f"⏱ Интернета не было: {format_delta(delta)}"
            )
            speed_low = False
        
        # ===== ПРОВЕРКА СКОРОСТИ =====
        if is_connected:
            if download_speed < SPEED_THRESHOLD:
                send_telegram_message(
                    f"⚠️ Скорость УПАЛА в {format_time(now)}\n"
                    f"Текущая: {download_speed:.2f} Мбит/сек (ниже {SPEED_THRESHOLD})"
                )
                speed_low = True
                
            elif download_speed >= SPEED_THRESHOLD and speed_low:
                send_telegram_message(
                    f"✅ Скорость ВОССТАНОВЛЕНА в {format_time(now)}\n"
                    f"Текущая: {download_speed:.2f} Мбит/сек"
                )
                speed_low = False
                
    except Exception as e:
        # ===== РАЗРЫВ ИНТЕРНЕТА =====
        now = get_moscow_time()
        if is_connected:
            is_connected = False
            disconnect_start = now
            speed_low = False
            send_telegram_message(
                f"❌ Интернет соединение РАЗОРВАНО в {format_time(now)}"
            )
            print(f"❌ Ошибка: {e}")
        
        # Если ошибка не связана с интернетом, показываем её
        if "speedtest" not in str(e).lower():
            print(f"⚠️ Другая ошибка: {e}")

async def main_loop():
    """Основной цикл с проверкой"""
    print("🔄 Запускаю мониторинг...")
    
    # Отправляем приветственное сообщение
    send_telegram_message("🚀 Бот мониторинга интернета запущен!")
    
    while True:
        try:
            await check_internet()
        except Exception as e:
            print(f"❌ Критическая ошибка в цикле: {e}")
        
        # Ждём перед следующей проверкой
        for i in range(CHECK_INTERVAL, 0, -1):
            print(f"⏳ Следующая проверка через {i} сек...", end='\r')
            await asyncio.sleep(1)
        print()  # Переход на новую строку

async def main():
    print("=" * 50)
    print("🚀 БОТ МОНИТОРИНГА ИНТЕРНЕТА")
    print("=" * 50)
    print(f"📡 Проверка каждые {CHECK_INTERVAL} секунд")
    print(f"⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")
    print(f"🕐 Часовой пояс: Москва")
    print("=" * 50)
    
    await main_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Фатальная ошибка: {e}")
        input("Нажми Enter для выхода...")