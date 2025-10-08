import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
import json
import os
from collections import defaultdict

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 稀有度颜色定义
rarity_colors = {
    'legendary': (255/255, 201/255, 53/255),    # 传奇鱼
    'epic': (171/255, 99/255, 255/255),         # 史诗鱼
    'rare': (106/255, 175/255, 246/255),        # 稀有鱼
    'extraordinary': (142/255, 201/255, 85/255),# 非凡鱼
    'standard': (183/255, 186/255, 193/255),    # 标准鱼
    'airforce': (255/255, 0/255, 0/255)         # 空军
}

class FishingDataProcessor:
    def __init__(self, data_dir="dist/archived-data"):
        self.data_dir = data_dir
        self.all_records = []
        print(f"初始化数据处理器，数据目录: {data_dir}")
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有数据文件"""
        print("开始加载数据...")
        if not os.path.exists(self.data_dir):
            print(f"警告: 数据目录 {self.data_dir} 不存在")
            return
        
        file_count = 0
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        records = data.get('records', [])
                        self.all_records.extend(records)
                        file_count += 1
                except Exception as e:
                    print(f"警告: 加载文件 {filename} 时出错: {e}")
        
        print(f"总共加载了 {file_count} 个文件，记录总数: {len(self.all_records)}")
        
        if self.all_records:
            # 按时间戳排序
            self.all_records.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
            print("数据已按时间排序")
    
    def get_statistics(self):
        """获取统计信息"""
        stats = {
            'total_records': len(self.all_records),
            'fish_counts': defaultdict(int),
            'airforce_count': 0,
            'rarity_percentages': {},
            'airforce_rate': 0.0
        }
        
        for record in self.all_records:
            if record['is_airforce']:
                stats['airforce_count'] += 1
            else:
                stats['fish_counts'][record['rarity']] += 1
        
        total_fish = len(self.all_records)
        if total_fish > 0:
            stats['airforce_rate'] = (stats['airforce_count'] / total_fish) * 100
            for rarity, count in stats['fish_counts'].items():
                stats['rarity_percentages'][rarity] = (count / total_fish) * 100
        
        return stats
    
    def get_rarity_trend_data(self, interval_minutes=30):
        """获取稀有度趋势数据，处理样本量过小的区间"""
        print(f"计算趋势数据（时间间隔: {interval_minutes}分钟）...")
        if not self.all_records:
            print("没有记录，返回空数据")
            return {}
        
        # 获取时间范围
        start_time = datetime.strptime(self.all_records[0]['timestamp'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(self.all_records[-1]['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        # 创建时间区间
        interval = timedelta(minutes=interval_minutes)
        time_slots = []
        current_time = start_time
        
        while current_time <= end_time:
            time_slots.append(current_time)
            current_time += interval
        
        # 预处理：为每个记录分配时间区间
        slot_records = defaultdict(list)
        
        for record in self.all_records:
            record_time = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
            
            for i in range(len(time_slots) - 1):
                if time_slots[i] <= record_time < time_slots[i + 1]:
                    slot_records[i].append(record)
                    break
        
        # 过滤掉没有记录的时间区间
        valid_slots = [(i, records) for i, records in slot_records.items() if records]
        valid_slots.sort(key=lambda x: x[0])
        
        if not valid_slots:
            return {}
        
        # 固定最小样本量阈值为20
        min_sample_threshold = 20
        
        print(f"有效时间段: {len(valid_slots)}, 最小样本量阈值: {min_sample_threshold}")
        
        # 合并样本量过小的区间
        merged_slots = []
        skip_next = False
        
        for idx, (slot_idx, records) in enumerate(valid_slots):
            if skip_next:
                skip_next = False
                continue
                
            # 检查当前区间样本量是否过小
            if len(records) < min_sample_threshold:
                # 将样本分配给相邻区间
                if idx > 0 and idx < len(valid_slots) - 1:
                    # 有两个相邻区间，平分
                    prev_slot_idx, prev_records = valid_slots[idx - 1]
                    next_slot_idx, next_records = valid_slots[idx + 1]
                    
                    # 更新前一个区间（已经在merged_slots中）
                    if merged_slots:
                        merged_slots[-1] = (merged_slots[-1][0], merged_slots[-1][1] + records[:len(records)//2])
                    
                    # 将剩余样本加到下一个区间，并跳过下一个区间的正常处理
                    next_records_combined = records[len(records)//2:] + next_records
                    merged_slots.append((next_slot_idx, next_records_combined))
                    skip_next = True
                    
                    print(f"合并小样本区间 {slot_idx}: {len(records)} 样本分配到相邻区间")
                elif idx == 0 and len(valid_slots) > 1:
                    # 第一个区间，全部给下一个
                    next_slot_idx, next_records = valid_slots[idx + 1]
                    next_records_combined = records + next_records
                    merged_slots.append((next_slot_idx, next_records_combined))
                    skip_next = True
                    print(f"合并第一个小样本区间 {slot_idx}: {len(records)} 样本分配到下一个区间")
                elif idx == len(valid_slots) - 1 and merged_slots:
                    # 最后一个区间，全部给前一个
                    merged_slots[-1] = (merged_slots[-1][0], merged_slots[-1][1] + records)
                    print(f"合并最后一个小样本区间 {slot_idx}: {len(records)} 样本分配到前一个区间")
                else:
                    # 孤立的小样本区间，保留
                    merged_slots.append((slot_idx, records))
            else:
                # 样本量足够，保留
                merged_slots.append((slot_idx, records))
        
        print(f"合并后有效时间段: {len(merged_slots)}")
        
        # 初始化结果（不包括空军）
        trend_data = {}
        for rarity in rarity_colors.keys():
            if rarity != 'airforce':
                trend_data[rarity] = {
                    'times': [],
                    'interval_probabilities': [],
                    'cumulative_probabilities': []
                }
        
        # 计算累积数据
        cumulative_counts = defaultdict(int)
        cumulative_total = 0
        
        for slot_idx, records in merged_slots:
            slot_time = time_slots[slot_idx]
            slot_total = len(records)
            
            # 统计当前区间的各稀有度数量
            rarity_counts = defaultdict(int)
            airforce_count = 0
            
            for record in records:
                if record['is_airforce']:
                    airforce_count += 1
                else:
                    rarity_counts[record['rarity']] += 1
            
            # 更新累积计数
            cumulative_total += slot_total
            for rarity in rarity_colors.keys():
                if rarity == 'airforce':
                    cumulative_counts[rarity] += airforce_count
                else:
                    cumulative_counts[rarity] += rarity_counts[rarity]
            
            # 保存数据
            # 保存数据（不包括空军）
            for rarity in trend_data.keys():
                trend_data[rarity]['times'].append(slot_time)
                
                # 区间内概率
                count = rarity_counts[rarity]
                interval_prob = (count / slot_total * 100) if slot_total > 0 else 0
                trend_data[rarity]['interval_probabilities'].append(interval_prob)
                
                # 累积概率
                cumulative_prob = (cumulative_counts[rarity] / cumulative_total * 100) if cumulative_total > 0 else 0
                trend_data[rarity]['cumulative_probabilities'].append(cumulative_prob)
        print("趋势数据计算完成")
        return trend_data

class FishingDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("钓鱼数据看板")
        self.root.geometry("1200x800")
        
        self.bg_color = "#f0f0f0"
        self.root.configure(bg=self.bg_color)
        
        print("初始化数据处理器...")
        self.data_processor = FishingDataProcessor()
        
        print("创建界面...")
        self.create_widgets()
        
        print("加载数据...")
        self.load_data()
        print("初始化完成")
    
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title_label = tk.Label(main_frame, text="钓鱼数据看板", font=("Arial", 24, "bold"),
                              bg=self.bg_color, fg="#333333")
        title_label.pack(pady=(0, 20))
        
        control_frame = tk.Frame(main_frame, bg=self.bg_color)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        refresh_button = tk.Button(control_frame, text="刷新数据", command=self.refresh_data,
                                  font=("Arial", 12), bg="#4CAF50", fg="white",
                                  activebackground="#45a049")
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 添加显示模式按钮
        self.show_interval_button = tk.Button(control_frame, text="只显示区间概率",
                                             command=lambda: self.set_display_mode('interval'),
                                             font=("Arial", 10), bg="#2196F3", fg="white",
                                             activebackground="#1976D2")
        self.show_interval_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.show_cumulative_button = tk.Button(control_frame, text="只显示累积概率",
                                              command=lambda: self.set_display_mode('cumulative'),
                                              font=("Arial", 10), bg="#FF9800", fg="white",
                                              activebackground="#F57C00")
        self.show_cumulative_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.show_both_button = tk.Button(control_frame, text="显示两者",
                                        command=lambda: self.set_display_mode('both'),
                                        font=("Arial", 10), bg="#9C27B0", fg="white",
                                        activebackground="#7B1FA2")
        self.show_both_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(control_frame, text="就绪", font=("Arial", 10),
                                    bg=self.bg_color, fg="#666666")
        self.status_label.pack(side=tk.LEFT)
        
        stats_frame = tk.LabelFrame(main_frame, text="统计信息", font=("Arial", 14, "bold"),
                                   bg=self.bg_color, fg="#333333")
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.stats_content = tk.Label(stats_frame, text="", font=("Arial", 12),
                                     bg=self.bg_color, justify=tk.LEFT)
        self.stats_content.pack(padx=10, pady=10)
        
        chart_frame = tk.LabelFrame(main_frame, text="稀有度趋势图（30分钟间隔）", font=("Arial", 14, "bold"),
                                   bg=self.bg_color, fg="#333333")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.patch.set_facecolor('white')
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 初始化显示模式
        self.display_mode = 'both'  # 'interval', 'cumulative', 'both'
    
    def set_display_mode(self, mode):
        """设置显示模式"""
        self.display_mode = mode
        self.update_trend_chart()
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def load_data(self):
        self.update_status("正在加载数据...")
        self.update_statistics()
        self.update_trend_chart()
        self.update_status("数据加载完成")
    
    def refresh_data(self):
        self.update_status("正在刷新数据...")
        self.data_processor = FishingDataProcessor()
        self.load_data()
    
    def update_statistics(self):
        self.update_status("正在计算统计信息...")
        stats = self.data_processor.get_statistics()
        
        stats_text = f"总样本量: {stats['total_records']}\n"
        stats_text += f"空军数: {stats['airforce_count']}  (空军率: {stats['airforce_rate']:.2f}%)\n\n"
        stats_text += "各稀有度统计:\n"
        
        rarity_order = ['legendary', 'epic', 'rare', 'extraordinary', 'standard']
        rarity_names = {
            'legendary': '传奇鱼',
            'epic': '史诗鱼',
            'rare': '稀有鱼',
            'extraordinary': '非凡鱼',
            'standard': '标准鱼'
        }
        
        for rarity in rarity_order:
            count = stats['fish_counts'].get(rarity, 0)
            percentage = stats['rarity_percentages'].get(rarity, 0)
            stats_text += f"  {rarity_names[rarity]}: {count}  ({percentage:.2f}%)\n"
        
        self.stats_content.config(text=stats_text)
    
    def update_trend_chart(self):
        self.update_status("正在生成趋势图...")
        self.ax.clear()

        trend_data = self.data_processor.get_rarity_trend_data()

        rarity_names = {
            'legendary': '传奇鱼',
            'epic': '史诗鱼',
            'rare': '稀有鱼',
            'extraordinary': '非凡鱼',
            'standard': '标准鱼'
        }

        has_data = False
        for rarity, data in trend_data.items():
            if not data['times']:
                continue
                
            has_data = True
            if self.display_mode in ['interval', 'both']:
                self.ax.plot(data['times'], data['interval_probabilities'],
                            color=rarity_colors[rarity], linewidth=2,
                            label=f"{rarity_names[rarity]} (区间概率)", linestyle='-')
            
            if self.display_mode in ['cumulative', 'both']:
                self.ax.plot(data['times'], data['cumulative_probabilities'],
                            color=rarity_colors[rarity], linewidth=1.5,
                            label=f"{rarity_names[rarity]} (累积概率)", linestyle='--', alpha=0.7)
        
        if not has_data:
            self.ax.text(0.5, 0.5, '暂无数据', transform=self.ax.transAxes,
                        ha='center', va='center', fontsize=16)
        else:
            # 根据显示模式设置标题
            if self.display_mode == 'interval':
                title = "稀有度出现概率走势 (区间概率)"
            elif self.display_mode == 'cumulative':
                title = "稀有度出现概率走势 (累积概率)"
            else:
                title = "稀有度出现概率走势"
                
            self.ax.set_title(title, fontsize=16, pad=20)
            self.ax.set_xlabel("时间", fontsize=12)
            self.ax.set_ylabel("概率 (%)", fontsize=12)
            self.ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
            self.ax.grid(True, alpha=0.3)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            self.fig.autofmt_xdate()
        
        self.canvas.draw()

def main():
    print("启动钓鱼数据看板...")
    root = tk.Tk()
    app = FishingDashboard(root)
    print("进入主循环...")
    root.mainloop()

if __name__ == "__main__":
    main()