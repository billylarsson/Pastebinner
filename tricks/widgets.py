from PIL                   import Image, ImageDraw
from PIL.ImageQt           import ImageQt
from PyQt6                 import QtCore, QtGui
from PyQt6.QtGui           import QFont, QFontMetrics
from PyQt6.QtWidgets       import QLabel
from tricks.database       import Pastes, db
from tricks.datetools      import epoch_to_date
from tricks.gpgthings      import decrypt_armor
from tricks.pastebin_api   import delete_paste, download_paste
from tricks.privacy_images import grabimages
from tricks.smartpos       import *
from tricks.styles         import *
from tricks.techs          import tmpdir
import io, time, typing, zipfile


def add(
        val: [int | float],
        factor: float = 0.0,
        min_add: int = 1,
        max_add: int = 255,
        min_val: int = 0,
        max_val: int = 255,
) -> int:
    if factor == 0.0:
        add_val: int = min_add
    else:
        add_val: int = int(val * factor)

    add_val = min(add_val, max_add)
    add_val = max(min_add, add_val)

    v: int = int(val) + add_val

    v = min(max_val, v)
    v = max(v, min_val)
    return v


def sub(
        val: [int | float],
        factor: float = 0.0,
        min_sub: int = 1,
        max_sub: int = 255,
        min_val: int = 0,
        max_val: int = 255,
) -> int:
    if factor == 0.0:
        sub_val: int = min_sub
    else:
        sub_val: int = int(val * factor)

    sub_val = min(sub_val, max_sub)
    sub_val = max(min_sub, sub_val)

    v: int = int(val) - sub_val

    v = min(max_val, v)
    v = max(v, min_val)
    return v

def rests_rgba_dict(start_rgba: tuple, end_rgba: tuple, lenght: int) -> dict:
    rests: dict = {}
    for count, key in enumerate('rgba'):
        start_val: int = start_rgba[count]
        end_val: int = end_rgba[count]
        fn = add if start_val < end_val else sub if end_val < start_val else lambda args, kwargs: None
        try:
            ppp: float = abs(start_val - end_val) / lenght
        except ZeroDivisionError:
            ppp: float = 0.01

        rests[key] = dict(
            val=start_val,
            start_val=start_val,
            end_val=end_val,
            ppp=ppp,
            rest=0.0,
            fn=fn,
        )
    return rests

class Base(QLabel):
    def __init__(self, master, monospace: bool = False, *args, **kwargs):
        self.master = master
        self.monospace = monospace
        super().__init__(master, *args, **kwargs)

        if monospace:
            font: QFont = QFont('monospace')
            self.setFont(font)

        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.show()


class TextLabel(Base):
    border_width: int = 2
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

    def get_proper_font_size(self, text: [str | None] = None) -> int:
        btn_w: int = self.width()
        btn_h: int = self.height()
        key: str = f'w:{btn_w} h:{btn_h}'
        try:
            return self.master._height_fontsize[key]
        except (AttributeError, KeyError) as Error:

            if isinstance(Error, AttributeError):
                self.master._height_fontsize = {}

            text: str = text or self.text()
            font_size: int = 6

            while font_size < 48:
                font: QFont = self.font()
                font.setPixelSize(font_size)
                self.setFont(font)
                metrics = QtGui.QFontMetrics(font)
                height: int = metrics.boundingRect(text).height()
                if height > btn_h - ((self.border_width * 2) + 10):
                    break

                font_size += 1

            self.master._height_fontsize[key]: int = font_size
            return font_size

    def set_proper_font_size(self, *args, **kwargs):
        font_size: int = self.get_proper_font_size(*args, **kwargs)
        style(self, font=font_size)

    def get_proper_text(self, text: [str | None] = None, edge: [int | None] = None) -> str:
        work_edge: int = edge or self.border_width
        work_text: str = text or self.text()
        font: QFont = self.font()
        metrics = QtGui.QFontMetrics(font)
        width: int = metrics.boundingRect(work_text).width()
        margin: int = self.contentsMargins().left()
        while len(work_text) > 3 and (width + work_edge + margin) > self.width():
            work_text = f'{work_text[:-3]}..'
            width = metrics.boundingRect(work_text).width()

        return work_text

    def set_proper_text(self, *args, **kwargs):
        new_text: str = self.get_proper_text(*args, **kwargs)
        self.setText(new_text)

class ShadedTextLabel(TextLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shade = self.Shade(self.master, monospace=self.master.monospace)
        pos(self.shade, size=[0, 0])
        self.raise_()

    def set_proper_text(self, *args, **kwargs):
        super().set_proper_text(*args, **kwargs)
        self.shade.mimic()

    class Shade(Base):
        def mimic(self):
            pos(self, size=self.master, left=-1, top=1)
            copy_stylesheet(self, self.master.text_label)
            style(self, color='rgba(250,250,250,150)')
            text: str = self.master.text_label.text()
            self.setText(text)

class DragAndDropper(Base):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, a0):
        if a0.buttons().value == 1:
            for url_data in a0.mimeData().urls():
                if url_data.isLocalFile():
                    a0.accept()
                    return

    def dropEvent(self, a0):
        for url_data in a0.mimeData().urls():
            if url_data.isLocalFile():
                path: str = url_data.path()
                self.save_to_database_show_image(path)

    def save_to_database_show_image(self, path: str, apply_to_all: bool = True):
        thumb_size: tuple[int, int] = self.width(), self.height(),
        try:
            im: Image.Image = Image.open(path)
            im = im.resize(thumb_size, resample=Image.Resampling.LANCZOS)
        except:
            return

        priv_var: str = self.master.priv_trans[self.master.paste[Pastes.private]]
        db.save_image(priv_var, im=im, w=im.width, h=im.height, quality=100)

        imqt: ImageQt = ImageQt(im)
        qim: QtGui.QImage = QtGui.QImage(imqt)
        pixmap: QtGui.QPixmap = QtGui.QPixmap.fromImage(qim)

        # simply showing the new pixmap in the dragdrop label for all (or self only), not perfect not critical
        if apply_to_all:
            widgets: list = self.master.master.master.widgets
            for paste in widgets:
                if paste.paste[Pastes.private] == self.master.paste[Pastes.private]:
                    paste.drag_and_drop_label.setPixmap(pixmap)
        else:
            self.setPixmap(pixmap)


class ScrollerThingey(Base):
    recent_size: tuple[int, int] = -1, -1
    holding: bool = False
    handle: int = 0

    def __init__(self, master, width: int, height: int, x_offset: int = 0, y_offset: int = 0):
        super().__init__(master)
        self.x_offset: int = x_offset
        self.y_offset: int = y_offset
        pos(self, size=[width, height])

    def change_look(self):
        size: tuple[int, int] = self.width(), self.height()
        im = Image.new('RGBA', size, (0, 0, 0, 255))
        draw = ImageDraw.Draw(im)

        x1, x2, y1, y2 = 0, im.width - 1, 0, im.height - 1
        r: int = 100
        g: int = 100
        b: int = 100
        a: int = 255
        while (x1 != x2) and (y1 != y2):
            x1 += 1 if x1 != x2 else 0
            x2 -= 1 if x2 != x1 else 0
            y1 += 1 if y1 != y2 else 0
            y2 -= 1 if y2 != y1 else 0
            r = add(r, factor=0.1)
            g = add(g, factor=0.1)
            b = add(b, factor=0.1)
            draw.rectangle((x1, y1, x2, y2), outline=(r, g, b, a))

        imqt: ImageQt = ImageQt(im)
        qim: QtGui.QImage = QtGui.QImage(imqt)
        pixmap: QtGui.QPixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)

    def get_right(self) -> int:
        rgt: int = self.master.geometry().right()
        return rgt

    def get_left(self) -> int:
        w: int = self.width()
        rgt: int = self.get_right()
        lft: int = rgt - w
        return lft

    def get_min_top(self) -> int:
        min_top: int = self.y_offset
        return min_top

    def get_max_top(self) -> int:
        max_top: int = (self.master.height() - self.y_offset) - self.height()
        return max_top

    def mousePressEvent(self, ev):
        self.handle = ev.globalPosition().y() - self.geometry().top()
        self.holding = True

    def mouseReleaseEvent(self, ev):
        self.holding = False

    def mouseMoveEvent(self, ev):
        if self.holding:
            min_top: int = self.get_min_top()
            max_top: int = self.get_max_top()
            global_y: int = ev.globalPosition().y() - self.handle
            if global_y < min_top:
                top: int = max(global_y, min_top)
            else:
                top: int = min(global_y, max_top)

            pos(self, top=top)

            try:
                progress: float = top / (max_top - min_top)
            except ZeroDivisionError:
                progress: float = 0.0

            curtain_height: int = self.master.canvas.height() - self.master.height()
            new_top: float = -(float(curtain_height) * progress)
            pos(self.master.canvas, top=new_top)

    def show_scroller(self):
        w: int = self.width()
        h: int = self.height()
        if (w, h) != self.recent_size:
            self.recent_size = w, h
            self.change_look()
            lft: int = self.get_left()
            pos(self, left=lft, x_offset=self.x_offset, y_offset=self.y_offset)

        self.show()
    def hide_scroller(self):
        self.hide()



class ScrollerCanvas(Base):
    """"""
class CustScrollArea(Base):
    widgets: list = []
    Canvas = ScrollerCanvas
    Scroller = ScrollerThingey

    def __init__(self,
                 master,
                 steps: int = 100,
                 scroller_w: int = 11,
                 scroller_h: int = 50,
                 scroller_x_offset: int = 0,
                 scroller_y_offset: int = 0,
                 ):

        super().__init__(master)
        self.steps: int = steps
        self.canvas: ScrollerCanvas = self.Canvas(self)
        scroller_size: dict = dict(width=scroller_w, height=scroller_h)
        scroller_offsets: dict = dict(x_offset=scroller_x_offset, y_offset=scroller_y_offset)
        self.scroller: ScrollerThingey = self.Scroller(self, **scroller_size, **scroller_offsets)
        self.scroller.hide_scroller()

    def wheelEvent(self, event: typing.Optional[QtGui.QWheelEvent]):
        if self.canvas.height() <= self.height():
            return

        event_steps: int = event.angleDelta().y() // 120
        vector: int = event_steps and event_steps // abs(event_steps)  # 0, 1, or -1
        down: bool = vector == -1
        self.scroll_vertically(down)

    def scroll_vertically(self, down: bool):
        canvas_top: int = self.canvas.geometry().top()
        curtain_height: int = self.canvas.height() - self.height()
        steps: int = min(self.steps, len(self.widgets)) or 1
        ppp: int = curtain_height // steps
        if down:
            new_top: int = max(-curtain_height, canvas_top - ppp)
        else:
            new_top: int = min(0, canvas_top + ppp)

        pos(self.canvas, top=new_top)

        try:
            progress: float = abs(new_top) / abs(curtain_height)
        except ZeroDivisionError:
            progress: float = 0.0

        scroller_realm: float = float(self.scroller.get_max_top() - self.scroller.get_min_top())
        scroller_top: int = int(scroller_realm * progress)
        pos(self.scroller, top=scroller_top)

    def add_widget(self, widget: object):
        if widget not in self.widgets:
            self.widgets.append(widget)
            self.auto_arrange_widgets()
            self.expand()

    def remove_widget(self, widget: object):
        if widget in self.widgets:
            self.widgets.remove(widget)
            self.auto_arrange_widgets()
            self.expand()

    def auto_arrange_widgets(self, y_offset: int = 0):
        for count, i in self.widgets:
            if not count:
                pos(i, top=0)
            else:
                pos(i, below=self.widgets[count], y_offset=y_offset)

    def resizeEvent(self, a0):
        if 'canvas' in dir(self):
            self.expand()

    def expand(self):
        if self.widgets:
            w: int = self.width()
            h: int = max(x.geometry().bottom() + 1 for x in self.widgets)
        else:
            w: int = self.width()
            h: int = self.height()

        pos(self.canvas, size=[w, h])
        if h <= self.height():
            self.scroller.hide_scroller()
        else:
            self.scroller.show_scroller()



class PasteHeader(Base):
    priv_trans: dict = {0: 'privacy_min', 1: 'privacy_mid', 2: 'privacy_max'}
    background_idle: tuple = 175, 155, 120, 255
    background_hover: tuple = 225, 225, 220, 255
    activated: bool = False
    right_hold: bool = False

    def __init__(self, master, main, paste: tuple, widgets: list):
        super().__init__(master)
        self.paste: tuple = paste
        self.widgets: list = widgets
        self.main = main

    def make_right_corner(self, draw: ImageDraw, h: int, rgt: int, **kwargs):
        org_r, org_g, org_b, org_a = self.background_idle
        r, g, b, _ = tuple(max(col - 3, 0) for col in self.background_idle)
        max_r: int = min(255, int(org_r * 1.15))
        max_g: int = min(255, int(org_g * 1.15))
        max_b: int = min(255, int(org_b * 1.15))

        cnr: int = int(h * 0.8)
        for x in range(rgt - int(cnr * 3.5), rgt + 1):
            xy: tuple = x, 0, rgt, cnr,
            fill: tuple = r, g, b, org_a
            draw.line(xy, fill)
            if (x % 2):
                r = add(r, max_val=max_r)
                g = add(g, max_val=max_g)
                b = add(b, max_val=max_b)

    def make_privacy_image(self, btm: int, **kwargs) -> Image:
        priv_var: str = self.priv_trans[self.paste[Pastes.private]]
        priv_im: [None | Image.Image] = grabimages(priv_var=priv_var)
        #priv_im: [None | Image.Image] = db.load_image(priv_var)
        thumb_size: tuple[int, int] = (btm - 2) * 2, btm - 4,

        if not priv_im:
            priv_im = Image.new('RGBA', thumb_size, (10,20,30,255))
        elif (priv_im.width, priv_im.height) != thumb_size:
            priv_im = priv_im.resize(thumb_size, resample=Image.Resampling.LANCZOS)

        return priv_im

    def make_long_lines(self, draw: ImageDraw, im: Image, priv_im: Image, rgt: int, btm: int, **kwargs):
        r: int = 150
        g: int = 150
        b: int = 150
        a: int = 255
        draw.rectangle((0, 0, priv_im.width + 2, btm), fill=(r, g, b, a))
        for n in range(1, 4):
            draw.rectangle((priv_im.width + 2 + n, n, rgt - n, btm - n), outline=(r, g, b, a))
            r = sub(r, factor=0.25, min_val=20)
            g = sub(g, factor=0.25, min_val=20)
            b = sub(b, factor=0.25, min_val=20)

        im.paste(priv_im, (2, 2))
        draw.rectangle((2, 2, 2 + priv_im.width, 2 + priv_im.height), outline=(50, 50, 50, 255))

        for xy in [(n, n, rgt - n, btm - n) for n in [0]]:
            draw.rectangle(xy, outline=(0, 0, 0, 255))

    def make_drag_and_dropper(self, priv_im: Image, **kwargs):
        self.drag_and_drop_label = DragAndDropper(self)
        pos(self.drag_and_drop_label, size=[priv_im.width, priv_im.height], top=2, left=2)
        style(self.drag_and_drop_label, background='transparent')

    def make_date_label(self, edge: int, **kwargs):
        post_epoch: int = self.paste[Pastes.date]
        human_date: str = epoch_to_date(post_epoch)
        self.date_label = TextLabel(self)
        self.date_label.setText(human_date)
        style(self.date_label, color='rgb(30,30,30)', bold=True)
        pos(self.date_label, height=self.height() * 0.4)
        self.date_label.set_proper_font_size()
        text_width: int = self.date_label.text_width()
        pos(self.date_label, top=4, left=self.width() - (text_width + (edge * 3)), width=text_width + (edge * 2))

    def make_text_label(self, edge: int, h: int, proper_left: int, **kwargs):
        reach: dict = dict(right=self.geometry().right() - 9)
        self.text_label = TextLabel(self)
        pos(self.text_label, top=4, left=proper_left, height=h - 8, reach=reach)
        style(self.text_label, background='transparent', color='black')
        self.text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_label.setContentsMargins(10, 0, 0 ,0)
        org_text: str = self.paste[Pastes.title] or ""
        self.text_label.setText(org_text)
        self.text_label.set_proper_font_size()
        text_label_edge: int = self.date_label.width() + edge
        self.text_label.set_proper_text(edge=text_label_edge)

    def make_shade_labels(self, priv_im: Image, h: int, edge: int, proper_left: int, **kwargs):
        self.shade_one = self.Shade(self)
        self.shade_two = self.Shade(self)
        reach: dict = dict(right=self.geometry().right() - 9)
        pos(self.shade_one, size=[priv_im.width, priv_im.height], top=2, left=2)
        pos(self.shade_two, height=h - (edge * 2), top=edge, left=proper_left, reach=reach)
        [x.idle() for x in (self.shade_one, self.shade_two)]

    def paste_isexpired(self) -> bool:
        if self.paste[Pastes.expire_date]:
            expire_epoch: int = self.paste[Pastes.expire_date]
            now: int = int(time.time())
            return now > expire_epoch
        return False
    def make_expire_labels(self, draw: ImageDraw, w: int, h: int, edge: int, proper_left: int, **kwargs):
        if self.paste_isexpired():
            post_epoch: int = self.paste[Pastes.date] or 0
            human_date: str = epoch_to_date(post_epoch)
            self.date_label.setText(f'{human_date}\nEXPIRED')
            pos(self.date_label, height=self, sub=edge * 2)
            style(self.date_label, color='gray')
            style(self.text_label, color='gray')
            draw.rectangle((proper_left, edge, w - (edge + 1), h - (edge + 1)), fill=(40, 40, 40, 255))

        elif self.paste[Pastes.expire_date]:
            post_epoch: int = self.paste[Pastes.date] or 0
            expire_epoch: int = self.paste[Pastes.expire_date]
            now: int = int(time.time())
            ticks: int = abs(expire_epoch - post_epoch) or 1
            progress: float = (now - post_epoch) / ticks
            line_lenght: int = int((w - proper_left) * progress)
            x1: int = proper_left
            x2: int = min(w - proper_left, proper_left + line_lenght)
            y: int = h - (edge + 1)
            thick: int = 2
            time_rgba: tuple = 200, 60, 0, 255
            dark_rgba: tuple = 155, 55, 55, 255
            time_line: dict = rests_rgba_dict(time_rgba, self.background_idle, line_lenght)
            black_line: dict = rests_rgba_dict(dark_rgba, self.background_idle, line_lenght)
            while x1 <= x2:
                rgba: tuple = tuple(time_line[key]['val'] for key in time_line)
                for n in range(thick):
                    draw.point((x1, y - n), fill=rgba)

                rgba: tuple = tuple(black_line[key]['val'] for key in black_line)
                draw.point((x1, y - thick), fill=rgba)

                for rests in [time_line, black_line]:
                    for i in rests:
                        rests[i]['rest'] += rests[i]['ppp']
                        if rests[i]['rest'] > 1.0:
                            val: int = rests[i]['val']
                            fn = rests[i]['fn']
                            rests[i]['val'] = fn(val)
                            rests[i]['rest'] -= float(int(rests[i]['rest']))
                x1 += 1


    def make_size_label(self, edge: int, **kwargs):
        self.size_label = TextLabel(self)
        self.size_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight)
        self.size_label.setContentsMargins(0, 0, 4, 0)
        dt: TextLabel = self.date_label
        reach: dict = dict(bottom=self.height() - edge + 2)
        pos(self.size_label, width=dt, below=dt, reach=reach, y_offset=-3)
        copy_stylesheet(self.size_label, dt)

        if not self.paste_isexpired():
            size: int = (self.paste[Pastes.size] or 0)
            mb_int: int = int(size / 1_000_000)
            if mb_int:
                kb_int: int = round(size - (mb_int * 1_000_000), 3)
                kb_str: str = f'{kb_int}0'
                size_txt: str = f'{mb_int}.{kb_str[:2]} MB'
                style(self.size_label, color='rgb(125,35,25)')
            elif size // 1000:
                kb_str: str = f'{round(size / 1000)}'
                size_txt: str = f'{kb_str} KB'
                style(self.size_label, color='rgb(35,55,125)')
            else:
                size_txt: str = f'{size} bytes'
                style(self.size_label, color='rgb(15,55,25)')

            self.size_label.setText(size_txt)


    def init_draw(self):
        w: int = self.width()
        h: int = self.height()
        size: tuple[int, int] = w, h,
        im = Image.new('RGBA', size, self.background_idle)
        draw = ImageDraw.Draw(im)
        priv_im: Image = self.make_privacy_image(im.height - 1)

        draw_kwgs: dict = dict(
            im=im,
            draw=draw,
            priv_im=priv_im,
            proper_left=priv_im.width + 6,
            edge=4,
            w=w, h=h,
            lft=0, rgt=im.width - 1,
            top=0, btm=im.height - 1,
        )

        self.make_right_corner(**draw_kwgs)
        self.make_long_lines(**draw_kwgs)
        self.make_date_label(**draw_kwgs)
        self.make_text_label(**draw_kwgs)
        self.make_shade_labels(**draw_kwgs)
        self.make_expire_labels(**draw_kwgs)
        self.make_size_label(**draw_kwgs)
        self.make_drag_and_dropper(**draw_kwgs)

        imqt = ImageQt(im)
        qim = QtGui.QImage(imqt)
        pixmap = QtGui.QPixmap.fromImage(qim)
        self.setPixmap(pixmap)


    class Shade(Base):
        def hover(self):
            style(self, background='transparent')

        def idle(self):
            style(self, background='rgba(0,0,0,50)')

    def enterEvent(self, event):
        if not self.activated:
            try:
                [x.hover() for x in (self.shade_one, self.shade_two)]
            except AttributeError:
                ...

    def leaveEvent(self, a0):
        if not self.activated:
            try:
                [x.idle() for x in (self.shade_one, self.shade_two)]
            except AttributeError:
                ...

    def mouseReleaseEvent(self, ev):
        if self.right_hold:
            self.right_hold = False
            self.deletecountdowner()

        for i in self.widgets:
            if i.activated and i != self:
                i.activated = False
                [x.idle() for x in (i.shade_one, i.shade_two)]

        self.activated = not self.activated
        if self.activated and ev.button().value == 1:
            self.show_contents()

    def mousePressEvent(self, ev):
        if ev.button().value != 1:
            self.right_hold = True
            if 'delete_label' not in dir(self):
                self.create_delete_label()

            self.deletecountdowner()

    def create_delete_label(self):
        self.delete_label = Base(self)
        pos(self.delete_label, width=0, height=self)
        style(self.delete_label, background='red', border='black 2px')

    def deletecountdowner(self):
        delay: float = 0.01
        try:
            delete_label = self.delete_label
        except AttributeError:
            self.create_delete_label()
            delete_label = self.delete_label

        if not self.right_hold:
            try:
                delete_label.close()
                delattr(self, 'delete_label')
            except (RuntimeError, AttributeError):
                ...
            return

        next_w: int = delete_label.width() + 1
        for bump in [int(self.width() * 0.10), int(self.width() * 0.5)]:
            if next_w > bump:
                next_w += 5

        if next_w > self.width():
            self.right_hold = False

            paste_key: str = self.paste[Pastes.key]
            deleted: bool = delete_paste(paste_key)

            if not deleted:
                pos(delete_label, width=self)
                style(delete_label, font=14, bold=True, color='black')
                delete_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                delete_label.setText('ASSUMING FAILIURE')
                q: str = 'update pastes set missing = (?) where key is (?)'
                v: tuple = True, paste_key,
                with db.connection:
                    db.cursor.execute(q, v)
            else:
                q: str = 'delete from pastes where key is (?)'
                v: tuple = paste_key,
                with db.connection:
                    db.cursor.execute(q, v)

                widgets: list = self.main.shelf.scrollarea.widgets
                if len(widgets) > 1:
                    tops: list = [x.geometry().top() for x in widgets]
                    tops.sort()
                    y_delta: int = tops[1] - tops[0]
                    top: int = min(tops)
                    widgets.remove(self)
                    for count, paste in enumerate(widgets):
                        pos(paste, top=top + (y_delta * count))
                else:
                    widgets.remove(self)

                self.close()

        else:
            pos(delete_label, width=next_w)
            self.main.thread_then_main(main_fn=self.deletecountdowner, wait=delay)

    def show_contents(self):
        title: str = self.paste[Pastes.title] or ""
        paste_key: str = self.paste[Pastes.key]
        self.main.rgt_titlebar.searchbar.setText(title)
        text: [str | bytes] = self.paste[Pastes.data] or ""
        if not isinstance(text, str):
            text: str = 'ERROR LOADING TEXT, SEEMS TO BE NOT A STRING!!!'

        if not text:
            text: str = download_paste(paste_key)
            if text:
                q: str = 'update pastes set data = (?) where key is (?)'
                v: tuple = text, paste_key,
                with db.connection:
                    db.cursor.execute(q, v)

                q: str = 'select * from pastes where key is (?)'
                v: tuple = paste_key,
                data: [tuple | None] = db.cursor.execute(q, v).fetchone()
                if data:
                    self.paste = data

        self.main.write_area.qtextedit.setText(text)
        privacy: [int | None] = self.paste[Pastes.private]
        if isinstance(privacy, int):
            db.save_setting(self.main.privacy_btn.load_save_var, privacy)
            self.main.privacy_btn.change_save_and_visualize(privacy=privacy)

        if isinstance(text, str) and '-----BEGIN PGP MESSAGE-----' in text:
            if 'gpg_decrypt_shade' not in dir(self.main):
                from tricks.buttons import Button
                bw: int = Button.border_width
                text_label: TextLabel = self.main.gpg_bar.text_label
                decrypt_btn: TextLabel = self.GPGBtn(text_label)
                decrypt_btn.qtextedit = self.main.write_area.qtextedit
                decrypt_btn.main = self.main
                decrypt_btn.setText('DECRYPT')
                pos(decrypt_btn, size=text_label, sub=bw * 2, left=bw - 1, top=bw - 1, add=2)
                copy_stylesheet(destination=decrypt_btn, source=text_label)
                style(decrypt_btn, background='rgba(50, 225, 50, 255)', color='black', border='black')
                try:
                    # removes bold font... I know much trouble though I'd rather do it here than in style_fn
                    style_dict: dict = construct_stylesheet_dict(decrypt_btn)
                    key: str = next(iter(style_dict))
                    style_dict[key].pop('font-weight')
                    style_str: str = construct_stylesheet_str(style_dict)
                    decrypt_btn.setStyleSheet(style_str)
                except KeyError:
                    ...

                self.main.gpg_decrypt_shade = decrypt_btn

        elif 'gpg_decrypt_shade' in dir(self.main):
            self.main.gpg_decrypt_shade.suicide()

        url: str = f'http://pastebin.com/raw/{paste_key}'
        self.main.show_url_label(url)


    class GPGBtn(TextLabel):

        def mouseReleaseEvent(self, ev):
            if ev.button().value == 1:
                try:
                    qtextedit = self.qtextedit
                except AttributeError:
                    ...
                text: str = qtextedit.toPlainText()
                decrypted_text: [str | bytes] = decrypt_armor(text)
                if isinstance(decrypted_text, str):
                    qtextedit.setText(decrypted_text)
                else:
                    try:
                        fake_file = io.BytesIO()
                        fake_file.write(decrypted_text)
                        fake_file.seek(0)

                        tmp_dir: str = tmpdir()
                        with zipfile.ZipFile(fake_file, mode='r') as zf:
                            zf.extractall(tmp_dir)

                        inject: list = ['EXTRACTED ALL FILES INTO:', tmp_dir]
                        qtextedit.setText("\n\n".join(inject))
                        title_text: str = " ".join(inject)
                    except:
                        title_text: str = 'ERROR SHOWING DECRYPTED TEXT, SEEMS TO BE NOT A STRING!!!'

                    self.master.master.master.change_window_title(title_text)



            self.mouseReleaseEvent = lambda *args, **kwargs: None
            self.suicide()

        def suicide(self):
            if 'countdown' not in dir(self):
                self.setText('')
                self.countdown: int = 30
            else:
                self.countdown -= 1

            if self.countdown <= 0:
                try:
                    self.close()
                    del self.main.gpg_decrypt_shade
                except (AttributeError, RuntimeError):
                    ...
            else:
                stylesheet: dict = construct_stylesheet_dict(self)
                try:
                    key: str = next(iter(stylesheet))
                    bg_col: str = stylesheet[key]['background-color']
                    parts: list = bg_col.split(',')
                    r, g, b, a = tuple(int("".join(n for n in x if n.isdigit())) for x in parts)
                except (KeyError, ValueError):
                    self.countdown = 0
                    self.main.thread_then_main(self.suicide, wait=0.1)
                    return

                r = add(r, factor=0.15)
                g = add(g, factor=0.20)
                b = add(b, factor=0.05)
                a = sub(a, min_sub=15)
                style(self, background=f'rgba({r},{g},{b},{a})', border=f'rgba(0,0,0,{a})')
                self.main.thread_then_main(self.suicide, wait=0.1)

