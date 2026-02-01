# process_screenshots.py
import os
import subprocess
from loguru import logger
import asyncio

# --- Основные настройки ---
PROCESSED_BOOKMARKS_DIR = "frontend/nuxt-app/public/processed_bookmarks"
# Ограничение на количество скриншотов для обработки (для тестирования)
SCREENSHOT_PROCESS_LIMIT = 1000

TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
JPEG_QUALITY = 85 # Качество JPEG от 1 (худшее) до 100 (лучшее)

async def process_single_screenshot(bookmark_id: str, input_png_path: str):
    """
    Обрабатывает один скриншот с помощью FFmpeg:
    масштабирует с обрезкой до 1280x720 и конвертирует в JPG.
    """
    logger.info(f"Обработка скриншота для ID: {bookmark_id}")

    # Путь для сохранения нового JPG файла
    output_png_path = os.path.join(PROCESSED_BOOKMARKS_DIR, bookmark_id, f"screenshot_{TARGET_WIDTH}x{TARGET_HEIGHT}.png")

    # Команда FFmpeg для масштабирования с обрезкой и конвертации в JPG
    command = [
        "ffmpeg",
        "-i", input_png_path,
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        # "-q:v", str(JPEG_QUALITY), # Этот параметр не применим к PNG
        "-y", # Перезаписывать файл без подтверждения
        output_png_path
    ]

    try:
        # Запускаем FFmpeg как подпроцесс
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, command, stdout=stdout, stderr=stderr
            )
        
        logger.success(f"Успешно обработан скриншот для ID {bookmark_id}: {output_png_path}")

    except FileNotFoundError:
        logger.error("Ошибка: ffmpeg не найден. Убедитесь, что он установлен и доступен в PATH.")
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Ошибка FFmpeg при обработке скриншота для ID {bookmark_id} (Код: {e.returncode}):\n"
            f"STDOUT: {e.stdout.decode()}\nSTDERR: {e.stderr.decode()}"
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обработке скриншота для ID {bookmark_id}: {e}")


async def main():
    logger.info("Запуск обработки скриншотов...")

    all_bookmark_dirs = sorted([d for d in os.listdir(PROCESSED_BOOKMARKS_DIR) if os.path.isdir(os.path.join(PROCESSED_BOOKMARKS_DIR, d))])
    
    if not all_bookmark_dirs:
        logger.info(f"В папке '{PROCESSED_BOOKMARKS_DIR}' не найдено обработанных закладок.")
        return

    screenshots_to_process = []
    processed_count = 0
    for bookmark_dir in all_bookmark_dirs:
        png_file_path = os.path.join(PROCESSED_BOOKMARKS_DIR, bookmark_dir, "screenshot.png")
        # Проверяем, существует ли файл и не пуст ли он
        if os.path.isfile(png_file_path) and os.path.getsize(png_file_path) > 0:
            screenshots_to_process.append(bookmark_dir)
            processed_count += 1
            if SCREENSHOT_PROCESS_LIMIT and processed_count >= SCREENSHOT_PROCESS_LIMIT:
                break
    
    if not screenshots_to_process:
        logger.info(f"В папке '{PROCESSED_BOOKMARKS_DIR}' не найдено валидных скриншотов для обработки.")
        return

    logger.info(f"Найдено {len(screenshots_to_process)} скриншотов для обработки.")

    for bookmark_id in screenshots_to_process:
        png_file_path = os.path.join(PROCESSED_BOOKMARKS_DIR, bookmark_id, "screenshot.png")
        await process_single_screenshot(bookmark_id, png_file_path)

    logger.info("Обработка скриншотов завершена.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
