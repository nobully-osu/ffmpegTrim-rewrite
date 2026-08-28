import sys, re
from configparser import ConfigParser
from pathlib import Path

import ffmpegTrim
from ffmpegTrim import parse_timecode, get_output_path
from widgets.marquee_label import MarqueeLabel

from PySide6.QtCore import (
    Qt,
    QProcess
)

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QFileDialog,
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QWidget,
    QPushButton,
    QPlainTextEdit,
    QProgressBar
)

from PySide6.QtGui import (
    QActionGroup, QTextCursor
)

version = "v1.0.0"

def load_theme(theme_path):
    with open(theme_path, "r", encoding="utf-8") as file:
        stylesheet = file.read()

    QApplication.instance().setStyleSheet(stylesheet)

class MainWindow(QMainWindow):
    def __init__(self, /):
        super().__init__()

        self.config = ConfigParser()
        self.config.read("config.ini")

        self.setWindowTitle(f"ffmpegTrimQt {version}")
        self.resize(800, 600)

        self.process = QProcess(self)
        self.stderr_buffer = ""

        self.setup_ui()
        self.setup_menubar()
        self.setup_connections()

        if not Path(__file__) / "config.ini":
            ffmpegTrim.setup()

        load_theme(Path(__file__).parent / "themes" / "win9x.qss")

    def setup_ui(self):
        main_layout = QVBoxLayout()

        # -------------------------------------------------
        # File picker
        # -------------------------------------------------

        target_layout = QHBoxLayout()

        target_label = QLabel("Target:")

        self.path_line_edit = QLineEdit()

        self.browse_button = QPushButton("Browse...")

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.path_line_edit)
        target_layout.addWidget(self.browse_button)

        # -------------------------------------------------
        # Timestamp entry
        # -------------------------------------------------

        time_layout = QHBoxLayout()

        self.start_time_line_edit = QLineEdit()
        self.start_time_line_edit.setPlaceholderText("hh:mm:ss.mmm")

        to_label = QLabel("to")

        self.end_time_line_edit = QLineEdit()
        self.end_time_line_edit.setPlaceholderText("hh:mm:ss.mmm")

        time_layout.addWidget(self.start_time_line_edit)
        time_layout.addWidget(to_label)
        time_layout.addWidget(self.end_time_line_edit)

        # -------------------------------------------------
        # Start and clear buttons
        # -------------------------------------------------

        start_button_layout = QHBoxLayout()

        self.clear_button = QPushButton("Clear")
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("startButton")

        start_button_layout.addWidget(self.clear_button)
        start_button_layout.addWidget(self.start_button)

        # -------------------------------------------------
        # Console output and progress bar
        # -------------------------------------------------

        output_layout = QVBoxLayout()

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        output_layout.addWidget(self.progress)
        output_layout.addWidget(self.console)

        # -------------------------------------------------
        # Main window layout
        # -------------------------------------------------

        main_layout.addLayout(target_layout)
        main_layout.addLayout(time_layout)
        main_layout.addLayout(start_button_layout)
        main_layout.addLayout(output_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)

    def setup_menubar(self):
        menu_bar = self.menuBar()

        self.file_menu = menu_bar.addMenu("File")
        self.setup_file_menu()
        self.theme_menu = menu_bar.addMenu("Themes")
        self.setup_theme_menu()
        self.help_menu = menu_bar.addMenu("Help")
        self.setup_help_menu()

    def setup_file_menu(self):
        open_config_action = self.file_menu.addAction("Open config.ini")
        exit_action = self.file_menu.addAction("Exit")

        open_config_action.triggered.connect(self.open_config)
        exit_action.triggered.connect(sys.exit)

    def setup_theme_menu(self):
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        theme_directory = Path(__file__).parent / "themes"
        default_theme = "win9x"

        for theme_path in theme_directory.glob("*.qss"):
            action = self.theme_menu.addAction(theme_path.stem)

            action.setCheckable(True)
            theme_group.addAction(action)

            if theme_path.stem == default_theme:
                action.setChecked(True)

            action.triggered.connect(
                lambda checked=False, path=theme_path:
                load_theme(path)
            )

    def setup_help_menu(self):
        about_action = self.help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)

    def read_process_output(self):
        output = self.process.readAllStandardOutput().data().decode(
            "utf-8",
            errors="replace"
        )
        self.append_console(output)

    def read_process_error(self):

        data = self.process.readAllStandardError()
        text = data.data().decode(
            "utf-8",
            errors="replace"
        )

        self.append_console(text)
        self.stderr_buffer += text

        while "\n" in self.stderr_buffer or "\r" in self.stderr_buffer:
            match = re.search(r"[\r\n]", self.stderr_buffer)

            if not match:
                break

            line = self.stderr_buffer[:match.start()]
            self.stderr_buffer = self.stderr_buffer[match.end():]

            self.parse_ffmpeg_line(line)

    def parse_ffmpeg_line(self, line):
        match = re.search(
            r"time=(\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
            line
        )

        if match:
            timecode = match.group(1)
            elapsed = parse_timecode(timecode)

            progress_percent = elapsed / self.duration * 100
            self.progress.setValue(progress_percent)

    def append_console(self, output):
        self.console.appendPlainText(output.rstrip())
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def setup_connections(self):
        self.browse_button.clicked.connect(self.browse_file)
        self.clear_button.clicked.connect(self.clear_line_edits)
        self.start_button.clicked.connect(self.run_ffmpeg)

        self.process.started.connect(self.process_started)
        self.process.finished.connect(self.process_finished)

        self.process.readyReadStandardOutput.connect(
            self.read_process_output
        )

        self.process.readyReadStandardError.connect(
            self.read_process_error
        )

    def browse_file(self):
        default_path = self.config.get(
            "main",
            "default-path",
            fallback=str(Path.home())
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video",
            default_path,
            "Video Files (*.mp4 *.mkv *.mov *.avi);;All Files (*)"
        )

        if file_path:
            self.path_line_edit.setText(file_path)

    def run_ffmpeg(self):
        self.console.clear()

        audio_codec = self.config.get("main", "audio")
        video_codec = self.config.get("main", "video")
        preset = self.config.get("main", "preset")
        file_extension = self.config.get("main", "extension")

        input_path = Path(self.path_line_edit.text())
        if not input_path.is_file():
            self.console.appendPlainText("Invalid file path.")
            return

        temp_path = input_path.with_suffix("")
        start_time = self.start_time_line_edit.text()
        end_time = self.end_time_line_edit.text()

        try:
            start_time_seconds = parse_timecode(start_time)
            end_time_seconds = parse_timecode(end_time)
            self.duration = end_time_seconds - start_time_seconds
        except ValueError as error:
            self.console.appendPlainText(f"Invalid timecode: {error}")
            self.console.appendPlainText("Please ensure timecode is in correct format.")
            return

        output_path = get_output_path(str(temp_path), file_extension)

        arguments = [
            "-i", str(input_path),
            "-ss", start_time,
            "-t", str(self.duration),
            "-c:v", video_codec,
            "-preset", preset,
            "-c:a", audio_codec,
            output_path
        ]

        self.process.start("ffmpeg", arguments)

    def clear_line_edits(self):
        self.path_line_edit.clear()
        self.start_time_line_edit.clear()
        self.end_time_line_edit.clear()

    def process_started(self):
        self.start_button.setText("Running...")
        self.start_button.setEnabled(False)
        self.progress.setValue(0)

    def process_finished(self):
        QApplication.beep()
        self.start_button.setText("Start")
        self.start_button.setEnabled(True)
        self.progress.setValue(100)

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def open_config(self):
        config_path = Path(__file__).parent / "config.ini"

        QProcess.startDetached(
            "notepad.exe",
            [str(config_path)]
        )

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"About ffmpegTrimQt {version}")
        self.resize(256, 64)

        layout = QVBoxLayout(self)

        marquee = MarqueeLabel(f"★ Welcome to ffmpegTrimQt {version} ★  |  Best viewed at 800x600  |  Powered by FFmpeg")
        marquee.setFixedHeight(20)

        ok_button = QPushButton("Ok")
        ok_button.setMaximumWidth(64)
        ok_button.clicked.connect(self.accept)

        layout.addWidget(marquee)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)

def main():
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()