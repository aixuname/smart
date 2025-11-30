import random
import time
import sys
import pygame
from midiutil import MIDIFile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

# ---------------------- 基础配置 ----------------------
NOTE_MAP = {
    '宫': 60, '商': 62, '角': 64, '徵': 67, '羽': 69
}
KEY_TO_NOTE = {'f': '宫', 'g': '商', 'h': '角', 'j': '徵', 'k': '羽'}
NOTE_TO_KEY = {v: k for k, v in KEY_TO_NOTE.items()}

# 初始化pygame音频（用于播放音符和音乐）
pygame.mixer.init()


# ---------------------- 音乐生成与播放工具函数 ----------------------
def generate_ancient_music():
    """生成古乐MIDI和标准按键序列"""
    melody_templates = [
        ['宫', '商', '角', '徵', '羽', '徵', '角', '商', '宫'],
        ['宫', '角', '徵', '羽', '徵', '角', '商', '角', '宫'],
        ['商', '角', '徵', '羽', '羽', '徵', '角', '商', '商']
    ]
    selected_melody = random.choice(melody_templates)
    key_sequence = [NOTE_TO_KEY[note] for note in selected_melody]

    # 生成MIDI文件
    track = 0
    channel = 0
    time_step = 0
    duration = 0.5
    tempo = 70
    volume = 100
    midi = MIDIFile(1)
    midi.addTempo(track, time_step, tempo)
    for note_name in selected_melody:
        midi.addNote(track, channel, NOTE_MAP[note_name], time_step, duration, volume)
        time_step += duration

    with open("ancient_music.mid", "wb") as f:
        midi.writeFile(f)
    return key_sequence


def play_single_note(note_name):
    """播放单个音符（非阻塞，避免卡界面）"""
    try:
        temp_midi = MIDIFile(1)
        temp_midi.addTempo(0, 0, 100)
        temp_midi.addNote(0, 0, NOTE_MAP[note_name], 0, 0.8, 100)
        with open("temp_note.mid", "wb") as f:
            temp_midi.writeFile(f)
        pygame.mixer.music.load("temp_note.mid")
        pygame.mixer.music.play()
        time.sleep(0.3)
        pygame.mixer.music.stop()
    except Exception as e:
        print(f"音符播放失败：{e}")


def play_ancient_music():
    """播放古乐（阻塞，确保播放完整）"""
    try:
        pygame.mixer.music.load("ancient_music.mid")
        pygame.mixer.music.play()
        time.sleep(5)
        pygame.mixer.music.stop()
        return True
    except Exception as e:
        print(f"古乐播放失败：{e}")
        return False


# ---------------------- 子线程：音乐播放（避免卡界面） ----------------------
class MusicPlayThread(QThread):
    """古乐播放子线程（防止主线程卡顿）"""
    play_finished = pyqtSignal(bool)  # 播放完成信号（成功/失败）

    def run(self):
        success = play_ancient_music()
        self.play_finished.emit(success)


# ---------------------- 主窗口类 ----------------------
class MusicGameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_game_state()

    def init_ui(self):
        """初始化窗口界面"""
        # 窗口配置
        self.setWindowTitle("暨南大学中华文化日 - 宫商角徵羽键盘音游")
        self.setFixedSize(2000, 1400)  # 固定窗口大小，适配摆摊展示
        self.setStyleSheet("background-color: #f5f5f0;")  # 米黄色背景，贴合传统文化氛围

        # 字体配置
        self.title_font = QFont("微软雅黑", 16, QFont.Bold)
        self.label_font = QFont("微软雅黑", 12)
        self.text_font = QFont("微软雅黑", 11)

        # 中心部件与布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 1. 标题区域
        title_label = QLabel("🎶 宫商角徵羽键盘音游 🎶")
        title_label.setFont(self.title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #8B4513;")  # 棕色文字，贴合传统文化
        main_layout.addWidget(title_label)

        # 2. 五音按键映射提示
        map_label = QLabel("五音对应：F=宫 | G=商 | H=角 | J=徵 | K=羽 | 结束操作：Esc键")
        map_label.setFont(self.label_font)
        map_label.setAlignment(Qt.AlignCenter)
        map_label.setStyleSheet("color: #333333; background-color: #e8e0d0; padding: 8px; border-radius: 5px;")
        main_layout.addWidget(map_label)

        # 3. 流程提示
        flow_label = QLabel("游戏流程：按键测试 → 聆听古乐 → 弹奏发声 → 系统评分")
        flow_label.setFont(self.label_font)
        flow_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(flow_label)

        # 4. 乐谱展示区
        self.score_label = QLabel("📜 标准乐谱：等待生成...")
        self.score_label.setFont(self.label_font)
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet(
            "background-color: white; padding: 10px; border: 2px solid #8B4513; border-radius: 5px;")
        main_layout.addWidget(self.score_label)

        # 5. 互动日志区（显示测试、弹奏记录）
        self.log_text = QTextEdit()
        self.log_text.setFont(self.text_font)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: white; border: 1px solid #cccccc; border-radius: 5px;")
        self.log_text.setPlaceholderText("互动记录将显示在这里...")
        main_layout.addWidget(self.log_text, 1)  # 占1份权重，自动拉伸

        # 6. 功能按钮区（水平布局）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        # 开始测试按钮
        self.test_btn = QPushButton("🎹 开始按键测试")
        self.test_btn.setFont(self.label_font)
        self.test_btn.setStyleSheet(
            "background-color: #D2B48C; color: white; padding: 10px 20px; border: none; border-radius: 5px;")
        self.test_btn.clicked.connect(self.start_key_test)
        btn_layout.addWidget(self.test_btn)

        # 播放古乐按钮（初始禁用，测试后启用）
        self.play_music_btn = QPushButton("🎵 播放古乐")
        self.play_music_btn.setFont(self.label_font)
        self.play_music_btn.setStyleSheet(
            "background-color: #A0522D; color: white; padding: 10px 20px; border: none; border-radius: 5px;")
        self.play_music_btn.clicked.connect(self.start_play_music)
        self.play_music_btn.setEnabled(False)
        btn_layout.addWidget(self.play_music_btn)

        # 开始弹奏按钮（初始禁用，播放音乐后启用）
        self.play_btn = QPushButton("🎶 开始弹奏")
        self.play_btn.setFont(self.label_font)
        self.play_btn.setStyleSheet(
            "background-color: #CD853F; color: white; padding: 10px 20px; border: none; border-radius: 5px;")
        self.play_btn.clicked.connect(self.start_play)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)

        # 重新开始按钮
        self.restart_btn = QPushButton("🔄 重新开始")
        self.restart_btn.setFont(self.label_font)
        self.restart_btn.setStyleSheet(
            "background-color: #8B4513; color: white; padding: 10px 20px; border: none; border-radius: 5px;")
        self.restart_btn.clicked.connect(self.restart_game)
        btn_layout.addWidget(self.restart_btn)

        main_layout.addLayout(btn_layout)

        # 7. 评分展示区
        self.score_display = QLabel("🏆 你的得分：等待弹奏...")
        self.score_display.setFont(self.title_font)
        self.score_display.setAlignment(Qt.AlignCenter)
        self.score_display.setStyleSheet("color: #8B4513; padding: 10px;")
        main_layout.addWidget(self.score_display)

    def init_game_state(self):
        """初始化游戏状态"""
        self.test_completed = False  # 按键测试是否完成
        self.music_played = False  # 古乐是否播放完成
        self.is_playing = False  # 是否处于弹奏状态
        self.standard_seq = []  # 标准按键序列
        self.player_seq = []  # 玩家弹奏序列

    def append_log(self, text):
        """向日志区添加内容"""
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {text}")
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def start_key_test(self):
        """开始按键测试"""
        self.append_log("=== 按键测试开始！按F/G/H/J/K键试听五音，按Esc键结束测试 ===")
        self.test_btn.setEnabled(False)
        self.test_completed = False
        # 启用键盘监听（PyQt5自带的键盘事件）
        self.setFocusPolicy(Qt.StrongFocus)  # 获取焦点，才能监听键盘

    def start_play_music(self):
        """播放古乐（子线程执行，避免卡界面）"""
        if not self.test_completed:
            QMessageBox.warning(self, "提示", "请先完成按键测试！")
            return

        self.append_log("=== 开始播放古乐，请仔细聆听并记忆乐谱 ===")
        self.play_music_btn.setEnabled(False)
        self.play_btn.setEnabled(False)

        # 生成古乐和标准乐谱
        self.standard_seq = generate_ancient_music()
        standard_str = " → ".join([k.upper() for k in self.standard_seq])
        self.score_label.setText(f"📜 标准乐谱已生成：")
        self.append_log(f"标准乐谱已生成")
        # self.score_label.setText(f"📜 标准乐谱：{standard_str}")
        # self.append_log(f"标准乐谱已生成：{standard_str}")

        # 启动子线程播放音乐
        self.music_thread = MusicPlayThread()
        self.music_thread.play_finished.connect(self.on_music_play_finished)
        self.music_thread.start()

    def on_music_play_finished(self, success):
        """古乐播放完成回调"""
        if success:
            self.append_log("=== 古乐播放完成！可以开始弹奏了 ===")
            self.music_played = True
            self.play_btn.setEnabled(True)
        else:
            self.append_log("=== 古乐播放失败，请手动打开ancient_music.mid文件聆听 ===")
            QMessageBox.warning(self, "警告", "古乐播放失败，请手动打开ancient_music.mid文件！")
            self.play_btn.setEnabled(True)  # 即使播放失败，也允许弹奏

    def start_play(self):
        """开始弹奏"""
        if not self.music_played:
            QMessageBox.warning(self, "提示", "请先播放古乐！")
            return

        self.append_log("=== 弹奏开始！按乐谱顺序按F/G/H/J/K键（按键发声），按Esc键结束弹奏 ===")
        self.play_btn.setEnabled(False)
        self.is_playing = True
        self.player_seq = []  # 清空之前的弹奏记录
        self.setFocusPolicy(Qt.StrongFocus)  # 确保窗口获取键盘焦点

    def calculate_score(self):
        """计算得分"""
        if not self.standard_seq:
            return 0

        min_len = min(len(self.standard_seq), len(self.player_seq))
        correct_count = sum([1 for s, p in zip(self.standard_seq[:min_len], self.player_seq[:min_len]) if s == p])
        match_score = (correct_count / len(self.standard_seq)) * 70

        len_diff = abs(len(self.player_seq) - len(self.standard_seq))
        rhythm_score = max(0, 30 - len_diff * 5)

        return round(match_score + rhythm_score, 1)

    def show_score(self):
        """展示评分结果"""
        score = self.calculate_score()
        player_str = " → ".join([k.upper() for k in self.player_seq]) if self.player_seq else "未按键"
        standard_str = " → ".join([k.upper() for k in self.standard_seq])

        self.score_display.setText(f"🏆 你的得分：{score}分")
        self.append_log(f"=== 弹奏结束！评分结果 ===")
        self.append_log(f"标准乐谱：{standard_str}")
        self.append_log(f"你的弹奏：{player_str}")
        self.append_log(f"最终得分：{score}分")

        # 等级判断
        if score >= 90:
            level = "🏆 知音级！你对古乐节奏把握精准，堪称中华音乐小达人～"
        elif score >= 70:
            level = "🥈 熟练级！节奏和旋律都不错，稍加练习就是古乐高手～"
        elif score >= 50:
            level = "🥉 入门级！已经掌握五音规律，多听多练就能更熟练～"
        else:
            level = "🌟 潜力级！再听一遍音乐，相信你能弹得更好～"

        self.append_log(f"等级评定：{level}")
        QMessageBox.information(self, "评分结果", f"你的得分：{score}分\n{level}")

    def restart_game(self):
        """重新开始游戏"""
        self.init_game_state()
        self.score_label.setText("📜 标准乐谱：等待生成...")
        self.score_display.setText("🏆 你的得分：等待弹奏...")
        self.log_text.clear()
        self.test_btn.setEnabled(True)
        self.play_music_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.append_log("=== 游戏已重新开始，请点击「开始按键测试」启动流程 ===")

    # ---------------------- 键盘事件监听（核心：测试和弹奏的按键响应） ----------------------
    def keyPressEvent(self, event):
        """监听键盘按键事件"""
        key = event.key()
        key_char = chr(key).lower() if key >= Qt.Key_A and key <= Qt.Key_Z else None

        # 1. 测试环节的按键响应
        if not self.test_completed and not self.is_playing:
            if key_char in KEY_TO_NOTE.keys():
                note_name = KEY_TO_NOTE[key_char]
                self.append_log(f"✅ 按了【{key_char.upper()}】键，对应五音【{note_name}】")
                play_single_note(note_name)  # 播放对应音符
            elif key == Qt.Key_Escape:
                self.append_log("=== 按键测试结束！可以播放古乐了 ===")
                self.test_completed = True
                self.play_music_btn.setEnabled(True)

        # 2. 弹奏环节的按键响应
        elif self.is_playing:
            if key_char in KEY_TO_NOTE.keys():
                note_name = KEY_TO_NOTE[key_char]
                self.player_seq.append(key_char)
                self.append_log(f"🎹 弹奏：【{key_char.upper()}】（五音：{note_name}）")
                play_single_note(note_name)  # 弹奏发声
            elif key == Qt.Key_Escape:
                self.is_playing = False
                self.show_score()  # 结束弹奏，展示评分


# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MusicGameWindow()
    window.show()
    try:
        sys.exit(app.exec_())
    finally:
        # 程序结束时清理pygame资源
        pygame.mixer.quit()