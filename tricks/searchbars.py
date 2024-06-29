from PIL.ImageQt            import ImageQt, QImage
from PyQt6                  import QtCore, QtGui, QtWidgets
from PyQt6.QtGui            import QFont, QFontMetrics
from tricks.database        import Pastes
from tricks.smartpos        import pos
from tricks.styles          import copy_stylesheet, style
from tricks.threadpool      import ThreadThenMain
from tricks.widget_drawings import bordered_crackling_background
from tricks.widgets         import Base
import time

class SearchBar(QtWidgets.QLineEdit):
    def __init__(self, master, *args, **kwargs):
        self.master: Base = master
        super().__init__(master, *args, **kwargs)
        self.setReadOnly(True)
        font: QFont = QFont('monospace')
        self.setFont(font)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.setContentsMargins(5, 0, 0, 0)
        style(self, background='transparent', color='black', border='transparent', font=14, weight=500)
        self.show()

    def keyPressEvent(self, *args):
        self.setReadOnly(False)
        super().keyPressEvent(*args)
        self.setReadOnly(True)

    def text_size(self) -> tuple:
        text: str = self.text()
        font: QFont = self.font()
        metrics: QFontMetrics = QtGui.QFontMetrics(font)
        bound = metrics.boundingRect(text)
        return bound.width(), bound.height()

    def text_height(self) -> int:
        _, height = self.text_size()
        return height

    def text_width(self) -> int:
        width, _ = self.text_size()
        return width

    def text_changed(self, *args, **kwargs):
        text: str = self.text()
        try:
            self.shade.setText(text)
        except AttributeError:

            if text:
                self.shade: SearchBar = SearchBar(self.master, text=text)
                self.shade.keyPressEvent = lambda *args: None
                self.shade.lower()

                pos(self.shade, size=self, sub=4, left=1, top=3)
                copy_stylesheet(self.shade, self, color='rgba(220, 220, 220, 225)')

        if (self.text_width() + 10) > self.width():
            self.shade.hide()
        else:
            self.shade.show()

class CompleteSearchBar(Base):

    def init_draw(self):
        self.searchbar = SearchBar(self)
        cursor = QtGui.QCursor()
        beam_shape = QtCore.Qt.CursorShape(4)
        cursor.setShape(beam_shape)
        self.searchbar.setCursor(cursor)
        pos(self.searchbar, size=self, sub=4, left=2, top=2)

        from tricks.buttons import Button

        w: int = self.width()
        h: int = self.height()
        background: tuple = Button.col_background_idle
        border: tuple = Button.col_border_idle
        im, draw = bordered_crackling_background(w, h, background=background, border=border, bw=2)

        imqt = ImageQt(im)
        qim = QImage(imqt)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)

        self.searchbar.textChanged.connect(self.searchbar.text_changed)


class LeftSearchBar(CompleteSearchBar):
    next_search: float = time.time() + 86400.0
    runner: bool = False
    keypress_idle: float = 1.0

    def init_draw(self):
        super().init_draw()
        self.searchbar.textChanged.connect(self.search_titles)

    def search_titles(self):
        self.next_search = (time.time() + self.keypress_idle)
        if not self.runner:
            self.runner = True
            try:
                self.thread_then_main
            except AttributeError:
                self.thread_then_main = ThreadThenMain()

            self.thread_then_main(wait=self.keypress_idle, main_fn=self.thread_knock_knock)

    def thread_knock_knock(self):
        if time.time() < self.next_search:
            wait: float = (self.next_search - time.time())
            wait = min(wait, self.keypress_idle)
            wait = max(wait, 0.1)
            self.thread_then_main(wait=wait, main_fn=self.thread_knock_knock)
            return

        self.runner = False
        try:
            widgets: list = self.master.shelf.scrollarea.widgets
            text: str = self.searchbar.text().strip()
            texts: set = set(text.lower().split()) if text else set()
        except AttributeError:
            return

        widgets.sort(key=lambda x: x.paste[Pastes.date], reverse=True)
        tops: list = [x.geometry().top() for x in widgets]
        tops.sort()

        if texts:
            head: list = []
            tail: list = []
            for w in widgets:
                lowcaps_title: str = w.paste[Pastes.title].lower()
                for text in texts:
                    if text not in lowcaps_title:
                        tail.append(w)
                        break
                else:
                    head.append(w)
            ordered_widgets: list = head + tail
        else:
            ordered_widgets: list = widgets

        rescrolling_needed: bool = False
        for widget, top in zip(ordered_widgets, tops):
            rescrolling_needed: bool = rescrolling_needed or (widget.geometry().top() != top)
            pos(widget, top=top)

        if rescrolling_needed:
            self.master.shelf.scrollarea.scroller.show_scroller()
            min_top: int = self.master.shelf.scrollarea.scroller.get_min_top()
            pos(self.master.shelf.scrollarea.canvas, top=min_top)

        if self.master.searchbar_credentials():
            if 'settings_helper' not in dir(self.master):
                self.master.show_missing_setting_helper(override=True)



class RightTitleBar(CompleteSearchBar):
    ...

