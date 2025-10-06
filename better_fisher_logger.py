# better_fisher_logger.py
# 这是一个阉割版的 better_fisher.py，仅用于记录钓鱼数据，不执行任何游戏操作。

import ctypes
import time
import sys
import random
import pygetwindow as gw
import json
import os
from datetime import datetime

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- 依赖库导入 ---
try:
    import pyautogui
except ImportError:
    print("错误: 缺少 pyautogui 库，请运行: pip install pyautogui")
    raise

import cv2
import numpy as np

USE_KEYBOARD = True
try:
    import keyboard
    import threading
except ImportError:
    USE_KEYBOARD = False
    print("错误: 缺少 keyboard 库，请运行: pip install keyboard")
    raise

# --- 彩色打印与全局控制 ---
# Windows控制台颜色代码
STD_OUTPUT_HANDLE = -11
FOREGROUND_BLUE = 0x09
FOREGROUND_GREEN = 0x0a
FOREGROUND_CYAN = 0x0b
FOREGROUND_RED = 0x0c
FOREGROUND_MAGENTA = 0x0d
FOREGROUND_YELLOW = 0x0e
FOREGROUND_WHITE = 0x0f

# 获取标准输出句柄
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

def set_color(color):
    """设置控制台文本颜色"""
    ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, color)

def cprint(message, color, end='\n'):
    """带颜色的打印函数"""
    set_color(color)
    print(message, end=end)
    set_color(FOREGROUND_WHITE) # 恢复默认白色

# 定义颜色类别
C_INFO = FOREGROUND_CYAN
C_STATUS = FOREGROUND_YELLOW
C_SUCCESS = FOREGROUND_GREEN
C_WARN = FOREGROUND_MAGENTA
C_ERROR = FOREGROUND_RED
C_DEBUG = FOREGROUND_WHITE
C_CONTROL = FOREGROUND_BLUE
C_GRAY = FOREGROUND_WHITE

is_running = True  # 控制主循环是否运行

# 统计文件路径
STATISTICS_FILE = "statistics-content.json"

# 检查统计文件是否存在，如果不存在则禁用统计功能
STATISTICS_ENABLED = os.path.exists(STATISTICS_FILE)
if STATISTICS_ENABLED:
    cprint(f"发现统计文件 {STATISTICS_FILE}，统计功能已启用", C_SUCCESS)
else:
    cprint(f"未发现统计文件 {STATISTICS_FILE}，统计功能已禁用", C_WARN)
cprint(f"按 Ctrl+K 可以{'创建统计文件并' if not STATISTICS_ENABLED else ''}切换统计功能", C_INFO)

# 鱼计数器
legendary_count = 0
epic_count = 0
rare_count = 0
extraordinary_count = 0
standard_count = 0
unknown_count = 0
airforce_count = 0

# 稀有度前景颜色映射
rarity_fg_colors = {
    'legendary': FOREGROUND_YELLOW,
    'epic': FOREGROUND_MAGENTA,
    'rare': FOREGROUND_CYAN,
    'extraordinary': FOREGROUND_GREEN,
    'standard': FOREGROUND_WHITE,
    'unknown': FOREGROUND_MAGENTA
}

# --- 统计功能 ---
def load_statistics():
    """从JSON文件加载统计数据"""
    if not os.path.exists(STATISTICS_FILE):
        return {"records": []}
    
    try:
        with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        cprint(f"加载统计文件失败: {e}", C_WARN)
        return {"records": []}

def save_statistics(data):
    """保存统计数据到JSON文件"""
    try:
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        cprint(f"保存统计文件失败: {e}", C_ERROR)

def load_all_statistics():
    """加载当前统计文件和所有归档文件的统计数据"""
    all_records = []
    
    current_stats = load_statistics()
    all_records.extend(current_stats.get("records", []))
    
    archive_dir = "archived-data"
    if os.path.exists(archive_dir):
        try:
            for filename in os.listdir(archive_dir):
                if filename.startswith("sc-") and filename.endswith(".json"):
                    filepath = os.path.join(archive_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            archive_stats = json.load(f)
                            all_records.extend(archive_stats.get("records", []))
                    except Exception as e:
                        cprint(f"加载归档文件 {filename} 失败: {e}", C_WARN)
        except Exception as e:
            cprint(f"读取归档目录失败: {e}", C_WARN)
    
    return {"records": all_records}

def record_fishing_result(rarity):
    """记录单次钓鱼结果"""
    if not STATISTICS_ENABLED:
        cprint("统计功能已禁用，跳过记录", C_DEBUG)
        return
        
    stats = load_statistics()
    
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rarity": rarity,
        "is_airforce": rarity == 'airforce'
    }
    
    stats["records"].append(record)
    save_statistics(stats)
    cprint(f"已记录钓鱼结果到 {STATISTICS_FILE}", C_DEBUG)

def display_statistics():
    """显示统计信息"""
    if not STATISTICS_ENABLED:
        cprint("统计功能已禁用，无法显示历史统计数据", C_INFO)
        cprint("按 Ctrl+K 可以启用统计功能", C_INFO)
        return
        
    current_stats = load_statistics()
    current_records = current_stats.get("records", [])
    
    if not current_records:
        cprint("暂无钓鱼统计数据", C_INFO)
        return
    
    current_rarity_counts = {r: 0 for r in rarity_fg_colors.keys()}
    current_rarity_counts['airforce'] = 0
    
    for record in current_records:
        rarity = record.get('rarity', 'airforce')
        if rarity in current_rarity_counts:
            current_rarity_counts[rarity] += 1
    
    current_total_attempts = len(current_records)
    current_airforce_count = current_rarity_counts['airforce']
    current_airforce_rate = (current_airforce_count / current_total_attempts * 100) if current_total_attempts > 0 else 0
    current_total_fish = current_total_attempts - current_airforce_count
    
    all_stats = load_all_statistics()
    all_records = all_stats.get("records", [])
    
    all_rarity_counts = {r: 0 for r in rarity_fg_colors.keys()}
    all_rarity_counts['airforce'] = 0
    
    for record in all_records:
        rarity = record.get('rarity', 'airforce')
        if rarity in all_rarity_counts:
            all_rarity_counts[rarity] += 1
    
    all_total_attempts = len(all_records)
    all_airforce_count = all_rarity_counts['airforce']
    all_airforce_rate = (all_airforce_count / all_total_attempts * 100) if all_total_attempts > 0 else 0
    all_total_fish = all_total_attempts - all_airforce_count
    
    cprint("\n" + "="*50, C_INFO)
    cprint("📊 钓鱼统计信息", C_INFO)
    cprint("="*50 + "\n", C_INFO)
    
    chinese_rarity_names = {
        'legendary': '传奇鱼', 'epic': '史诗鱼', 'rare': '稀有鱼',
        'extraordinary': '非凡鱼', 'standard': '标准鱼', 'unknown': '未知鱼'
    }
   
    for rarity in chinese_rarity_names.keys():
        current_count = current_rarity_counts[rarity]
        all_count = all_rarity_counts[rarity]
        
        if current_count > 0 or all_count > 0:
            current_rate = (current_count / current_total_fish * 100) if current_total_fish > 0 else 0
            all_rate = (all_count / all_total_fish * 100) if all_total_fish > 0 else 0
            zh_name = chinese_rarity_names[rarity]
            color = rarity_fg_colors[rarity] if rarity != 'unknown' else C_GRAY
            
            if current_count > 0:
                cprint(f"{zh_name}: {current_count}条 ({current_rate:.2f}%)  |  共 {all_count}条 ({all_rate:.2f}%)", color)
            elif all_count > 0:
                cprint(f"{zh_name}: 0条 (0.00%)  |  共 {all_count}条 ({all_rate:.2f}%)", color)
    
    cprint(f"空军: {current_airforce_count}次 ({current_airforce_rate:.2f}%)    |  共 {all_airforce_count}次 ({all_airforce_rate:.2f}%)", C_GRAY)
    cprint(f"样本量: {current_total_attempts}次            |  共 {all_total_attempts}次", C_INFO)
    cprint("\n" + "="*50 + "\n", C_INFO)

def toggle_run():
    global is_running
    is_running = not is_running
    status = '停止' if not is_running else '恢复运行'
    cprint(f"\n程序已 {status} (快捷键: Ctrl+L)\n", C_CONTROL)

def toggle_statistics():
    global STATISTICS_ENABLED
    if not os.path.exists(STATISTICS_FILE):
        try:
            with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)
            STATISTICS_ENABLED = True
            cprint(f"已成功创建统计文件 {STATISTICS_FILE}，统计功能已启用", C_SUCCESS)
        except Exception as e:
            cprint(f"创建统计文件失败: {e}", C_ERROR)
    else:
        STATISTICS_ENABLED = not STATISTICS_ENABLED
        status = '启用' if STATISTICS_ENABLED else '禁用'
        cprint(f"统计功能已{status}", C_SUCCESS)

def archive_statistics():
    if not os.path.exists(STATISTICS_FILE):
        cprint("统计文件不存在，无法归档", C_WARN)
        return
    
    try:
        archive_dir = "archived-data"
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = os.path.join(archive_dir, f"sc-{timestamp}.json")
        
        with open(STATISTICS_FILE, 'r', encoding='utf-8') as src, open(archive_filename, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"records": []}, f, ensure_ascii=False, indent=2)
        
        cprint(f"统计文件已归档为: {archive_filename}", C_SUCCESS)
        cprint("已创建新的统计文件，统计功能继续启用", C_SUCCESS)
        STATISTICS_ENABLED = True
    except Exception as e:
        cprint(f"归档统计文件失败: {e}", C_ERROR)

def keyboard_listener():
    ctrl_k_pressed = False
    while True:
        if USE_KEYBOARD:
            if keyboard.is_pressed('ctrl+l'):
                toggle_run()
                time.sleep(0.5)
            elif keyboard.is_pressed('ctrl+k'):
                if not ctrl_k_pressed:
                    ctrl_k_pressed = True
                    toggle_statistics()
                    time.sleep(0.5)
            elif keyboard.is_pressed('enter') and ctrl_k_pressed:
                archive_statistics()
                ctrl_k_pressed = False
                time.sleep(0.5)
            else:
                if ctrl_k_pressed and not keyboard.is_pressed('ctrl+k'):
                    ctrl_k_pressed = False
        time.sleep(0.1)

listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
listener_thread.start()

try:
    import win32gui
except ImportError:
    cprint("错误: 缺少 pywin32 库，请运行: pip install pywin32", C_ERROR)
    raise

# --- 窗口与坐标设置 ---
try:
    window = gw.getWindowsWithTitle("猛兽派对")[0]
    hwnd = win32gui.FindWindow(None, "猛兽派对")
except IndexError:
    cprint("错误: 未找到 '猛兽派对' 游戏窗口，请确保游戏正在运行。", C_ERROR)
    sys.exit(1)

rect = win32gui.GetClientRect(hwnd)
window_width = rect[2] - rect[0]
window_height = rect[3] - rect[1]
window_left = window.left
window_top = window.top

cprint(f"成功获取窗口: '猛兽派对'", C_INFO)
cprint(f"窗口大小: {window_width}x{window_height}  位置: ({window_left}, {window_top})", C_INFO)

COORDS_CONFIG = {
    "orange_zone": (0.5874, 0.9278, "张力表盘橙色区域"),
    "bite_mark": (0.5083, 0.2811, "咬钩感叹号"),
}

def get_abs_coord(ratio_x, ratio_y, is_orange_zone=False):
    if window_width == 3840 and window_height == 2160:
        return (2155, 1850) if is_orange_zone else (2113, 1910)
    return int(ratio_x * window_width + window_left), int(ratio_y * window_height + window_top)

CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1], is_orange_zone=True)
CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])

cprint(f"计算坐标: 橙色区({CHECK_X}, {CHECK_Y}), 感叹号({CHECK_X3}, {CHECK_Y3})", C_DEBUG)

# --- 像素与颜色检测 ---
def get_pointer_color(x, y):
    return pyautogui.pixel(x, y)

def color_changed(base_color, new_color, tolerance=12):
    return any(abs(b - n) > tolerance for b, n in zip(base_color, new_color))

def color_in_range(base_color, new_color, tolerance=12):
    return all(abs(b - n) <= tolerance for b, n in zip(base_color, new_color))

def detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5):
    rarity_colors = {
        'legendary': (255, 201, 53), 'epic': (171, 99, 255), 'rare': (106, 175, 246),
        'extraordinary': (142, 201, 85), 'standard': (183, 186, 193)
    }
    light_brown = (199, 118, 38)
    bright_yellow = (255, 232, 79)
    
    top, left, bottom, right = region
    if (bottom - top) * (right - left) <= 0: return 'airforce'
    
    match_counts = {rarity: 0 for rarity in rarity_colors}
    brown_count, yellow_count, sample_count = 0, 0, 0
    step = 10
    
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            try:
                color = get_pointer_color(x, y)
                rarity_matched = False
                for rarity, target_color in rarity_colors.items():
                    if color_in_range(target_color, color, tolerance):
                        match_counts[rarity] += 1
                        rarity_matched = True
                        break
                if not rarity_matched:
                    if color_in_range(light_brown, color, tolerance=5): brown_count += 1
                    elif color_in_range(bright_yellow, color, tolerance=10): yellow_count += 1
                sample_count += 1
            except Exception:
                sample_count += 1
    
    if sample_count == 0: return 'airforce'
    
    best_rarity = 'airforce'
    max_ratio = 0
    for rarity, count in match_counts.items():
        ratio = count / sample_count
        if ratio > max_ratio and ratio >= rarity_threshold:
            max_ratio = ratio
            best_rarity = rarity
    
    if best_rarity != 'airforce': return best_rarity
    
    brown_ratio = brown_count / sample_count
    yellow_ratio = yellow_count / sample_count
    if brown_ratio >= indicator_threshold or yellow_ratio >= indicator_threshold:
        return 'unknown'
        
    return 'airforce'

# --- 混合匹配咬钩检测 ---
center_x, center_y = window_left + window_width // 2, window_top + window_height // 2
roi_width = int(window_width * 0.08 * 2)
roi_height = int(window_height * 0.40)
roi_x = center_x - roi_width // 2
roi_y = center_y - roi_height
roi_search_area = (roi_x, roi_y, roi_width, roi_height)

LOWER_YELLOW = np.array([22, 120, 200])
UPPER_YELLOW = np.array([28, 255, 255])
template = cv2.imread(resource_path("exclamation_mark.png"), cv2.IMREAD_UNCHANGED)
template_bgr = template[:, :, :3]
template_alpha = template[:, :, 3]

def find_yellow_blob(img_bgr):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) < 50: return None
    M = cv2.moments(largest_contour)
    if M["m00"] == 0: return None
    return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])

def verify_with_opencv(img_bgr, center_point, threshold=0.5):
    verify_roi_w, verify_roi_h = 100, 200
    vx = max(0, center_point[0] - verify_roi_w // 2)
    vy = max(0, center_point[1] - verify_roi_h // 2)
    img_roi = img_bgr[vy:vy+verify_roi_h, vx:vx+verify_roi_w]
    if img_roi.shape[0] < 1 or img_roi.shape[1] < 1: return False
    res = cv2.matchTemplate(img_roi, template_bgr, cv2.TM_CCOEFF_NORMED, mask=template_alpha)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= threshold

# --- 核心记录逻辑 ---
def bite_check():
    cprint(f"等待鱼咬钩...", C_STATUS)
    timeout = 40
    start_time = time.time()
    check_interval = 0.1
    
    while is_running:
        elapsed = 0
        while elapsed < check_interval and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running: break
            
        try:
            screenshot = pyautogui.screenshot(region=roi_search_area)
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            cprint(f"截图失败: {e}", C_WARN)
            continue
            
        blob_center = find_yellow_blob(img_bgr)
        if blob_center and verify_with_opencv(img_bgr, blob_center, threshold=0.5):
            cprint("检测到叹号!", C_SUCCESS)
            return True

        if time.time() - start_time >= timeout:
            cprint("咬钩检测超时", C_WARN)
            return False
            
    cprint("咬钩检测被中断", C_CONTROL)
    return False

def wait_for_reel_end_and_log():
    cprint("检测到叹号后等待2秒...", C_STATUS)
    time.sleep(2)

    cprint("开始检测压力表盘是否消失...", C_STATUS)
    base_color_orange = (255, 195, 83)
    start_time = time.time()
    timeout = 30

    while is_running:
        if time.time() - start_time > timeout:
            cprint("检测压力表盘超时 (30秒)，判定为空军", C_WARN)
            record_fishing_result('airforce')
            return

        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
        except Exception as e:
            cprint(f"读取像素失败: {e}", C_WARN)
            time.sleep(0.1)
            continue

        if color_changed(base_color_orange, color_exist, tolerance=100):
            cprint("检测到压力表盘消失，开始检测稀有度...", C_SUCCESS)
            
            # 等待0.4秒让UI稳定
            time.sleep(0.4)

            center_x = window_left + window_width // 2
            if window_width == 1920 and window_height == 1080:
                region = (window_top + 160, window_left + 875, window_top + 200, window_left + 960)
            elif window_width == 3840 and window_height == 2160:
                region = (window_top + 230, center_x - 130, window_top + 320, center_x + 20)
            else:
                region = (window_top + 190, center_x - 130, window_top + 250, center_x + 20)
            
            rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
            
            if rarity != 'airforce':
                cprint(f"钓鱼成功！稀有度: {rarity}", C_SUCCESS)
            else:
                cprint("判定为空军", C_WARN)

            record_fishing_result(rarity)
            update_counts(rarity)
            return
        
        time.sleep(0.1)

def update_counts(rarity):
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, unknown_count, airforce_count
    if rarity == 'legendary': legendary_count += 1
    elif rarity == 'epic': epic_count += 1
    elif rarity == 'rare': rare_count += 1
    elif rarity == 'extraordinary': extraordinary_count += 1
    elif rarity == 'standard': standard_count += 1
    elif rarity == 'unknown': unknown_count += 1
    elif rarity == 'airforce': airforce_count += 1

def main_loop():
    display_statistics()
    if not STATISTICS_ENABLED:
        cprint("注意: 当前未启用统计功能，钓鱼数据将不会被保存", C_WARN)
        cprint("按 Ctrl+K 可以启用统计功能", C_INFO)

    cprint("\n" + "="*20 + " 开始新一轮记录 " + "="*20, C_INFO)
    
    if bite_check():
        wait_for_reel_end_and_log()
    else:
        cprint("本轮未检测到咬钩或被中断", C_WARN)

    total_fish = legendary_count + epic_count + rare_count + extraordinary_count + standard_count + unknown_count
    total_attempts = total_fish + airforce_count
    airforce_rate = (airforce_count / total_attempts * 100) if total_attempts > 0 else 0
    
    cprint("本次运行统计: ", C_DEBUG, end='')
    if total_fish > 0:
        rates = {r: (globals()[f"{r}_count"] / total_fish * 100) for r in rarity_fg_colors.keys()}
        cprint(f"传奇{legendary_count}条({rates['legendary']:.1f}%)", rarity_fg_colors['legendary'], end=', ')
        cprint(f"史诗{epic_count}条({rates['epic']:.1f}%)", rarity_fg_colors['epic'], end=', ')
        cprint(f"稀有{rare_count}条({rates['rare']:.1f}%)", rarity_fg_colors['rare'], end=', ')
        cprint(f"非凡{extraordinary_count}条({rates['extraordinary']:.1f}%)", rarity_fg_colors['extraordinary'], end=', ')
        cprint(f"标准{standard_count}条({rates['standard']:.1f}%)", rarity_fg_colors['standard'], end=', ')
        cprint(f"未知{unknown_count}条({rates['unknown']:.1f}%)", C_GRAY, end=", ")
    else:
        cprint(f"传奇{legendary_count}条", rarity_fg_colors['legendary'], end=', ')
        cprint(f"史诗{epic_count}条", rarity_fg_colors['epic'], end=', ')
        cprint(f"稀有{rare_count}条", rarity_fg_colors['rare'], end=', ')
        cprint(f"非凡{extraordinary_count}条", rarity_fg_colors['extraordinary'], end=', ')
        cprint(f"标准{standard_count}条", rarity_fg_colors['standard'], end=', ')
        cprint(f"未知{unknown_count}条", C_GRAY, end=', ')
    cprint(f"空军{airforce_count}次({airforce_rate:.1f}%)", C_GRAY)
    
    cprint("="*20 + " 本轮记录结束 " + "="*20, C_INFO)
    time.sleep(2)

# --- 主程序入口 ---
if __name__ == "__main__":
    cprint("="*50, C_INFO)
    cprint("猛兽派对 - 钓鱼记录脚本 (无操作)", C_INFO)
    cprint("作者: Fox, 由SammFang改版", C_INFO)
    cprint("="*50, C_INFO)
    cprint("\n请将游戏窗口置于前台，脚本开始后不要移动窗口。", C_WARN)
    cprint(f"按 Ctrl+L 可以暂停或恢复脚本。", C_WARN)
    cprint(f"按 Ctrl+K 可以{'创建统计文件并' if not STATISTICS_ENABLED else ''}切换统计功能。", C_INFO)
    cprint(f"按 Ctrl+K+Enter 可以归档当前统计文件并创建新的统计文件。", C_INFO)
    cprint(f"按 'q' 可以紧急终止脚本。", C_WARN)
    
    for i in range(3, 0, -1):
        cprint(f"{i} 秒后开始...", C_INFO)
        time.sleep(1)

    try:
        while True:
            if not is_running:
                cprint("程序已停止，等待恢复...", C_CONTROL)
                while not is_running:
                    time.sleep(0.5)
                cprint("程序恢复，开始新一轮", C_CONTROL)
            
            main_loop()
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        cprint("\n检测到 Ctrl+C，程序退出。", C_CONTROL)
    except Exception as e:
        cprint(f"\n发生未处理的异常: {e}", C_ERROR)
    finally:
        cprint("脚本已停止。", C_INFO)