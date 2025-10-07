# windows_sendinput_auto_fish.py
# Windows-only: 使用 SendInput 注入鼠标事件

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

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from collections import deque



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

try:
    import win32gui
    import win32con
except ImportError:
    print("错误: 缺少 pywin32 库，请运行: pip install pywin32")
    raise

# --- 统计文件路径 ---
STATISTICS_FILE = "statistics-content.json"

# 全局变量
is_running = True  # 控制主循环是否运行
statistics_only_mode = False  # 仅统计模式标志
afk_mode = False  # 挂机防踢模式标志
legendary_count = 0
epic_count = 0
rare_count = 0
extraordinary_count = 0
standard_count = 0
unknown_count = 0
airforce_count = 0

# 检查统计文件是否存在，如果不存在则禁用统计功能
STATISTICS_ENABLED = os.path.exists(STATISTICS_FILE)

# 稀有度颜色映射
RARITY_COLORS = {
    'legendary': '#FFC935',      # 传奇鱼 - 金黄色
    'epic': '#AB63FF',           # 史诗鱼 - 紫色
    'rare': '#66A6FF',            # 稀有鱼 - 蓝色
    'extraordinary': '#8EC955',  # 非凡鱼 - 绿色
    'standard': '#B7BAC1',       # 标准鱼 - 灰色
    'unknown': '#FFFFFF',        # 未知鱼 - 白色
    'airforce': '#FFFFFF'        # 空军 - 白色
}

# GUI类
class FishingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("自动钓鱼工具better_fisher(GUI)")
        self.root.geometry("1200x700")
        self.root.configure(bg='#2b2b2b')
        
        # 设置窗口图标和样式
        self.setup_styles()
        
        # 创建主框架
        self.create_main_layout()
        
        # 初始化日志队列
        self.log_queue = deque(maxlen=100)
        
        # 启动日志更新线程
        self.update_log_display()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_styles(self):
        """设置现代UI样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', background='#2b2b2b', foreground='#FFFFFF', font=('Microsoft YaHei', 16, 'bold'))
        style.configure('Heading.TLabel', background='#2b2b2b', foreground='#CCCCCC', font=('Microsoft YaHei', 12, 'bold'))
        style.configure('Info.TLabel', background='#2b2b2b', foreground='#AAAAAA', font=('Microsoft YaHei', 10))
        style.configure('Status.TLabel', background='#2b2b2b', foreground='#00FF00', font=('Microsoft YaHei', 10))
        style.configure('Warning.TLabel', background='#2b2b2b', foreground='#FFAA00', font=('Microsoft YaHei', 10))
        style.configure('Error.TLabel', background='#2b2b2b', foreground='#FF5555', font=('Microsoft YaHei', 10))
        
        # 配置按钮样式
        style.configure('Primary.TButton', font=('Microsoft YaHei', 10, 'bold'))
        style.configure('Success.TButton', font=('Microsoft YaHei', 10, 'bold'))
        style.configure('Danger.TButton', font=('Microsoft YaHei', 10, 'bold'))
        
        # 配置框架样式
        style.configure('Card.TFrame', background='#3c3c3c', relief='raised', borderwidth=1)
        
    def create_main_layout(self):
        """创建主布局"""
        # 创建主容器（去掉顶部标题栏）
        main_container = tk.Frame(self.root, bg='#2b2b2b')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板 - 统计信息
        left_panel = tk.Frame(main_container, bg='#2b2b2b', width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        self.create_statistics_panel(left_panel)
        
        # 中间面板 - 状态和控制
        middle_panel = tk.Frame(main_container, bg='#2b2b2b', width=300)
        middle_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        middle_panel.pack_propagate(False)
        
        self.create_status_panel(middle_panel)
        
        # 右侧面板 - 日志信息
        right_panel = tk.Frame(main_container, bg='#2b2b2b')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.create_log_panel(right_panel)
        
    def create_statistics_panel(self, parent):
        """创建统计信息面板"""
        # 统计卡片框架
        stats_card = tk.Frame(parent, bg='#3c3c3c', relief='raised', bd=1)
        stats_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题
        title_label = ttk.Label(stats_card, text="📊 钓鱼统计", style='Heading.TLabel')
        title_label.pack(pady=(10, 5))
        
        # 统计功能状态
        self.stats_status_label = ttk.Label(stats_card, text="", style='Info.TLabel')
        self.stats_status_label.pack(pady=5)
        self.update_stats_status()
        
        # 分隔线
        separator1 = tk.Frame(stats_card, bg='#555555', height=1)
        separator1.pack(fill=tk.X, padx=10, pady=5)
        
        # 当前运行统计 - 精简版
        current_frame = tk.Frame(stats_card, bg='#3c3c3c')
        current_frame.pack(fill=tk.X, padx=10, pady=2)
        
        ttk.Label(current_frame, text="当前运行", style='Heading.TLabel').pack(anchor=tk.W)
        
        self.current_stats_frame = tk.Frame(current_frame, bg='#3c3c3c')
        self.current_stats_frame.pack(fill=tk.X, pady=2)
        
        # 创建精简统计标签
        self.create_compact_stat_labels(self.current_stats_frame, "current")
        
        # 分隔线
        separator2 = tk.Frame(stats_card, bg='#555555', height=1)
        separator2.pack(fill=tk.X, padx=10, pady=5)
        
        # 历史统计 - 包含本次和历史总和
        history_frame = tk.Frame(stats_card, bg='#3c3c3c')
        history_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(history_frame, text="历史统计", style='Heading.TLabel').pack(anchor=tk.W)
        
        # 创建两栏显示的框架
        self.history_stats_frame = tk.Frame(history_frame, bg='#3c3c3c')
        self.history_stats_frame.pack(fill=tk.X, pady=2)
        
        # 创建两栏统计标签
        self.create_dual_column_stat_labels(self.history_stats_frame)
        
        # 刷新统计按钮
        refresh_btn = ttk.Button(stats_card, text="刷新统计", command=self.refresh_statistics)
        refresh_btn.pack(pady=10)
        
    def create_compact_stat_labels(self, parent, stat_type):
        """创建精简统计标签"""
        # 稀有度标签 - 显示所有鱼类
        rarities = [
            ('legendary', '传奇'),
            ('epic', '史诗'),
            ('rare', '稀有'),
            ('extraordinary', '非凡'),
            ('standard', '标准'),
            ('airforce', '空军')
        ]
        
        # 创建一行显示的框架
        row_frame = tk.Frame(parent, bg='#3c3c3c')
        row_frame.pack(fill=tk.X, pady=1)
        
        # 所有鱼类在一行显示
        for i, (rarity, zh_name) in enumerate(rarities):
            # 创建彩色圆点作为图例
            dot_frame = tk.Frame(row_frame, bg='#3c3c3c')
            dot_frame.pack(side=tk.LEFT, padx=1)
            
            # 创建彩色圆点
            dot = tk.Label(dot_frame, text="●", bg='#3c3c3c', fg=RARITY_COLORS[rarity], font=('Microsoft YaHei', 9))
            dot.pack(side=tk.LEFT)
            
            # 创建数值标签
            label_value = tk.Label(dot_frame, text="0", bg='#3c3c3c', fg=RARITY_COLORS[rarity], font=('Microsoft YaHei', 7, 'bold'))
            setattr(self, f"current_{rarity}_label", label_value)
            label_value.pack(side=tk.LEFT, padx=(0, 4))
    
    def create_dual_column_stat_labels(self, parent):
        """创建双列统计标签 - 本次和历史总和"""
        # 稀有度标签
        rarities = [
            ('legendary', '传奇鱼'),
            ('epic', '史诗鱼'),
            ('rare', '稀有鱼'),
            ('extraordinary', '非凡鱼'),
            ('standard', '标准鱼'),
            ('unknown', '未知鱼'),
            ('airforce', '空军')
        ]
        
        # 创建标题行
        title_frame = tk.Frame(parent, bg='#3c3c3c')
        title_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(title_frame, text="类型", style='Info.TLabel', width=8).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="本次", style='Info.TLabel', width=12).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="总和", style='Info.TLabel', width=12).pack(side=tk.LEFT)
        
        # 创建分隔线
        separator = tk.Frame(parent, bg='#555555', height=1)
        separator.pack(fill=tk.X, pady=2)
        
        # 为每种稀有度创建行
        for rarity, zh_name in rarities:
            row_frame = tk.Frame(parent, bg='#3c3c3c')
            row_frame.pack(fill=tk.X, pady=1)
            
            # 类型标签
            label_name = tk.Label(row_frame, text=f"{zh_name}:", bg='#3c3c3c', fg=RARITY_COLORS[rarity], font=('Microsoft YaHei', 9, 'bold'), width=8)
            label_name.pack(side=tk.LEFT)
            
            # 本次统计标签
            current_label = tk.Label(row_frame, text="0条 (0.0%)", bg='#3c3c3c', fg='#CCCCCC', font=('Microsoft YaHei', 8), width=12)
            setattr(self, f"current_display_{rarity}_label", current_label)
            current_label.pack(side=tk.LEFT)
            
            # 总和统计标签
            total_label = tk.Label(row_frame, text="0条 (0.0%)", bg='#3c3c3c', fg='#CCCCCC', font=('Microsoft YaHei', 8), width=12)
            setattr(self, f"total_{rarity}_label", total_label)
            total_label.pack(side=tk.LEFT)
        
        # 创建样本量行
        sample_frame = tk.Frame(parent, bg='#3c3c3c')
        sample_frame.pack(fill=tk.X, pady=2)
        
        # 创建样本量分隔线
        sample_separator = tk.Frame(parent, bg='#555555', height=1)
        sample_separator.pack(fill=tk.X, pady=2)
        
        # 样本量标签
        sample_row = tk.Frame(parent, bg='#3c3c3c')
        sample_row.pack(fill=tk.X, pady=1)
        
        label_name = tk.Label(sample_row, text="样本量:", bg='#3c3c3c', fg='#AAAAAA', font=('Microsoft YaHei', 9, 'bold'), width=8)
        label_name.pack(side=tk.LEFT)
        
        # 本次样本量标签
        self.current_sample_label = tk.Label(sample_row, text="0次", bg='#3c3c3c', fg='#CCCCCC', font=('Microsoft YaHei', 8), width=12)
        self.current_sample_label.pack(side=tk.LEFT)
        
        # 总和样本量标签
        self.total_sample_label = tk.Label(sample_row, text="0次", bg='#3c3c3c', fg='#CCCCCC', font=('Microsoft YaHei', 8), width=12)
        self.total_sample_label.pack(side=tk.LEFT)
            
    def create_status_panel(self, parent):
        """创建状态控制面板"""
        # 状态卡片框架
        status_card = tk.Frame(parent, bg='#3c3c3c', relief='raised', bd=1)
        status_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题
        title_label = ttk.Label(status_card, text="⚙️ 状态与控制", style='Heading.TLabel')
        title_label.pack(pady=(10, 5))
        
        # 分隔线
        separator1 = tk.Frame(status_card, bg='#555555', height=1)
        separator1.pack(fill=tk.X, padx=10, pady=5)
        
        # 运行状态
        status_frame = tk.Frame(status_card, bg='#3c3c3c')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="运行状态:", style='Info.TLabel').pack(anchor=tk.W)
        
        # 状态标签容器
        status_container = tk.Frame(status_frame, bg='#3c3c3c')
        status_container.pack(anchor=tk.W, pady=5)
        
        self.status_label = tk.Label(status_container, text="● 就绪", bg='#3c3c3c', fg='#00FF00', font=('Microsoft YaHei', 12, 'bold'))
        self.status_label.pack(side=tk.LEFT)
        
        # 模式指示器
        self.mode_indicator = tk.Label(status_container, text="", bg='#3c3c3c', fg='#AAAAAA', font=('Microsoft YaHei', 9))
        self.mode_indicator.pack(side=tk.LEFT, padx=(5, 0))
        self.update_mode_indicator()
        
        # 分隔线
        separator2 = tk.Frame(status_card, bg='#555555', height=1)
        separator2.pack(fill=tk.X, padx=10, pady=5)
        
        # 控制按钮
        control_frame = tk.Frame(status_card, bg='#3c3c3c')
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="▶ 开始钓鱼", command=self.start_fishing, state=tk.DISABLED)
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ttk.Button(control_frame, text="⏸ 暂停钓鱼", command=self.stop_fishing, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        # 分隔线
        separator3 = tk.Frame(status_card, bg='#555555', height=1)
        separator3.pack(fill=tk.X, padx=10, pady=5)
        
        # 统计功能控制
        stats_control_frame = tk.Frame(status_card, bg='#3c3c3c')
        stats_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(stats_control_frame, text="统计功能:", style='Info.TLabel').pack(anchor=tk.W)
        
        # 按钮并排放置的容器
        buttons_container = tk.Frame(stats_control_frame, bg='#3c3c3c')
        buttons_container.pack(fill=tk.X, pady=2)
        
        # 左侧按钮
        left_buttons = tk.Frame(buttons_container, bg='#3c3c3c')
        left_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.toggle_stats_btn = ttk.Button(left_buttons, text="切换统计功能", command=self.toggle_statistics)
        self.toggle_stats_btn.pack(fill=tk.X, pady=(2, 2))
        
        # 右侧按钮
        right_buttons = tk.Frame(buttons_container, bg='#3c3c3c')
        right_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        self.archive_stats_btn = ttk.Button(right_buttons, text="归档统计数据", command=self.archive_statistics)
        self.archive_stats_btn.pack(fill=tk.X, pady=(2, 2))
        
        # 切换仅统计模式按钮
        self.toggle_mode_btn = ttk.Button(stats_control_frame, text="切换仅统计模式", command=self.toggle_statistics_mode)
        self.toggle_mode_btn.pack(fill=tk.X, pady=2)
        
        # 分隔线
        separator4 = tk.Frame(status_card, bg='#555555', height=1)
        separator4.pack(fill=tk.X, padx=10, pady=5)
        
        # 快捷键说明
        shortcut_frame = tk.Frame(status_card, bg='#3c3c3c')
        shortcut_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(shortcut_frame, text="快捷键:", style='Info.TLabel').pack(anchor=tk.W)
        
        shortcuts = [
            "Ctrl+L: 暂停/恢复/停止挂机",
            "Ctrl+K: 切换统计",
            "Ctrl+K+Enter: 归档",
            "Ctrl+M: 切换仅统计",
            "Q: 紧急停止"
        ]
        
        for shortcut in shortcuts:
            label = tk.Label(shortcut_frame, text=f"  • {shortcut}", bg='#3c3c3c', fg='#AAAAAA', font=('Microsoft YaHei', 8))
            label.pack(anchor=tk.W)
            
    def create_log_panel(self, parent):
        """创建日志面板"""
        # 日志卡片框架
        log_card = tk.Frame(parent, bg='#3c3c3c', relief='raised', bd=1)
        log_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题
        title_frame = tk.Frame(log_card, bg='#3c3c3c')
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(title_frame, text="📝 运行日志", style='Heading.TLabel').pack(side=tk.LEFT)
        
        clear_btn = ttk.Button(title_frame, text="清空日志", command=self.clear_log)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(
            log_card,
            wrap=tk.WORD,
            width=50,
            height=20,
            bg='#1e1e1e',
            fg='#CCCCCC',
            font=('Consolas', 9),
            insertbackground='#CCCCCC'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 配置文本标签颜色
        self.log_text.tag_config('INFO', foreground='#00AAFF')
        self.log_text.tag_config('SUCCESS', foreground='#00FF00')
        self.log_text.tag_config('WARNING', foreground='#FFAA00')
        self.log_text.tag_config('ERROR', foreground='#FF5555')
        self.log_text.tag_config('STATUS', foreground='#FFFF00')
        self.log_text.tag_config('DEBUG', foreground='#CCCCCC')
        
        # 挂机防踢功能板块
        afk_frame = tk.Frame(log_card, bg='#3c3c3c')
        afk_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 分隔线
        separator = tk.Frame(afk_frame, bg='#555555', height=1)
        separator.pack(fill=tk.X, pady=(0, 5))
        
        # 挂机防踢按钮
        self.afk_btn = ttk.Button(afk_frame, text="挂机防踢", command=self.toggle_afk_mode)
        self.afk_btn.pack(fill=tk.X, pady=2)
        
    def update_stats_status(self):
        """更新统计功能状态"""
        if STATISTICS_ENABLED:
            self.stats_status_label.config(text="✅ 统计功能已启用")
        else:
            self.stats_status_label.config(text="❌ 统计功能已禁用")
            
    def update_mode_indicator(self):
        """更新模式指示器"""
        global statistics_only_mode, afk_mode
        if afk_mode:
            self.mode_indicator.config(text="（挂机）")
        elif statistics_only_mode:
            self.mode_indicator.config(text="（仅统计）")
        else:
            self.mode_indicator.config(text="（托管）")
            
    def add_log(self, message, log_type='INFO'):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # 添加到队列
        self.log_queue.append((log_entry, log_type))
        
    def update_log_display(self):
        """更新日志显示"""
        try:
            while self.log_queue:
                log_entry, log_type = self.log_queue.popleft()
                
                self.log_text.insert(tk.END, log_entry + '\n', log_type)
                self.log_text.see(tk.END)
                
                # 限制日志行数
                lines = int(self.log_text.index('end-1c').split('.')[0])
                if lines > 1000:
                    self.log_text.delete('1.0', '100.0')
        except:
            pass
            
        # 定期更新
        self.root.after(100, self.update_log_display)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete('1.0', tk.END)
        
    def update_current_statistics(self):
        """更新当前运行统计"""
        total_fish = legendary_count + epic_count + rare_count + extraordinary_count + standard_count + unknown_count
        total_attempts = total_fish + airforce_count
        
        # 更新精简当前统计
        self.current_legendary_label.config(text=f"{legendary_count}")
        self.current_epic_label.config(text=f"{epic_count}")
        self.current_rare_label.config(text=f"{rare_count}")
        self.current_extraordinary_label.config(text=f"{extraordinary_count}")
        self.current_standard_label.config(text=f"{standard_count}")
        self.current_airforce_label.config(text=f"{airforce_count}")
        
        # 更新双列显示中的本次统计
        if total_fish > 0:
            legendary_rate = (legendary_count / total_fish * 100) if total_fish > 0 else 0
            epic_rate = (epic_count / total_fish * 100) if total_fish > 0 else 0
            rare_rate = (rare_count / total_fish * 100) if total_fish > 0 else 0
            extraordinary_rate = (extraordinary_count / total_fish * 100) if total_fish > 0 else 0
            standard_rate = (standard_count / total_fish * 100) if total_fish > 0 else 0
            unknown_rate = (unknown_count / total_fish * 100) if total_fish > 0 else 0
            
            self.current_display_legendary_label.config(text=f"{legendary_count}条 ({legendary_rate:.1f}%)")
            self.current_display_epic_label.config(text=f"{epic_count}条 ({epic_rate:.1f}%)")
            self.current_display_rare_label.config(text=f"{rare_count}条 ({rare_rate:.1f}%)")
            self.current_display_extraordinary_label.config(text=f"{extraordinary_count}条 ({extraordinary_rate:.1f}%)")
            self.current_display_standard_label.config(text=f"{standard_count}条 ({standard_rate:.1f}%)")
            self.current_display_unknown_label.config(text=f"{unknown_count}条 ({unknown_rate:.1f}%)")
        else:
            self.current_display_legendary_label.config(text=f"{legendary_count}条 (0.0%)")
            self.current_display_epic_label.config(text=f"{epic_count}条 (0.0%)")
            self.current_display_rare_label.config(text=f"{rare_count}条 (0.0%)")
            self.current_display_extraordinary_label.config(text=f"{extraordinary_count}条 (0.0%)")
            self.current_display_standard_label.config(text=f"{standard_count}条 (0.0%)")
            self.current_display_unknown_label.config(text=f"{unknown_count}条 (0.0%)")
            
        airforce_rate = (airforce_count / total_attempts * 100) if total_attempts > 0 else 0
        self.current_display_airforce_label.config(text=f"{airforce_count}次 ({airforce_rate:.1f}%)")
        
        # 更新总和统计
        self.update_total_statistics()
        
    def load_all_statistics(self):
        """加载当前统计文件和所有归档文件的统计数据"""
        all_records = []
        
        # 加载当前统计文件
        current_stats = load_statistics()
        all_records.extend(current_stats.get("records", []))
        
        # 加载所有归档文件
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
                            self.add_log(f"加载归档文件 {filename} 失败: {e}", 'WARNING')
            except Exception as e:
                self.add_log(f"读取归档目录失败: {e}", 'WARNING')
        
        return {"records": all_records}

    def update_total_statistics(self):
        """更新本次统计和历史总和统计"""
        if not STATISTICS_ENABLED:
            return
            
        # 加载当前统计数据
        current_stats = load_statistics()
        current_records = current_stats.get("records", [])
        
        # 统计当前文件各稀有度数量
        current_counts = {
            'legendary': 0,
            'epic': 0,
            'rare': 0,
            'extraordinary': 0,
            'standard': 0,
            'unknown': 0,
            'airforce': 0
        }
        
        for record in current_records:
            rarity = record.get('rarity', 'airforce')
            if rarity in current_counts:
                current_counts[rarity] += 1
        
        current_fish = (current_counts['legendary'] + current_counts['epic'] +
                       current_counts['rare'] + current_counts['extraordinary'] +
                       current_counts['standard'] + current_counts['unknown'])
        current_attempts = current_fish + current_counts['airforce']
        
        # 更新本次统计显示
        if current_fish > 0:
            legendary_rate = (current_counts['legendary'] / current_fish * 100) if current_fish > 0 else 0
            epic_rate = (current_counts['epic'] / current_fish * 100) if current_fish > 0 else 0
            rare_rate = (current_counts['rare'] / current_fish * 100) if current_fish > 0 else 0
            extraordinary_rate = (current_counts['extraordinary'] / current_fish * 100) if current_fish > 0 else 0
            standard_rate = (current_counts['standard'] / current_fish * 100) if current_fish > 0 else 0
            unknown_rate = (current_counts['unknown'] / current_fish * 100) if current_fish > 0 else 0
            
            self.current_display_legendary_label.config(text=f"{current_counts['legendary']}条 ({legendary_rate:.1f}%)")
            self.current_display_epic_label.config(text=f"{current_counts['epic']}条 ({epic_rate:.1f}%)")
            self.current_display_rare_label.config(text=f"{current_counts['rare']}条 ({rare_rate:.1f}%)")
            self.current_display_extraordinary_label.config(text=f"{current_counts['extraordinary']}条 ({extraordinary_rate:.1f}%)")
            self.current_display_standard_label.config(text=f"{current_counts['standard']}条 ({standard_rate:.1f}%)")
            self.current_display_unknown_label.config(text=f"{current_counts['unknown']}条 ({unknown_rate:.1f}%)")
        else:
            self.current_display_legendary_label.config(text=f"{current_counts['legendary']}条 (0.0%)")
            self.current_display_epic_label.config(text=f"{current_counts['epic']}条 (0.0%)")
            self.current_display_rare_label.config(text=f"{current_counts['rare']}条 (0.0%)")
            self.current_display_extraordinary_label.config(text=f"{current_counts['extraordinary']}条 (0.0%)")
            self.current_display_standard_label.config(text=f"{current_counts['standard']}条 (0.0%)")
            self.current_display_unknown_label.config(text=f"{current_counts['unknown']}条 (0.0%)")
            
        current_airforce_rate = (current_counts['airforce'] / current_attempts * 100) if current_attempts > 0 else 0
        self.current_display_airforce_label.config(text=f"{current_counts['airforce']}次 ({current_airforce_rate:.1f}%)")
        
        # 更新本次样本量
        self.current_sample_label.config(text=f"{current_attempts}杆")
        
        # 加载所有统计数据（当前+归档）
        all_stats = self.load_all_statistics()
        all_records = all_stats.get("records", [])
        
        # 统计所有文件各稀有度数量
        total_counts = {
            'legendary': 0,
            'epic': 0,
            'rare': 0,
            'extraordinary': 0,
            'standard': 0,
            'unknown': 0,
            'airforce': 0
        }
        
        for record in all_records:
            rarity = record.get('rarity', 'airforce')
            if rarity in total_counts:
                total_counts[rarity] += 1
        
        total_fish = (total_counts['legendary'] + total_counts['epic'] +
                     total_counts['rare'] + total_counts['extraordinary'] +
                     total_counts['standard'] + total_counts['unknown'])
        total_attempts = total_fish + total_counts['airforce']
        
        # 更新总和统计显示
        if total_fish > 0:
            legendary_rate = (total_counts['legendary'] / total_fish * 100) if total_fish > 0 else 0
            epic_rate = (total_counts['epic'] / total_fish * 100) if total_fish > 0 else 0
            rare_rate = (total_counts['rare'] / total_fish * 100) if total_fish > 0 else 0
            extraordinary_rate = (total_counts['extraordinary'] / total_fish * 100) if total_fish > 0 else 0
            standard_rate = (total_counts['standard'] / total_fish * 100) if total_fish > 0 else 0
            unknown_rate = (total_counts['unknown'] / total_fish * 100) if total_fish > 0 else 0
            
            self.total_legendary_label.config(text=f"{total_counts['legendary']}条 ({legendary_rate:.1f}%)")
            self.total_epic_label.config(text=f"{total_counts['epic']}条 ({epic_rate:.1f}%)")
            self.total_rare_label.config(text=f"{total_counts['rare']}条 ({rare_rate:.1f}%)")
            self.total_extraordinary_label.config(text=f"{total_counts['extraordinary']}条 ({extraordinary_rate:.1f}%)")
            self.total_standard_label.config(text=f"{total_counts['standard']}条 ({standard_rate:.1f}%)")
            self.total_unknown_label.config(text=f"{total_counts['unknown']}条 ({unknown_rate:.1f}%)")
        else:
            self.total_legendary_label.config(text=f"{total_counts['legendary']}条 (0.0%)")
            self.total_epic_label.config(text=f"{total_counts['epic']}条 (0.0%)")
            self.total_rare_label.config(text=f"{total_counts['rare']}条 (0.0%)")
            self.total_extraordinary_label.config(text=f"{total_counts['extraordinary']}条 (0.0%)")
            self.total_standard_label.config(text=f"{total_counts['standard']}条 (0.0%)")
            self.total_unknown_label.config(text=f"{total_counts['unknown']}条 (0.0%)")
            
        total_airforce_rate = (total_counts['airforce'] / total_attempts * 100) if total_attempts > 0 else 0
        self.total_airforce_label.config(text=f"{total_counts['airforce']}次 ({total_airforce_rate:.1f}%)")
        
        # 更新总和样本量
        self.total_sample_label.config(text=f"{total_attempts}杆")

    def refresh_statistics(self):
        """刷新统计信息"""
        if not STATISTICS_ENABLED:
            messagebox.showwarning("警告", "统计功能未启用")
            return
        
        # 更新当前统计和总和统计
        self.update_current_statistics()
        
        self.add_log("统计信息已刷新", 'SUCCESS')
        
    def start_fishing(self):
        """开始钓鱼"""
        global is_running, hwnd

        # 自动聚焦到游戏窗口
        try:
            self.add_log("正在聚焦到 '猛兽派对' 游戏窗口...", 'INFO')
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5) # 等待窗口激活
        except Exception as e:
            self.add_log(f"自动聚焦窗口失败: {e}", 'WARNING')
            self.add_log("请手动点击游戏窗口以确保脚本正常工作。", 'WARNING')

        is_running = True
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="● 运行中", fg='#00FF00')
        
        self.add_log("开始自动钓鱼", 'STATUS')
        
        # 在新线程中运行钓鱼逻辑
        fishing_thread = threading.Thread(target=self.fishing_loop, daemon=True)
        fishing_thread.start()
        
    def stop_fishing(self):
        """停止钓鱼"""
        global is_running
        is_running = False
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="● 已暂停", fg='#FFAA00')
        
        self.add_log("钓鱼已暂停", 'WARNING')
        
    def fishing_loop(self):
        """钓鱼循环"""
        global is_running, statistics_only_mode
        
        while is_running:
            try:
                # 根据模式执行不同的钓鱼逻辑
                if statistics_only_mode:
                    # 仅统计模式：不执行游戏操作，只进行检测和记录
                    auto_fish_logger_once()
                else:
                    # 自动钓鱼模式：执行完整的钓鱼流程
                    auto_fish_once()
                
                # 更新统计显示
                self.root.after(0, self.update_current_statistics)
                
                # 短暂休息
                time.sleep(0.5)
                
            except Exception as e:
                self.add_log(f"钓鱼过程中发生错误: {e}", 'ERROR')
                time.sleep(1)
                
    def toggle_statistics(self):
        """切换统计功能"""
        global STATISTICS_ENABLED
        
        # 如果统计文件不存在，创建它
        if not os.path.exists(STATISTICS_FILE):
            try:
                # 创建初始统计文件
                initial_data = {"records": []}
                with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=2)
                
                # 更新统计功能状态
                STATISTICS_ENABLED = True
                self.add_log(f"已成功创建统计文件 {STATISTICS_FILE}，统计功能已启用", 'SUCCESS')
                self.update_stats_status()
            except Exception as e:
                self.add_log(f"创建统计文件失败: {e}", 'ERROR')
        else:
            # 如果文件存在，切换统计功能状态
            STATISTICS_ENABLED = not STATISTICS_ENABLED
            status = '启用' if STATISTICS_ENABLED else '禁用'
            self.add_log(f"统计功能已{status}", 'SUCCESS')
            self.update_stats_status()
            
    def toggle_statistics_mode(self):
        """切换仅统计模式"""
        global statistics_only_mode
        statistics_only_mode = not statistics_only_mode
        
        if statistics_only_mode:
            self.add_log("已切换到仅统计模式（不执行游戏操作）", 'SUCCESS')
            self.toggle_mode_btn.config(text="切换到自动钓鱼模式")
        else:
            self.add_log("已切换到自动钓鱼模式（托管）", 'SUCCESS')
            self.toggle_mode_btn.config(text="切换仅统计模式")
            
        self.update_mode_indicator()
            
    def archive_statistics(self):
        """归档统计数据"""
        if not os.path.exists(STATISTICS_FILE):
            messagebox.showwarning("警告", "统计文件不存在，无法归档")
            return
            
        try:
            # 创建归档目录（如果不存在）
            archive_dir = "archived-data"
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                self.add_log(f"已创建归档目录: {archive_dir}", 'DEBUG')
            
            # 创建归档文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = os.path.join(archive_dir, f"sc-{timestamp}.json")
            
            # 复制当前统计文件为归档文件
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as src:
                data = src.read()
            with open(archive_filename, 'w', encoding='utf-8') as dst:
                dst.write(data)
            
            # 创建新的空统计文件
            initial_data = {"records": []}
            with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
            
            self.add_log(f"统计文件已归档为: {archive_filename}", 'SUCCESS')
            self.add_log("已创建新的统计文件，统计功能继续启用", 'SUCCESS')
            
            # 确保统计功能启用
            global STATISTICS_ENABLED
            STATISTICS_ENABLED = True
            self.update_stats_status()
            
            # 刷新统计显示
            self.refresh_statistics()
            
        except Exception as e:
            self.add_log(f"归档统计文件失败: {e}", 'ERROR')
            
    def toggle_afk_mode(self):
        """切换挂机防踢模式"""
        global afk_mode, is_running
        afk_mode = not afk_mode
        
        if afk_mode:
            # 停止当前运行的钓鱼功能
            if is_running:
                self.stop_fishing()
            
            # 禁用其他功能按钮
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.toggle_stats_btn.config(state=tk.DISABLED)
            self.archive_stats_btn.config(state=tk.DISABLED)
            self.toggle_mode_btn.config(state=tk.DISABLED)
            
            # 更新按钮文本和状态
            self.afk_btn.config(text="停止挂机防踢")
            self.status_label.config(text="● 挂机中", fg='#FFAA00')
            
            # 更新模式指示器
            self.update_mode_indicator()
            
            self.add_log("挂机防踢模式已启动，每30秒(±10秒)随机按键", 'SUCCESS')
            self.add_log("按 Ctrl+L 可停止挂机防踢模式", 'INFO')
            
            # 启动挂机防踢线程
            afk_thread = threading.Thread(target=self.afk_loop, daemon=True)
            afk_thread.start()
        else:
            # 恢复其他功能按钮状态
            if window_initialized:
                self.start_btn.config(state=tk.NORMAL)
            self.toggle_stats_btn.config(state=tk.NORMAL)
            self.archive_stats_btn.config(state=tk.NORMAL)
            self.toggle_mode_btn.config(state=tk.NORMAL)
            
            # 更新按钮文本和状态
            self.afk_btn.config(text="挂机防踢")
            self.status_label.config(text="● 就绪", fg='#00FF00')
            
            # 更新模式指示器
            self.update_mode_indicator()
            
            self.add_log("挂机防踢模式已停止", 'SUCCESS')
    
    def afk_loop(self):
        """挂机防踢循环"""
        global afk_mode
        
        # 启动时先聚焦到游戏窗口
        try:
            win32gui.SetForegroundWindow(hwnd)
            self.root.after(0, lambda: self.add_log("挂机防踢已聚焦到游戏窗口", 'INFO'))
            time.sleep(0.5)
        except Exception as e:
            self.root.after(0, lambda: self.add_log(f"聚焦游戏窗口失败: {e}", 'WARNING'))
        
        while afk_mode:
            # 随机等待时间：30秒 ± 10秒 (20-40秒)
            wait_time = random.uniform(20, 40)
            
            # 使用可中断的等待
            elapsed = 0
            while elapsed < wait_time and afk_mode:
                time.sleep(0.1)
                elapsed += 0.1
                
                # 检查是否按下Ctrl+L
                if USE_KEYBOARD and keyboard.is_pressed('ctrl+l'):
                    self.root.after(0, self.toggle_afk_mode)
                    return
            
            if not afk_mode:
                break
                
            # 随机选择一个按键
            keys = ['tab', 'w', 'a', 's', 'd', 'space']
            random_key = random.choice(keys)
            
            # 随机按键时长：0.2到0.5秒
            press_duration = random.uniform(0.2, 0.5)
            
            try:
                # 按下按键
                keyboard.press(random_key)
                
                # 保持按下状态
                time.sleep(press_duration)
                
                # 释放按键
                keyboard.release(random_key)
                    
                self.root.after(0, lambda k=random_key, d=press_duration: self.add_log(f"挂机防踢: 按下了 {k} 键 ({d:.2f}秒)", 'DEBUG'))
                
            except Exception as e:
                # 确保按键被释放
                try:
                    keyboard.release(random_key)
                except:
                    pass
                self.root.after(0, lambda: self.add_log(f"挂机防踢按键失败: {e}", 'WARNING'))
    
    def on_closing(self):
        """关闭窗口时的处理"""
        global is_running, afk_mode
        is_running = False
        afk_mode = False
        time.sleep(0.5)  # 等待线程结束
        self.root.destroy()

# --- 统计功能 ---
def load_statistics():
    """从JSON文件加载统计数据"""
    if not os.path.exists(STATISTICS_FILE):
        return {"records": []}
    
    try:
        with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        if hasattr(gui, 'add_log'):
            gui.add_log(f"加载统计文件失败: {e}", 'ERROR')
        else:
            print(f"加载统计文件失败: {e}")
        return {"records": []}

def save_statistics(data):
    """保存统计数据到JSON文件"""
    try:
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        if hasattr(gui, 'add_log'):
            gui.add_log(f"保存统计文件失败: {e}", 'ERROR')
        else:
            print(f"保存统计文件失败: {e}")

def record_fishing_result(rarity):
    """记录单次钓鱼结果"""
    # 检查统计功能是否启用
    if not STATISTICS_ENABLED:
        if hasattr(gui, 'add_log'):
            gui.add_log("统计功能已禁用，跳过记录", 'DEBUG')
        return
        
    stats = load_statistics()
    
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rarity": rarity,
        "is_airforce": rarity == 'airforce'
    }
    
    stats["records"].append(record)
    save_statistics(stats)
    if hasattr(gui, 'add_log'):
        gui.add_log(f"已记录钓鱼结果到 {STATISTICS_FILE}", 'DEBUG')

# --- 彩色打印函数（适配GUI）---
def cprint(message, color, end='\n'):
    """带颜色的打印函数（适配GUI）"""
    if hasattr(gui, 'add_log'):
        # 映射颜色到日志类型
        color_map = {
            'INFO': 'INFO',
            'STATUS': 'STATUS', 
            'SUCCESS': 'SUCCESS',
            'WARN': 'WARNING',
            'ERROR': 'ERROR',
            'DEBUG': 'DEBUG',
            'CONTROL': 'INFO'
        }
        log_type = color_map.get(color, 'INFO')
        gui.add_log(message, log_type)
    else:
        # 如果GUI还未初始化，使用普通打印
        print(message)

# --- 全局GUI实例 ---
gui = None

# --- 窗口与坐标设置 ---
def initialize_window():
    """初始化窗口设置"""
    global window, hwnd, window_width, window_height, window_left, window_top
    global CHECK_X, CHECK_Y, CHECK_X2, CHECK_Y2, CHECK_X3, CHECK_Y3
    
    # 查找游戏窗口
    try:
        window = gw.getWindowsWithTitle("猛兽派对")[0]
        hwnd = win32gui.FindWindow(None, "猛兽派对")
    except IndexError:
        if hasattr(gui, 'add_log'):
            gui.add_log("错误: 未找到 '猛兽派对' 游戏窗口，请确保游戏正在运行。", 'ERROR')
        else:
            print("错误: 未找到 '猛兽派对' 游戏窗口，请确保游戏正在运行。")
        return False

    # 获取窗口客户区的大小和位置
    rect = win32gui.GetClientRect(hwnd)
    window_width = rect[2] - rect[0]
    window_height = rect[3] - rect[1]
    window_left = window.left
    window_top = window.top

    gui.add_log(f"成功获取窗口: '猛兽派对'", 'SUCCESS')
    gui.add_log(f"窗口大小: {window_width}x{window_height}  位置: ({window_left}, {window_top})", 'INFO')

    # 分辨率检测和配置提示
    if window_width == 1920 and window_height == 1080:
        gui.add_log("检测到 1920*1080 分辨率，已应用优化坐标设置", 'SUCCESS')
    elif window_width == 3840 and window_height == 2160:
        gui.add_log("检测到 3840*2160 分辨率，已应用优化坐标设置", 'SUCCESS')
        gui.add_log("green_zone 固定坐标: (2140, 1870)", 'DEBUG')
        gui.add_log("orange_zone 固定坐标: (2155, 1850)", 'DEBUG')
    else:
        gui.add_log(f"未识别的分辨率 {window_width}*{window_height}，使用默认坐标设置", 'WARNING')

    # 定义像素检测的相对坐标比例
    COORDS_CONFIG = {
        "orange_zone": (0.5874, 0.9278, "张力表盘橙色区域"),
        "green_zone": (0.5444, 0.9067, "张力表盘绿色边界"),
        "bite_mark": (0.5083, 0.2811, "咬钩感叹号"),
    }

    # 计算绝对坐标
    def get_abs_coord(ratio_x, ratio_y, is_orange_zone=False):
        # 针对3840*2160分辨率的特殊处理
        if window_width == 3840 and window_height == 2160:
            if is_orange_zone:
                return 2155, 1850  # orange_zone固定坐标
            else:
                return 2113, 1910  # green_zone固定坐标
        else:
            # 其他分辨率使用比例计算
            return int(ratio_x * window_width + window_left), int(ratio_y * window_height + window_top)

    CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1], is_orange_zone=True)
    CHECK_X2, CHECK_Y2 = get_abs_coord(COORDS_CONFIG["green_zone"][0], COORDS_CONFIG["green_zone"][1])
    CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])

    gui.add_log(f"计算坐标: 橙色区({CHECK_X}, {CHECK_Y}), 绿色边界({CHECK_X2}, {CHECK_Y2}), 感叹号({CHECK_X3}, {CHECK_Y3})", 'DEBUG')
    
    return True

# --- 窗口位置检测计数器 ---
window_check_counter = 0
window_check_frequency = 10  # 每10次操作检测一次窗口位置

def update_window_position():
    """更新窗口位置信息"""
    global window, hwnd, window_width, window_height, window_left, window_top, window_check_counter
    global CHECK_X, CHECK_Y, CHECK_X2, CHECK_Y2, CHECK_X3, CHECK_Y3
    
    try:
        # 获取最新的窗口信息
        new_window = gw.getWindowsWithTitle("猛兽派对")[0]
        new_hwnd = win32gui.FindWindow(None, "猛兽派对")
        
        # 获取新的窗口位置和大小
        new_rect = win32gui.GetClientRect(new_hwnd)
        new_window_width = new_rect[2] - new_rect[0]
        new_window_height = new_rect[3] - new_rect[1]
        new_window_left = new_window.left
        new_window_top = new_window.top
        
        # 检查窗口位置是否发生变化
        if (new_window_left != window_left or new_window_top != window_top or 
            new_window_width != window_width or new_window_height != window_height):
            gui.add_log(f"检测到窗口位置变化: 从 ({window_left}, {window_top}) {window_width}x{window_height} "
                   f"变为 ({new_window_left}, {new_window_top}) {new_window_width}x{new_window_height}", 'WARNING')
            
            # 更新全局变量
            window = new_window
            hwnd = new_hwnd
            window_width = new_window_width
            window_height = new_window_height
            window_left = new_window_left
            window_top = new_window_top
            
            # 重新计算检测坐标
            COORDS_CONFIG = {
                "orange_zone": (0.5874, 0.9278, "张力表盘橙色区域"),
                "green_zone": (0.5444, 0.9067, "张力表盘绿色边界"),
                "bite_mark": (0.5083, 0.2811, "咬钩感叹号"),
            }
            
            def get_abs_coord(ratio_x, ratio_y, is_orange_zone=False):
                if window_width == 3840 and window_height == 2160:
                    if is_orange_zone:
                        return 2155, 1850
                    else:
                        return 2113, 1910
                else:
                    return int(ratio_x * window_width + window_left), int(ratio_y * window_height + window_top)
            
            CHECK_X, CHECK_Y = get_abs_coord(COORDS_CONFIG["orange_zone"][0], COORDS_CONFIG["orange_zone"][1], is_orange_zone=True)
            CHECK_X2, CHECK_Y2 = get_abs_coord(COORDS_CONFIG["green_zone"][0], COORDS_CONFIG["green_zone"][1])
            CHECK_X3, CHECK_Y3 = get_abs_coord(COORDS_CONFIG["bite_mark"][0], COORDS_CONFIG["bite_mark"][1])
            
            gui.add_log(f"已更新坐标 (优化版): 橙色区({CHECK_X}, {CHECK_Y}), 绿色边界({CHECK_X2}, {CHECK_Y2}), 感叹号({CHECK_X3}, {CHECK_Y3})", 'DEBUG')
        
        window_check_counter = 0  # 重置计数器
        return True
    except Exception as e:
        gui.add_log(f"更新窗口位置失败: {e}", 'ERROR')
        return False

def check_window_position():
    """检查窗口位置，每一定次数检测一次"""
    global window_check_counter
    window_check_counter += 1
    
    # 每window_check_frequency次操作检测一次窗口位置
    if window_check_counter >= window_check_frequency:
        update_window_position()

# --- Win32 SendInput 底层鼠标注入定义 ---
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", INPUT_I)
    ]

# 常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800

# 获取 SendInput 函数
SendInput = ctypes.windll.user32.SendInput

# --- 鼠标事件封装 ---
def _send_mouse_event(flags, dx=0, dy=0, data=0):
    """构建并发送一个鼠标INPUT事件"""
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(dx, dy, data, flags, 0, ctypes.pointer(extra))
    ii = INPUT_I()
    ii.mi = mi
    command = INPUT(INPUT_MOUSE, ii)
    # 1 表示发送一个 INPUT
    SendInput(1, ctypes.byref(command), ctypes.sizeof(command))

def left_down():
    _send_mouse_event(MOUSEEVENTF_LEFTDOWN)

def left_up():
    _send_mouse_event(MOUSEEVENTF_LEFTUP)

def left_click():
    """执行一次完整的左键单击"""
    left_down()
    time.sleep(0.05)  # 模拟按下的短暂时间
    left_up()

# 移动鼠标到绝对坐标 (0..65535 范围)
def move_mouse_abs(x, y):
    # 获取屏幕尺寸
    sx = ctypes.windll.user32.GetSystemMetrics(0)
    sy = ctypes.windll.user32.GetSystemMetrics(1)
    # 归一化到 0..65535
    nx = int(x * 65535 / (sx - 1))
    ny = int(y * 65535 / (sy - 1))
    _send_mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, nx, ny)

# --- 像素与颜色检测 ---
def get_pointer_color(x, y):
    """获取指定屏幕坐标的像素颜色"""
    return pyautogui.pixel(x, y)

def color_changed(base_color, new_color, tolerance=12):
    """检查两种颜色之间的差异是否超过容差"""
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) > tolerance) or (abs(bg - ng) > tolerance) or (abs(bb - nb) > tolerance)

def color_in_range(base_color, new_color, tolerance=12):
    """检查一种颜色是否在另一种颜色的容差范围内"""
    br, bg, bb = base_color
    nr, ng, nb = new_color
    return (abs(br - nr) <= tolerance) and (abs(bg - ng) <= tolerance) and (abs(bb - nb) <= tolerance)

def detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5):
    """统一检测鱼稀有度和指示颜色，合并两种检测逻辑"""
    # 定义稀有度颜色基准 (R, G, B)
    rarity_colors = {
        'legendary': (255, 201, 53),    # 传奇鱼
        'epic': (171, 99, 255),         # 史诗鱼
        'rare': (106, 175, 246),        # 稀有鱼
        'extraordinary': (142, 201, 85),# 非凡鱼
        'standard': (183, 186, 193)     # 标准鱼
    }
    
    # 定义指示颜色
    light_brown = (199, 118, 38)   # 浅棕色，容差±5
    bright_yellow = (255, 232, 79)  # 明黄色，容差±10
    
    top, left, bottom, right = region
    total_pixels = (bottom - top) * (right - left)
    if total_pixels <= 0:
        return 'airforce'
    
    # 记录每个稀有度的匹配像素数
    match_counts = {rarity: 0 for rarity in rarity_colors}
    brown_count = 0
    yellow_count = 0
    sample_count = 0
    step = 10  # 步长为10的顺序采样
    
    # 计算预计采样点数
    num_y_steps = ((bottom - top - 1) // step) + 1
    num_x_steps = ((right - left - 1) // step) + 1
    expected_samples = num_y_steps * num_x_steps
    
    if hasattr(gui, 'add_log'):
        gui.add_log(f"开始在区域 {region} 内步长{step}顺序采样 (预计 {expected_samples} 个点) 统一检测鱼稀有度和指示颜色...", 'DEBUG')
    
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            try:
                color = get_pointer_color(x, y)
                
                # 首先检查稀有度颜色
                rarity_matched = False
                for rarity, target_color in rarity_colors.items():
                    if color_in_range(target_color, color, tolerance):
                        match_counts[rarity] += 1
                        rarity_matched = True
                        break  # 一个像素只匹配一个稀有度（优先第一个匹配）
                
                # 如果没有匹配稀有度，检查指示颜色
                if not rarity_matched:
                    # 检查浅棕色（容差±5）
                    if color_in_range(light_brown, color, tolerance=5):
                        brown_count += 1
                    # 检查明黄色（容差±10）
                    elif color_in_range(bright_yellow, color, tolerance=10):
                        yellow_count += 1
                
                sample_count += 1
            except Exception as e:
                if hasattr(gui, 'add_log'):
                    gui.add_log(f"采样点 ({x}, {y}) 颜色获取失败: {e}", 'DEBUG')
                sample_count += 1  # 仍计入采样
    
    if sample_count == 0:
        if hasattr(gui, 'add_log'):
            gui.add_log("采样失败，无有效点", 'DEBUG')
        return 'airforce'
    
    # 计算每个稀有度的匹配比例
    max_ratio = 0
    best_rarity = 'airforce'
    for rarity, count in match_counts.items():
        ratio = count / sample_count
        if hasattr(gui, 'add_log'):
            gui.add_log(f"{rarity}: {count}/{sample_count} ({ratio:.2%})", 'DEBUG')
        if ratio > max_ratio and ratio >= rarity_threshold:
            max_ratio = ratio
            best_rarity = rarity
    
    # 计算指示颜色的匹配比例
    brown_ratio = brown_count / sample_count
    yellow_ratio = yellow_count / sample_count
    if hasattr(gui, 'add_log'):
        gui.add_log(f"标志色1: {brown_count}/{sample_count} ({brown_ratio:.2%})", 'DEBUG')
        gui.add_log(f"标志色2: {yellow_count}/{sample_count} ({yellow_ratio:.2%})", 'DEBUG')
    
    # 优先返回稀有度检测结果
    if best_rarity != 'airforce':
        if hasattr(gui, 'add_log'):
            gui.add_log(f"检测到 {best_rarity} 鱼 (比例 {max_ratio:.2%})", 'DEBUG')
        return best_rarity
    
    # 如果稀有度检测失败，检查指示颜色
    if brown_ratio >= indicator_threshold or yellow_ratio >= indicator_threshold:
        if hasattr(gui, 'add_log'):
            gui.add_log(f"检测到鱼指示颜色 ({brown_ratio:.2%} 或 {yellow_ratio:.2%} ≥ {indicator_threshold:.2%})", 'DEBUG')
            gui.add_log("钓到了鱼！但检测稀有度失败。", 'WARNING')
        return 'unknown'  # 返回未知稀有度
    
    # 都未检测到
    if hasattr(gui, 'add_log'):
        gui.add_log(f"未检测到足够匹配像素，判定为空军 (稀有度阈值 {rarity_threshold}, 指示颜色阈值 {indicator_threshold})", 'DEBUG')
    return 'airforce'

# --- 混合匹配咬钩检测 ---

# 1. 定义精确的搜索区域 (ROI)
def initialize_roi():
    global roi_search_area, LOWER_YELLOW, UPPER_YELLOW, template, template_bgr, template_alpha, w, h
    
    center_x, center_y = window_left + window_width // 2, window_top + window_height // 2
    roi_width = int(window_width * 0.08 * 2)
    roi_height = int(window_height * 0.40)
    roi_x = center_x - roi_width // 2
    roi_y = center_y - roi_height
    roi_search_area = (roi_x, roi_y, roi_width, roi_height)
    
    if hasattr(gui, 'add_log'):
        gui.add_log(f"颜色定位搜索区域 (ROI): x={roi_x}, y={roi_y}, w={roi_width}, h={roi_height}", 'DEBUG')

    # 2. 定义黄色HSV范围
    LOWER_YELLOW = np.array([22, 120, 200])
    UPPER_YELLOW = np.array([28, 255, 255])

    # 3. 读取OpenCV模板（保持透明通道）
    template = cv2.imread(resource_path("exclamation_mark.png"), cv2.IMREAD_UNCHANGED)
    if template is None:
        if hasattr(gui, 'add_log'):
            gui.add_log("错误: 未找到 exclamation_mark.png 模板文件", 'ERROR')
        return False
        
    template_bgr = template[:, :, :3]        # RGB部分
    template_alpha = template[:, :, 3]       # alpha通道作为mask
    w, h = template_bgr.shape[1], template_bgr.shape[0]
    if hasattr(gui, 'add_log'):
        gui.add_log(f"已加载模板 'exclamation_mark.png' (大小: {w}x{h})", 'DEBUG')
    return True

def find_yellow_blob(img_bgr):
    """在图中寻找最大的黄色像素簇，返回其中心点"""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)
    
    # 寻找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None

    # 找到最大的轮廓
    largest_contour = max(contours, key=cv2.contourArea)
    
    # 如果最大的轮廓太小，也忽略
    if cv2.contourArea(largest_contour) < 50:
        return None
        
    # 计算中心点
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    
    return (cx, cy)

def verify_with_opencv(img_bgr, center_point, threshold=0.5):
    """在候选中心点周围的小区域内进行OpenCV模板匹配验证"""
    # 定义一个紧密包裹感叹号的小ROI
    verify_roi_w, verify_roi_h = 100, 200
    vx = center_point[0] - verify_roi_w // 2
    vy = center_point[1] - verify_roi_h // 2
    
    # 确保ROI在图像范围内
    vx = max(0, vx)
    vy = max(0, vy)
    
    # 从原始大图中截取小ROI
    img_roi = img_bgr[vy:vy+verify_roi_h, vx:vx+verify_roi_w]
    
    if img_roi.shape[0] < 1 or img_roi.shape[1] < 1:
        return False

    # 在小ROI上进行模板匹配
    res = cv2.matchTemplate(img_roi, template_bgr, cv2.TM_CCOEFF_NORMED, mask=template_alpha)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    
    return max_val >= threshold

# --- 核心钓鱼逻辑 ---
def bite_check():
    """混合模式检测鱼是否咬钩（先黄色定位，再OpenCV验证）"""
    if hasattr(gui, 'add_log'):
        gui.add_log(f"等待鱼咬钩 (混合模式: 黄色定位 + OpenCV验证)...", 'STATUS')
    timeout = 40
    start_time = time.time()
    
    check_interval = 0.1  # 每0.1秒检测一次
    
    while is_running:
        # 使用可中断的等待
        elapsed = 0
        while elapsed < check_interval and is_running:
            time.sleep(0.01)  # 小段睡眠，便于快速响应中断
            elapsed += 0.01
        
        if not is_running:
            break
            
        # 1. 快速颜色定位
        try:
            screenshot = pyautogui.screenshot(region=roi_search_area)
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            if hasattr(gui, 'add_log'):
                gui.add_log(f"截图失败: {e}", 'WARNING')
            continue
            
        blob_center = find_yellow_blob(img_bgr)
        
        if blob_center:
            # 2. 精确OpenCV模板验证
            if verify_with_opencv(img_bgr, blob_center, threshold=0.5):
                if hasattr(gui, 'add_log'):
                    gui.add_log("有鱼咬钩！ (混合匹配成功)", 'SUCCESS')
                # 使用可中断的随机等待
                wait_time = random.uniform(0.1, 0.2)
                elapsed = 0
                while elapsed < wait_time and is_running:
                    time.sleep(0.01)
                    elapsed += 0.01
                if not is_running:
                    return False
                return True

        # 判断是否超时
        if time.time() - start_time >= timeout:
            if hasattr(gui, 'add_log'):
                gui.add_log("咬钩检测超时，未检测到鱼", 'WARNING')
            return False
            
    if hasattr(gui, 'add_log'):
        gui.add_log("咬钩检测被中断", 'INFO')
    return False

def reel():
    """控制收杆过程，处理张力"""
    start_time = time.time()
    base_color_green = (127, 181, 77)   # 张力表盘绿色区
    base_color_orange = (255, 195, 83)  # 张力表盘橙色区
    success_popup_delay = 0.6           # 钓鱼成功弹窗的延迟时间（秒）
    
    if hasattr(gui, 'add_log'):
        gui.add_log(f"开始收杆...", 'STATUS')
        gui.add_log(f"目标颜色: 绿色区={base_color_green}, 橙色区={base_color_orange}", 'DEBUG')
    
    times = 0
    try:
        initial_orange = get_pointer_color(CHECK_X, CHECK_Y)
        if hasattr(gui, 'add_log'):
            gui.add_log(f"初始橙色区颜色: {initial_orange}", 'DEBUG')
    except Exception as e:
        if hasattr(gui, 'add_log'):
            gui.add_log(f"读取初始像素失败: {e}", 'WARNING')

    while is_running:
        # 检查窗口位置
        check_window_position()
        
        if not is_running:
            if hasattr(gui, 'add_log'):
                gui.add_log("收杆被中断", 'INFO')
            break
            
        # 紧急退出
        if USE_KEYBOARD and keyboard.is_pressed('q'):
            left_up()
            if hasattr(gui, 'add_log'):
                gui.add_log("检测到 'q'，紧急终止脚本", 'INFO')
            sys.exit(0)

        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
            color_bound = get_pointer_color(CHECK_X2, CHECK_Y2)
        except Exception as e:
            if hasattr(gui, 'add_log'):
                gui.add_log(f"读取像素失败: {e}", 'WARNING')
            time.sleep(0.05)
            continue

        # 条件1：钓鱼成功 (张力表盘消失)
        if times >= 10 and color_changed(base_color_orange, color_exist, tolerance=100):
            if hasattr(gui, 'add_log'):
                gui.add_log(f"检测到张力表盘消失，准备验证钓鱼结果...", 'STATUS')
            left_up()
            
            # 等待0.4秒后进入第一轮检测
            time.sleep(0.4)

            center_x = window_left + window_width // 2
            # 根据不同分辨率设置不同的检测区域
            if window_width == 1920 and window_height == 1080:
                region_top = window_top + 160
                region_bottom = window_top + 200
                region_left = window_left + 875
                region_right = window_left + 960
            elif window_width == 3840 and window_height == 2160:
                region_top = window_top + 230
                region_bottom = window_top + 320
                region_left = center_x - 130
                region_right = center_x + 20
            else:
                # 默认设置（保持原有逻辑）
                region_top = window_top + 190
                region_bottom = window_top + 250
                region_left = center_x - 130
                region_right = center_x + 20
            
            # 确保区域在窗口范围内
            region_top = max(window_top, region_top)
            region_bottom = min(window_top + window_height, region_bottom)
            region_left = max(window_left, region_left)
            region_right = min(window_left + window_width, region_right)
            
            region = (region_top, region_left, region_bottom, region_right)
            
            # 多轮检测逻辑（最多5秒）
            max_wait_time = 5
            elapsed_time = 0
            check_interval = 1  # 每次检测间隔1秒
            
            while elapsed_time < max_wait_time and is_running:
                if hasattr(gui, 'add_log'):
                    gui.add_log(f"第{elapsed_time // check_interval + 1}轮统一检测鱼稀有度和指示颜色，区域: {region}", 'DEBUG')
                rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
                
                if not is_running:
                    return None  # 程序中断时不记录为空军
                
                if rarity != 'airforce':
                    if hasattr(gui, 'add_log'):
                        gui.add_log(f"钓鱼成功！稀有度: {rarity}", 'SUCCESS')
                    return rarity
                
                # 都未检测到，等待1秒后重试（使用可中断等待）
                if elapsed_time + check_interval < max_wait_time:
                    if hasattr(gui, 'add_log'):
                        gui.add_log(f"未检测到鱼，{check_interval}秒后重试...", 'DEBUG')
                    # 使用可中断的等待
                    wait_elapsed = 0
                    while wait_elapsed < check_interval and is_running:
                        time.sleep(0.01)
                        wait_elapsed += 0.01
                    elapsed_time += check_interval
                else:
                    break
            
            # 超时仍未检测到
            if hasattr(gui, 'add_log'):
                gui.add_log(f"检测超时（{max_wait_time}秒），判定为空军", 'WARNING')
            return 'airforce'

        # 条件2：超时
        if time.time() - start_time > 30:
            if hasattr(gui, 'add_log'):
                gui.add_log("收杆超时 (30秒)", 'WARNING')
            left_up()
            return 'airforce'  # 超时视为空军

        times += 1
        time.sleep(0.1)

        if times % 10 == 0:
            if hasattr(gui, 'add_log'):
                gui.add_log(f"收杆中 (第 {times} 次): 橙色区={color_exist}, 绿色边界={color_bound}", 'DEBUG')

        left_down()

        if times % 15 == 0:
            if hasattr(gui, 'add_log'):
                gui.add_log("持续收杆...", 'STATUS')
            
        # 条件3：张力过高，需要松手
        if times >= 30 and color_changed(base_color_green, color_bound, tolerance=40):
            try:
                # 松手前再次确认张力表盘是否存在
                color_exist_before = get_pointer_color(CHECK_X, CHECK_Y)
                if color_changed(base_color_orange, color_exist_before, tolerance=100):
                    gui.add_log(f"松手前检测到张力表盘消失，准备验证钓鱼结果...", 'STATUS')
                    left_up()
                    
                    # 等待0.4秒后进入第一轮检测
                    time.sleep(0.4)

                    center_x = window_left + window_width // 2
                    # 根据不同分辨率设置不同的检测区域
                    if window_width == 1920 and window_height == 1080:
                        region_top = window_top + 160
                        region_bottom = window_top + 200
                        region_left = window_left + 875
                        region_right = window_left + 960
                    elif window_width == 3840 and window_height == 2160:
                        region_top = window_top + 230
                        region_bottom = window_top + 320
                        region_left = center_x - 130
                        region_right = center_x + 20
                    else:
                        # 默认设置（保持原有逻辑）
                        region_top = window_top + 190
                        region_bottom = window_top + 250
                        region_left = center_x - 130
                        region_right = center_x + 20
                    
                    # 确保区域在窗口范围内
                    region_top = max(window_top, region_top)
                    region_bottom = min(window_top + window_height, region_bottom)
                    region_left = max(window_left, region_left)
                    region_right = min(window_left + window_width, region_right)
                    
                    region = (region_top, region_left, region_bottom, region_right)
                    
                    # 多轮检测逻辑（最多5秒）
                    max_wait_time = 5
                    elapsed_time = 0
                    check_interval = 1  # 每次检测间隔1秒
                    
                    while elapsed_time < max_wait_time and is_running:
                        gui.add_log(f"第{elapsed_time // check_interval + 1}轮统一检测鱼稀有度和指示颜色 (松手后)，区域: {region}", 'DEBUG')
                        rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
                        
                        if not is_running:
                            return None  # 程序中断时不记录为空军
                        
                        if rarity != 'airforce':
                            gui.add_log(f"钓鱼成功！稀有度: {rarity}", 'SUCCESS')
                            return rarity
                        
                        # 都未检测到，等待1秒后重试（使用可中断等待）
                        if elapsed_time + check_interval < max_wait_time:
                            gui.add_log(f"未检测到鱼，{check_interval}秒后重试...", 'DEBUG')
                            # 使用可中断的等待
                            wait_elapsed = 0
                            while wait_elapsed < check_interval and is_running:
                                time.sleep(0.01)
                                wait_elapsed += 0.01
                            elapsed_time += check_interval
                        else:
                            break
                    
                    # 超时仍未检测到
                    gui.add_log(f"检测超时（{max_wait_time}秒），判定为空军", 'WARNING')
                    return 'airforce'
            except Exception as e:
                gui.add_log(f"松手前检查像素失败: {e}", 'WARNING')
            
            gui.add_log(f"张力过高，暂时松手。边界颜色: {color_bound}", 'STATUS')
            left_up()
            sleep_time = random.uniform(2.0, 3.0)
            # 使用可中断的等待
            elapsed = 0
            while elapsed < sleep_time and is_running:
                time.sleep(0.01)
                elapsed += 0.01
            if not is_running:
                return None  # 程序中断时不记录为空军
            gui.add_log("继续收杆", 'STATUS')

def auto_fish_once():
    """执行一轮完整的自动钓鱼流程"""
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, unknown_count, airforce_count
    
    gui.add_log("=== 开始新一轮钓鱼 ===", 'INFO')
    
    # 1. 抛竿
    gui.add_log("抛竿中...", 'STATUS')
    left_down()

    #1.5 纠正身位
    def async_press_a():
        sleep_time1 = random.uniform(0.6, 2.1)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time1 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        keyboard.press('a')
        sleep_time2 = random.uniform(0.25, 0.38)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time2 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            keyboard.release('a')
            return
            
        keyboard.release('a')
    
    async_thread = threading.Thread(target=async_press_a)
    async_thread.start()

    sleep_time = random.uniform(3.0, 4.0)
    # 使用可中断的等待
    elapsed = 0
    while elapsed < sleep_time and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        left_up()
        return
    left_up()
    gui.add_log("抛竿完成", 'SUCCESS')

    # 2. 等待鱼咬钩
    if not bite_check():
        gui.add_log("本轮未钓到鱼或被中断", 'WARNING')
        return

    # 3. 咬钩后初始点击
    click_duration = random.uniform(0.1, 0.3)
    gui.add_log(f"咬钩后初始点击，持续 {click_duration:.2f} 秒", 'STATUS')
    left_down()
    time.sleep(click_duration)
    left_up()
    
    # 4. 等待浮漂稳定
    wait_time = 1.6 + 2 * click_duration
    gui.add_log(f"等待浮漂上浮，持续 {wait_time:.2f} 秒", 'STATUS')
    # 使用可中断的等待
    elapsed = 0
    while elapsed < wait_time and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        return

    # 5. 收杆与张力控制
    reel_result = reel()
    
    # 处理结果
    if reel_result is None:
        # 程序被中断，不记录任何结果
        if hasattr(gui, 'add_log'):
            gui.add_log("钓鱼过程被中断，不记录结果", 'WARNING')
        return
    elif reel_result == 'airforce':
        airforce_count += 1
    else:
        # 6. 收鱼
        if hasattr(gui, 'add_log'):
            gui.add_log("收鱼中...", 'STATUS')
        sleep_time = random.uniform(1.5, 2.5)
        # 使用可中断的等待
        elapsed = 0
        while elapsed < sleep_time and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        # 使用可中断的等待
        elapsed = 0
        while elapsed < 0.5 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            return
            
        left_down()
        
        # 使用可中断的等待
        elapsed = 0
        while elapsed < 0.2 and is_running:
            time.sleep(0.01)
            elapsed += 0.01
        if not is_running:
            left_up()
            return
            
        left_up()
        # 更新计数器
        if reel_result == 'legendary':
            legendary_count += 1
        elif reel_result == 'epic':
            epic_count += 1
        elif reel_result == 'rare':
            rare_count += 1
        elif reel_result == 'extraordinary':
            extraordinary_count += 1
        elif reel_result == 'standard':
            standard_count += 1
        elif reel_result == 'unknown':
            unknown_count += 1
    
    # 只有在reel_result不为None时才记录钓鱼结果
    if reel_result is not None:
        record_fishing_result(reel_result)
    
    # 打印本次结果
    if reel_result == 'airforce':
        if hasattr(gui, 'add_log'):
            gui.add_log("这次钓鱼空军", 'WARNING')
    elif reel_result == 'unknown':
        if hasattr(gui, 'add_log'):
            gui.add_log("这次钓到了鱼，但稀有度未知", 'WARNING')
    else:
        chinese_rarity = {
            'legendary': '传奇',
            'epic': '史诗',
            'rare': '稀有',
            'extraordinary': '非凡',
            'standard': '标准'
        }
        zh_name = chinese_rarity[reel_result]
        if hasattr(gui, 'add_log'):
            gui.add_log(f"这次钓到了{zh_name}鱼", 'SUCCESS')
    
    if hasattr(gui, 'add_log'):
        gui.add_log("=== 本轮钓鱼结束 ===", 'INFO')
    # 使用可中断的等待
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01

# --- 仅统计模式的钓鱼逻辑 ---
def auto_fish_logger_once():
    """仅统计模式下的钓鱼记录逻辑（不执行任何游戏操作）"""
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, unknown_count, airforce_count
    
    gui.add_log("=== 开始仅统计模式记录 ===", 'INFO')
    
    # 1. 等待鱼咬钩
    if not bite_check_logger():
        gui.add_log("本轮未检测到咬钩或被中断", 'WARNING')
        return
    
    # 2. 检测到咬钩后等待2秒
    gui.add_log("检测到叹号后等待2秒...", 'STATUS')
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        return
    
    # 3. 开始检测压力表盘是否消失
    gui.add_log("开始检测压力表盘是否消失...", 'STATUS')
    base_color_orange = (255, 195, 83)
    start_time = time.time()
    timeout = 30
    
    while is_running:
        if time.time() - start_time > timeout:
            gui.add_log("检测压力表盘超时（30秒），判定为空军", 'WARNING')
            airforce_count += 1
            record_fishing_result('airforce')
            gui.add_log("这次钓鱼空军", 'WARNING')
            break
        
        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
        except Exception as e:
            gui.add_log(f"读取像素失败: {e}", 'WARNING')
            time.sleep(0.1)
            continue
        
        if color_changed(base_color_orange, color_exist, tolerance=100):
            gui.add_log("检测到压力表盘消失，开始检测稀有度...", 'SUCCESS')
            
            # 等待0.4秒让UI稳定
            elapsed = 0
            while elapsed < 0.4 and is_running:
                time.sleep(0.01)
                elapsed += 0.01
            if not is_running:
                return
            
            # 根据不同分辨率设置不同的检测区域
            center_x = window_left + window_width // 2
            if window_width == 1920 and window_height == 1080:
                region = (window_top + 160, window_left + 875, window_top + 200, window_left + 960)
            elif window_width == 3840 and window_height == 2160:
                region = (window_top + 230, center_x - 130, window_top + 320, center_x + 20)
            else:
                region = (window_top + 190, center_x - 130, window_top + 250, center_x + 20)
            
            # 检测鱼的稀有度
            rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
            
            if rarity != 'airforce':
                gui.add_log(f"钓鱼成功！稀有度: {rarity}", 'SUCCESS')
            else:
                gui.add_log("判定为空军", 'WARNING')
            
            # 更新计数器
            if rarity == 'legendary':
                legendary_count += 1
            elif rarity == 'epic':
                epic_count += 1
            elif rarity == 'rare':
                rare_count += 1
            elif rarity == 'extraordinary':
                extraordinary_count += 1
            elif rarity == 'standard':
                standard_count += 1
            elif rarity == 'unknown':
                unknown_count += 1
            elif rarity == 'airforce':
                airforce_count += 1
            
            # 记录结果
            record_fishing_result(rarity)
            
            # 打印本次结果
            if rarity == 'airforce':
                gui.add_log("这次钓鱼空军", 'WARNING')
            elif rarity == 'unknown':
                gui.add_log("这次钓到了鱼，但稀有度未知", 'WARNING')
            else:
                chinese_rarity = {
                    'legendary': '传奇',
                    'epic': '史诗',
                    'rare': '稀有',
                    'extraordinary': '非凡',
                    'standard': '标准'
                }
                zh_name = chinese_rarity[rarity]
                gui.add_log(f"这次钓到了{zh_name}鱼", 'SUCCESS')
            break
        
        time.sleep(0.1)
    
    gui.add_log("=== 仅统计模式记录结束 ===", 'INFO')
    
    # 使用可中断的等待
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01

def bite_check_logger():
    """仅统计模式下的咬钩检测（不执行任何游戏操作）"""
    gui.add_log(f"等待鱼咬钩（仅统计模式）...", 'STATUS')
    timeout = 40
    start_time = time.time()
    
    check_interval = 0.1  # 每0.1秒检测一次
    
    while is_running:
        # 使用可中断的等待
        elapsed = 0
        while elapsed < check_interval and is_running:
            time.sleep(0.01)  # 小段睡眠，便于快速响应中断
            elapsed += 0.01
        
        if not is_running:
            break
            
        # 1. 快速颜色定位
        try:
            screenshot = pyautogui.screenshot(region=roi_search_area)
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            gui.add_log(f"截图失败: {e}", 'WARNING')
            continue
            
        blob_center = find_yellow_blob(img_bgr)
        
        if blob_center:
            # 2. 精确OpenCV模板验证
            if verify_with_opencv(img_bgr, blob_center, threshold=0.5):
                gui.add_log("检测到叹号！（仅统计模式）", 'SUCCESS')
                return True

        # 判断是否超时
        if time.time() - start_time >= timeout:
            gui.add_log("咬钩检测超时，未检测到鱼", 'WARNING')
            return False
            
    gui.add_log("咬钩检测被中断", 'INFO')
    return False

# --- 键盘监听 ---
def keyboard_listener():
    """监听键盘事件，用于暂停/恢复脚本和切换统计功能"""
    ctrl_k_pressed = False  # 跟踪Ctrl+K是否被按下
    
    while True:
        if USE_KEYBOARD:
            if keyboard.is_pressed('ctrl+l'):
                global afk_mode
                if afk_mode:
                    # 如果在挂机模式，停止挂机
                    gui.toggle_afk_mode()
                elif is_running:
                    gui.stop_fishing()
                else:
                    gui.start_fishing()
                time.sleep(0.5)  # 防止按键重复检测
            elif keyboard.is_pressed('ctrl+k'):
                if not ctrl_k_pressed:
                    ctrl_k_pressed = True
                    gui.toggle_statistics()
                    time.sleep(0.5)  # 防止按键重复检测
            elif keyboard.is_pressed('enter') and ctrl_k_pressed:
                # Ctrl+K+Enter 组合键：归档统计文件
                gui.archive_statistics()
                ctrl_k_pressed = False  # 重置状态
                time.sleep(0.5)  # 防止按键重复检测
            elif keyboard.is_pressed('ctrl+m'):
                # Ctrl+M 组合键：切换仅统计模式
                gui.toggle_statistics_mode()
                time.sleep(0.5)  # 防止按键重复检测
            else:
                # 如果Ctrl+K被释放，重置状态
                if ctrl_k_pressed and not keyboard.is_pressed('ctrl+k'):
                    ctrl_k_pressed = False
        time.sleep(0.1)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    
    # 创建GUI实例
    gui = FishingGUI(root)
    
    # 初始化ROI
    # 在后台线程中检测窗口和初始化ROI
    window_initialized = False
    def window_detection_thread():
        global window_initialized
        while not window_initialized:
            if initialize_window():
                window_initialized = True
                gui.add_log("游戏窗口检测成功", 'SUCCESS')
                gui.status_label.config(text="● 就绪", fg='#00FF00')
                gui.start_btn.config(state=tk.NORMAL)
                
                # 初始化ROI
                if not initialize_roi():
                    gui.add_log("初始化ROI失败", 'ERROR')
                else:
                    gui.add_log("ROI初始化成功", 'SUCCESS')
            else:
                gui.add_log("错误: 未找到 '猛兽派对' 游戏窗口，请确保游戏正在运行。", 'ERROR')
                gui.add_log("程序将继续每0.5秒检测一次窗口，直到找到游戏窗口为止...", 'WARNING')
                gui.status_label.config(text="● 等待游戏窗口", fg='#FFAA00')
                time.sleep(0.5)
    
    # 启动窗口检测线程
    detection_thread = threading.Thread(target=window_detection_thread, daemon=True)
    detection_thread.start()
    # 在后台启动键盘监听线程
    listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
    listener_thread.start()
    
    # 显示初始信息
    gui.add_log("="*44, 'INFO')
    gui.add_log("猛兽派对 - 自动钓鱼脚本", 'INFO')
    gui.add_log("作者: Fox, 由SammFang改版", 'INFO')
    gui.add_log("="*44, 'INFO')
    gui.add_log("请将游戏窗口置于前台，脚本开始后不要移动窗口。", 'WARNING')
    gui.add_log("按 Ctrl+L 可以暂停或恢复脚本。", 'WARNING')
    gui.add_log(f"按 Ctrl+K 可以{'创建统计文件并' if not STATISTICS_ENABLED else ''}切换统计功能。", 'INFO')
    gui.add_log("按 Ctrl+K+Enter 可以归档当前统计文件并创建新的统计文件。", 'INFO')
    gui.add_log("按 'q' 可以紧急终止脚本。", 'WARNING')
    
    # 自动刷新统计信息
    if STATISTICS_ENABLED:
        gui.add_log("正在加载统计数据...", 'INFO')
        gui.refresh_statistics()
    else:
        gui.add_log("统计功能未启用，按 Ctrl+K 可以启用统计功能", 'WARNING')
    
    # 启动GUI主循环
    root.mainloop()

# --- 仅统计模式的钓鱼逻辑 ---
def auto_fish_logger_once():
    """仅统计模式下的钓鱼记录逻辑（不执行任何游戏操作）"""
    global legendary_count, epic_count, rare_count, extraordinary_count, standard_count, unknown_count, airforce_count
    
    gui.add_log("=== 开始仅统计模式记录 ===", 'INFO')
    
    # 1. 等待鱼咬钩
    if not bite_check_logger():
        gui.add_log("本轮未检测到咬钩或被中断", 'WARNING')
        return
    
    # 2. 检测到咬钩后等待2秒
    gui.add_log("检测到叹号后等待2秒...", 'STATUS')
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01
    if not is_running:
        return
    
    # 3. 开始检测压力表盘是否消失
    gui.add_log("开始检测压力表盘是否消失...", 'STATUS')
    base_color_orange = (255, 195, 83)
    start_time = time.time()
    timeout = 30
    
    while is_running:
        if time.time() - start_time > timeout:
            gui.add_log("检测压力表盘超时（30秒），判定为空军", 'WARNING')
            airforce_count += 1
            record_fishing_result('airforce')
            gui.add_log("这次钓鱼空军", 'WARNING')
            break
        
        try:
            color_exist = get_pointer_color(CHECK_X, CHECK_Y)
        except Exception as e:
            gui.add_log(f"读取像素失败: {e}", 'WARNING')
            time.sleep(0.1)
            continue
        
        if color_changed(base_color_orange, color_exist, tolerance=100):
            gui.add_log("检测到压力表盘消失，开始检测稀有度...", 'SUCCESS')
            
            # 等待0.4秒让UI稳定
            elapsed = 0
            while elapsed < 0.4 and is_running:
                time.sleep(0.01)
                elapsed += 0.01
            if not is_running:
                return
            
            # 根据不同分辨率设置不同的检测区域
            center_x = window_left + window_width // 2
            if window_width == 1920 and window_height == 1080:
                region = (window_top + 160, window_left + 875, window_top + 200, window_left + 960)
            elif window_width == 3840 and window_height == 2160:
                region = (window_top + 230, center_x - 130, window_top + 320, center_x + 20)
            else:
                region = (window_top + 190, center_x - 130, window_top + 250, center_x + 20)
            
            # 检测鱼的稀有度
            rarity = detect_fish_unified(region, rarity_threshold=0.1, indicator_threshold=0.05, tolerance=5)
            
            if rarity != 'airforce':
                gui.add_log(f"钓鱼成功！稀有度: {rarity}", 'SUCCESS')
            else:
                gui.add_log("判定为空军", 'WARNING')
            
            # 更新计数器
            if rarity == 'legendary':
                legendary_count += 1
            elif rarity == 'epic':
                epic_count += 1
            elif rarity == 'rare':
                rare_count += 1
            elif rarity == 'extraordinary':
                extraordinary_count += 1
            elif rarity == 'standard':
                standard_count += 1
            elif rarity == 'unknown':
                unknown_count += 1
            elif rarity == 'airforce':
                airforce_count += 1
            
            # 记录结果
            record_fishing_result(rarity)
            
            # 打印本次结果
            if rarity == 'airforce':
                gui.add_log("这次钓鱼空军", 'WARNING')
            elif rarity == 'unknown':
                gui.add_log("这次钓到了鱼，但稀有度未知", 'WARNING')
            else:
                chinese_rarity = {
                    'legendary': '传奇',
                    'epic': '史诗',
                    'rare': '稀有',
                    'extraordinary': '非凡',
                    'standard': '标准'
                }
                zh_name = chinese_rarity[rarity]
                gui.add_log(f"这次钓到了{zh_name}鱼", 'SUCCESS')
            break
        
        time.sleep(0.1)
    
    gui.add_log("=== 仅统计模式记录结束 ===", 'INFO')
    
    # 使用可中断的等待
    elapsed = 0
    while elapsed < 2 and is_running:
        time.sleep(0.01)
        elapsed += 0.01

def bite_check_logger():
    """仅统计模式下的咬钩检测（不执行任何游戏操作）"""
    gui.add_log(f"等待鱼咬钩（仅统计模式）...", 'STATUS')
    timeout = 40
    start_time = time.time()
    
    check_interval = 0.1  # 每0.1秒检测一次
    
    while is_running:
        # 使用可中断的等待
        elapsed = 0
        while elapsed < check_interval and is_running:
            time.sleep(0.01)  # 小段睡眠，便于快速响应中断
            elapsed += 0.01
        
        if not is_running:
            break
            
        # 1. 快速颜色定位
        try:
            screenshot = pyautogui.screenshot(region=roi_search_area)
            img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            gui.add_log(f"截图失败: {e}", 'WARNING')
            continue
            
        blob_center = find_yellow_blob(img_bgr)
        
        if blob_center:
            # 2. 精确OpenCV模板验证
            if verify_with_opencv(img_bgr, blob_center, threshold=0.5):
                gui.add_log("检测到叹号！（仅统计模式）", 'SUCCESS')
                return True

        # 判断是否超时
        if time.time() - start_time >= timeout:
            gui.add_log("咬钩检测超时，未检测到鱼", 'WARNING')
            return False
            
    gui.add_log("咬钩检测被中断", 'INFO')
    return False
