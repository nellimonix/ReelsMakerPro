APP_NAME = "ReelsMaker Pro [mod by llimonix]"
APP_VERSION = "1.1.1"
LOG_FILE = "app.log"
FFMPEG_EXE_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

VIDEO_EXTENSIONS = [
    ".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv"
]
GIF_EXTENSIONS = [".gif"]
VALID_INPUT_EXTENSIONS = VIDEO_EXTENSIONS + GIF_EXTENSIONS

FILTERS = {
    "Нет фильтра": "",
    "Случ. цвет (яркость/контраст/...)": "eq=brightness={br}:contrast={ct}:saturation={sat},hue=h={hue}",
    "Черно-белое": "hue=s=0",
    "Сепия": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0",
    "Инверсия": "negate",
    "Размытие (легкое)": "gblur=sigma=2",
    "Размытие (сильное)": "gblur=sigma=10",
    "Отразить по горизонтали": "hflip",
    "Отразить по вертикали": "vflip",
    "Пикселизация": "scale=iw/10:ih/10,scale=iw*10:ih*10:flags=neighbor",
    "VHS (шум, сдвиг)": "chromashift=1:1,noise=alls=20:allf=t+u",
    "Повыш. контрастность": "eq=contrast=1.5",
    "Пониж. контрастность": "eq=contrast=0.7",
    "Повыш. насыщенность": "eq=saturation=1.5",
    "Пониж. насыщенность": "eq=saturation=0.5",
    "Повыш. яркость": "eq=brightness=0.15",
    "Пониж. яркость": "eq=brightness=-0.15",
    "Холодный фильтр": "curves=b='0/0 0.4/0.5 1/1':g='0/0 0.4/0.4 1/1'",
    "Теплый фильтр": "curves=r='0/0 0.4/0.5 1/1':g='0/0 0.6/0.6 1/1'",
    "Случайный фильтр": "RANDOM_PLACEHOLDER",
}

OVERLAY_POSITIONS = {
    "Верх-Лево": "x=20:y=70",
    "Верх-Центр": "x=(W-w)/2:y=10",
    "Верх-Право": "x=W-w-10:y=10",
    "Середина-Лево": "x=10:y=(H-h)/2",
    "Середина-Центр": "x=(W-w)/2:y=(H-h)/2",
    "Середина-Право": "x=W-w-10:y=(H-h)/2",
    "Низ-Лево": "x=10:y=H-h-10",
    "Низ-Центр": "x=(W-w)/2:y=H-h-10",
    "Низ-Право": "x=W-w-10:y=H-h-10",
}

REELS_WIDTH = 1080
REELS_HEIGHT = 1920
REELS_FORMAT_NAME = f"Reels/TikTok ({REELS_WIDTH}x{REELS_HEIGHT})"
OUTPUT_FORMATS = ["Оригинальный", REELS_FORMAT_NAME]

CODECS = {
    "CPU (H.264 | libx264)": "libx264",
    "NVIDIA (H.264 | h264_nvenc)": "h264_nvenc",
    "NVIDIA (H.265 | hevc_nvenc)": "hevc_nvenc",
    "Intel (H.264 | h264_qsv)": "h264_qsv",
    "Intel (H.265 | hevc_qsv)": "hevc_qsv",
    "AMD (H.264 | h264_amf)": "h264_amf",
    "AMD (H.265 | hevc_amf)": "hevc_amf",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

WHISPER_LANGUAGES = [
    "Auto-detect", "Russian", "English", "Ukrainian",
    "German", "French", "Spanish", "Italian"
]
