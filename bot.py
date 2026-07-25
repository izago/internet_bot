import asyncio
import datetime
import os
import urllib.request
import urllib.parse
import pytz
import time
import speedtest

# =====================================================
# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====
# =====================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("❌ ОШИБКА: Не заданы переменные окружения")
    exit(1)

# =====================================================
# ===== НАСТРОЙКИ =====
# =====================================================

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
CHECK_INTERVAL = 60
SPEED_THRESHOLD = 150

# ID серверов Speedtest в России (можно заменить на свои)
# Москва, Санкт-Петербург, Екатеринбург
RUSSIAN_SERVERS = [10898, 7071, 5779, 17623, 23918]

# =====================================================
# ===== СОСТОЯНИЯ =====
# =====================================================

is_connected = True
disconnect_start = None
speed_low = False

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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

async def check_internet():
    global is_connected, disconnect_start, speed_low
    
    try:
        print("🔄 Проверяю скорость через Speedtest...")
        
        # Создаём объект Speedtest
        st = speedtest.Speedtest()
        
        # Пытаемся использовать российские серверы
        try:
            st.get_servers(RUSSIAN_SERVERS)
            st.get_best_server()
            print(f"📍 Сервер: {st.results.server['host']} ({st.results.server['country']})")
        except:
            # Если российские серверы не работают - используем автоматический выбор
            st.get_best_server()
            print(f"📍 Сервер: {st.results.server['host']} ({st.results.server['country']})")
        
        # Измеряем скорость
        download_speed = st.download() / 1_000_000
        now = get_moscow_time()
        
        print(f"📊 Скорость: {download_speed:.2f} Мбит/сек")
        
        # ===== ВОССТАНОВЛЕНИЕ ПОСЛЕ РАЗРЫВА =====
        if not is_connected:
            is_connected = True
            reconnect_time = now
            delta = (reconnect_time - disconnect_start).total_seconds()
            
            send_telegram_message(f"✅ Интернет соединение ВОССТАНОВЛЕНО в {format_time(reconnect_time)}")
            send_telegram_message(f"⏱ Интернета не было: {format_delta(delta)}")
            speed_low = False
        
        # ===== ПРОВЕРКА СКОРОСТИ =====
        if is_connected:
            if download_speed < SPEED_THRESHOLD:
                send_telegram_message(
                    f"⚠️ СКОРОСТЬ НИЗКАЯ! {format_time(now)}\n"
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
        now = get_moscow_time()
        if is_connected:
            is_connected = False
            disconnect_start = now
            speed_low = False
            send_telegram_message(f"❌ Интернет соединение РАЗОРВАНО в {format_time(now)}")
            print(f"❌ Ошибка: {e}")

async def main_loop():
    print("🔄 Запускаю мониторинг через Speedtest...")
    print(f"📡 Проверка каждые {CHECK_INTERVAL} секунд")
    print(f"⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")
    
    send_telegram_message("🚀 Бот мониторинга интернета запущен на Railway!")
    send_telegram_message(f"📊 Используется Speedtest с российскими серверами\n⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")
    
    while True:
        try:
            await check_internet()
        except Exception as e:
            print(f"❌ Критическая ошибка в цикле: {e}")
        
        for i in range(CHECK_INTERVAL, 0, -1):
            print(f"⏳ Следующая проверка через {i} сек...", end='\r')
            await asyncio.sleep(1)
        print()

async def main():
    print("=" * 60)
    print("🚀 БОТ МОНИТОРИНГА ИНТЕРНЕТА")
    print("=" * 60)
    print(f"📡 Проверка каждые {CHECK_INTERVAL} сек")
    print(f"⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")
    print(f"🕐 Часовой пояс: Москва")
    print("📊 Сервис: Speedtest (российские серверы)")
    print("=" * 60)
    
    await main_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
