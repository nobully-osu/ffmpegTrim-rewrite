version = "v2.0.0-alpha"
import sys
from configparser import ConfigParser
from pathlib import Path

from ffmpegTrim import parse_timecode, get_output_path

from PySide6.QtCore import (
    Qt, QProcess, QUrl
)

from PySide6.QtGui import (
    QActionGroup, QTextCursor, QDesktopServices
)

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QFileDialog, QDialog,
    QLabel,
    QVBoxLayout, QHBoxLayout,
    QLineEdit, QPlainTextEdit,
    QWidget,
    QPushButton,
    QProgressBar
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # import config
        self.config = ConfigParser()
        self.config.read("config.ini")

        # ffmpeg process definition
        self.ffmpeg_process = QProcess()

        # window settings
        self.setWindowTitle(f"ffmpegTrimQt {version}")
        self.resize(800, 600)

        self.default_theme = self.config.get("qt", "default-theme")
        self.load_theme(Path(__file__).parent / "themes" / f"{self.default_theme}.qss")

        # ui elements
        self.setup_ui()
        self.setup_menubar()

        # connections
        self.setup_connections()

    # helper functions
    def setup_ui(self):
        main_layout = QVBoxLayout()

        # file picker
        target_layout = QHBoxLayout()

        target_label = QLabel("Target:")
        self.path_line_edit = QLineEdit()
        self.browse_button = QPushButton("Browse...")

        target_layout.addWidget(target_label)
        target_layout.addWidget(self.path_line_edit)
        target_layout.addWidget(self.browse_button)

        # timestamp entry
        time_layout = QHBoxLayout()

        self.start_time_line_edit = QLineEdit()
        self.start_time_line_edit.setPlaceholderText("hh:mm:ss.mmm")

        to_label = QLabel("to")

        self.end_time_line_edit = QLineEdit()
        self.end_time_line_edit.setPlaceholderText("hh:mm:ss.mmm")

        time_layout.addWidget(self.start_time_line_edit)
        time_layout.addWidget(to_label)
        time_layout.addWidget(self.end_time_line_edit)

        # buttons
        start_button_layout = QHBoxLayout()

        self.clear_button = QPushButton("Clear")
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("startButton")

        start_button_layout.addWidget(self.clear_button)
        start_button_layout.addWidget(self.start_button)

        # progress bar + output console
        output_layout = QVBoxLayout()

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        output_layout.addWidget(self.progress)
        output_layout.addWidget(self.console)

        # main window layout
        main_layout.addLayout(target_layout)
        main_layout.addLayout(time_layout)
        main_layout.addLayout(start_button_layout)
        main_layout.addLayout(output_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)

    def setup_connections(self):
        self.browse_button.clicked.connect(self.browse_file)
        self.clear_button.clicked.connect(self.clear_line_edits)
        self.start_button.clicked.connect(self.run_ffmpeg)

        self.ffmpeg_process.started.connect(self.ffmpeg_started)
        self.ffmpeg_process.finished.connect(self.ffmpeg_finished)

        self.ffmpeg_process.readyReadStandardOutput.connect(
            self.read_process_output
        )

        self.ffmpeg_process.readyReadStandardError.connect(
            self.read_process_error
        )

    # menu bar setup
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

    def open_config(self):
        config_path = Path(__file__).parent / "config.ini"

        QDesktopServices.openUrl(QUrl.fromLocalFile(config_path))

    def setup_theme_menu(self):
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        theme_directory = Path(__file__).parent / "themes"

        for theme_path in theme_directory.glob("*.qss"):
            action = self.theme_menu.addAction(theme_path.stem)

            action.setCheckable(True)
            theme_group.addAction(action)

            if theme_path.stem == self.default_theme:
                action.setChecked(True)

            action.triggered.connect(
                lambda checked=False, path=theme_path:
                self.load_theme(path)
            )

    def setup_help_menu(self):
        about_action = self.help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def load_theme(self, theme_path):
        with open(theme_path, "r", encoding="utf-8") as theme:
            stylesheet = theme.read()

        QApplication.instance().setStyleSheet(stylesheet)

    # connection helper functions
    def browse_file(self):
        default_path = self.config.get(
            "qt",
            "default-path",
            fallback=str(Path.home())
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            default_path,
            "Video Files (*.mp4 *.mkv *.mov *.avi);;All Files (*)"
        )

        if file_path:
            self.path_line_edit.setText(file_path)

    def clear_line_edits(self):
        self.path_line_edit.clear()
        self.start_time_line_edit.clear()
        self.end_time_line_edit.clear()

    def run_ffmpeg(self):
        self.console.clear()

        audio_codec     = self.config.get("audio", "codec")
        audio_quality   = self.config.get("audio", "quality")
        video_codec     = self.config.get("video", "codec")
        video_quality   = self.config.get("video", "quality")
        cpu_preset      = self.config.get("video", "preset")
        file_extension  = self.config.get("video", "extension")

        input_path = Path(self.path_line_edit.text())
        if not input_path.is_file():
            self.console.appendPlainText("Invalid target video path.")
            return

        output_path = get_output_path(str(input_path.with_suffix("")), file_extension)

        start_time = self.start_time_line_edit.text()
        end_time = self.end_time_line_edit.text()

        try:
            self.duration = parse_timecode(end_time) - parse_timecode(start_time)
        except ValueError as error:
            self.console.appendPlainText(f"Invalid timecode: {error}")
            return

        video_args = (
            ["-c:v", "copy"]
            if video_codec == "copy"
            else ["-c:v", video_codec, "-preset", cpu_preset, "-crf", video_quality]
        )

        audio_args = (
            ["-c:a", "copy"]
            if audio_codec == "copy"
            else ["-c:a", audio_codec, "-b:a", audio_quality]
        )

        container_args = (
            ["-movflags", "+faststart"]
            if file_extension.lower() in ("mp4", "mov", "m4a")
            else []
        )

        args = [
            "-i", str(input_path),
            "-ss", start_time,
            "-t", str(self.duration),
            *video_args,
            *audio_args,
            *container_args,
            "-progress", "pipe:1",
            output_path
        ]

        self.ffmpeg_process.start(
            "ffmpeg", args
        )

    def ffmpeg_started(self):
        self.progress.setValue(0)
        self.start_button.setText("Running...")
        self.start_button.setEnabled(False)
        self.console.appendPlainText("ffmpeg started...\n")

    def ffmpeg_finished(self):
        QApplication.beep()
        self.progress.setValue(100)
        self.start_button.setText("Start")
        self.start_button.setEnabled(True)
        self.console.appendPlainText("ffmpeg finished.\n")

    def read_process_output(self):
        output = self.ffmpeg_process.readAllStandardOutput().data().decode(
            "utf-8",
            errors="replace"
        )

    def read_process_error(self):
        output = self.ffmpeg_process.readAllStandardError().data().decode(
            "utf-8",
            errors="replace"
        )
        self.append_console(output)

    def append_console(self, output):
        self.console.appendPlainText(output.rstrip())
        self.console.moveCursor(QTextCursor.MoveOperation.End)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(f"About ffmpegTrimQt {version}")

        layout = QVBoxLayout(self)

        label = QLabel(f"★ Welcome to ffmpegTrimQt {version} ★\nBest viewed at 800x600\nPowered by FFmpeg\n",
                       alignment=Qt.AlignmentFlag.AlignCenter)

        ok_button = QPushButton("Ok")
        ok_button.setMaximumWidth(64)
        ok_button.clicked.connect(self.accept)

        layout.addWidget(label)
        layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)


def main():
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
