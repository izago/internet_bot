import asyncio
import datetime
import os
import urllib.request
import urllib.parse
import pytz
import time
import json

# =====================================================
# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ===
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
# SPEED_THRESHOLD = 150  # ЗАКОММЕНТИРОВАНО - НЕ ИСПОЛЬЗУЕТСЯ

# ===== СПИСОК ИСТОЧНИКОВ ДЛЯ ТЕСТА =====
TEST_FILES = [
    "http://speedtest.tele2.net/10MB.zip",           # Tele2 10 МБ
    "http://speedtest.tele2.net/1MB.zip",            # Tele2 1 МБ
    "https://proof.ovh.net/files/10Mb.dat",          # OVH 10 МБ
    "https://proof.ovh.net/files/100Mb.dat",         # OVH 100 МБ
    "http://ipv4.download.thinkbroadband.com/10MB.zip", # ThinkBroadband
]

# =====================================================
# ===== СОСТОЯНИЯ =====
# =====================================================

is_connected = True
disconnect_start = None
# speed_low = False  # ЗАКОММЕНТИРОВАНО - НЕ ИСПОЛЬЗУЕТСЯ

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

def measure_speed():
    """Измерение скорости через скачивание файла с разных источников"""
    
    for url in TEST_FILES:
        try:
            print(f"📥 Пробую: {url}")
            
            # Получаем размер файла (Content-Length)
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                content_length = response.headers.get('Content-Length')
                if content_length is None:
                    print("⚠️ Не удалось определить размер файла, пропускаю...")
                    continue
                
                file_size_bytes = int(content_length)
                file_size_bits = file_size_bytes * 8
                file_size_mb = file_size_bytes / (1024 * 1024)
                
                print(f"📦 Размер: {file_size_mb:.1f} МБ")
            
            # Скачиваем файл с замером времени
            start_time = time.time()
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                # Читаем данные (но не сохраняем их)
                while response.read(8192):
                    pass
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 0:
                speed_mbps = file_size_bits / duration / 1_000_000
                print(f"✅ Успешно! Скорость: {speed_mbps:.2f} Мбит/сек")
                return speed_mbps
            else:
                print("⚠️ Слишком быстро, пропускаю...")
                continue
                
        except Exception as e:
            print(f"❌ Ошибка с {url}: {e}")
            continue
    
    print("❌ Все источники не работают!")
    return None

async def check_internet():
    global is_connected, disconnect_start
    # global speed_low  # ЗАКОММЕНТИРОВАНО - НЕ ИСПОЛЬЗУЕТСЯ
    
    try:
        print("🔄 Проверяю скорость через скачивание файла...")
        
        # Измеряем скорость
        download_speed = measure_speed()
        now = get_moscow_time()
        
        if download_speed is None:
            raise Exception("Не удалось измерить скорость (все источники недоступны)")
        
        print(f"📊 Скорость: {download_speed:.2f} Мбит/сек")
        
        # ===== ВОССТАНОВЛЕНИЕ ПОСЛЕ РАЗРЫВА =====
        if not is_connected:
            is_connected = True
            reconnect_time = now
            delta = (reconnect_time - disconnect_start).total_seconds()
            
            send_telegram_message(f"✅ Интернет соединение ВОССТАНОВЛЕНО в {format_time(reconnect_time)}")
            send_telegram_message(f"⏱ Интернета не было: {format_delta(delta)}")
            # speed_low = False  # ЗАКОММЕНТИРОВАНО - НЕ ИСПОЛЬЗУЕТСЯ
        
        # ==========================================
        # БЛОК ПРОВЕРКИ СКОРОСТИ - ПОЛНОСТЬЮ ЗАКОММЕНТИРОВАН
        # ==========================================
        # if is_connected:
        #     if download_speed < SPEED_THRESHOLD:
        #         send_telegram_message(
        #             f"⚠️ СКОРОСТЬ НИЗКАЯ! {format_time(now)}\n"
        #             f"Текущая: {download_speed:.2f} Мбит/сек (ниже {SPEED_THRESHOLD})"
        #         )
        #         speed_low = True
        #     elif download_speed >= SPEED_THRESHOLD and speed_low:
        #         send_telegram_message(
        #             f"✅ Скорость ВОССТАНОВЛЕНА в {format_time(now)}\n"
        #             f"Текущая: {download_speed:.2f} Мбит/сек"
        #         )
        #         speed_low = False
                
    except Exception as e:
        now = get_moscow_time()
        if is_connected:
            is_connected = False
            disconnect_start = now
            # speed_low = False  # ЗАКОММЕНТИРОВАНО - НЕ ИСПОЛЬЗУЕТСЯ
            send_telegram_message(f"❌ Интернет соединение РАЗОРВАНО в {format_time(now)}")
            print(f"❌ Ошибка: {e}")

async def main_loop():
    print("🔄 Запускаю мониторинг...")
    print(f"📡 Проверка каждые {CHECK_INTERVAL} секунд")
    # print(f"⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")  # ЗАКОММЕНТИРОВАНО
    
    send_telegram_message("🚀 Бот мониторинга интернета запущен на Railway!")
    # send_telegram_message(f"📊 Измерение через скачивание файла\n⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")  # ЗАКОММЕНТИРОВАНО
    
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

    STOP_BOT = os.getenv("STOP_BOT")
    
    if STOP_BOT == "1":
        print("🛑 Бот остановлен по запросу (STOP_BOT=1)")
        return

    
    print("=" * 60)
    print("🚀 БОТ МОНИТОРИНГА ИНТЕРНЕТА")
    print("=" * 60)
    print(f"📡 Проверка каждые {CHECK_INTERVAL} сек")
    # print(f"⚡ Порог скорости: {SPEED_THRESHOLD} Мбит/сек")  # ЗАКОММЕНТИРОВАНО
    print(f"🕐 Часовой пояс: Москва")
    print("📊 Метод: Скачивание файла (несколько источников)")
    print("=" * 60)
    
    await main_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
