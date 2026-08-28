from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

class MarqueeLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)

        self.text = text
        self.offset = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scroll_text)
        self.timer.start(30)

    def scroll_text(self):
        self.offset -= 1

        if self.offset < -self.text_width():
            self.offset = self.width()

        self.update()

    def text_width(self):
        return self.fontMetrics().horizontalAdvance(self.text)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setPen(Qt.GlobalColor.black)

        painter.drawText(
            self.offset,
            self.height() // 2,
            self.text
        )
