from PIL                    import Image
from PIL.ImageDraw          import ImageDraw
from PIL.ImageQt            import ImageQt, QImage
from PyQt6                  import QtGui, QtWidgets
from PyQt6.QtGui            import QFont
from tricks.buttons         import Button
from tricks.smartpos        import pos
from tricks.styles          import style
from tricks.widget_drawings import bordered, thread_draw
from tricks.widgets         import Base, CustScrollArea

class ScrollArea(CustScrollArea):
    ...

class DrawBase(Base):
    def init_draw(self):
        border: tuple = Button.col_border_idle
        background: tuple = 50, 50, 50, 255

        w: int = self.width()
        h: int = self.height()
        bw: int = Button.border_width

        kwgs = dict(
            draw_fn=bordered,
            emit_fn=self.set_background,
            w=w,
            h=h,
            border=border,
            background=background,
            bw=bw,
        )
        thread_draw(**kwgs)

    def set_background(self, work_dict: dict):
        w, h, datas = work_dict['w'], work_dict['h'], work_dict['datas']
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        im.putdata(datas)
        imqt = ImageQt(im)
        qim = QImage(imqt)
        pixmap = QtGui.QPixmap.fromImage(qim)

        self.setPixmap(pixmap)

class ShelfScrollArea(ScrollArea):
    class Canvas(ScrollArea.Canvas):
        def moveEvent(self, a0):
            self.master.show_top_btm_shader()

    def show_top_btm_shader(self):
        try:
            shade_top = self.master.scroll_top_trans
            shade_btm = self.master.scroll_btm_trans
        except AttributeError:
            return

        if not self.widgets:
            shade_top.hide()
        else:
            shade_top.show()
            max_top: int = shade_top.max_top
            min_top: int = shade_top.min_top
            canvas_top: int = self.canvas.geometry().top()
            if canvas_top < 0:
                if (min_top - canvas_top) < (max_top - 1):
                    pos(shade_top, top=min_top - canvas_top)
                else:
                    pos(shade_top, top=min_top)
            else:
                pos(shade_top, top=max_top)

        if not self.scroller:
            shade_btm.hide()
        else:
            shade_btm.show()

    def expand(self):
        super().expand()
        self.show_top_btm_shader()

class Shelf(DrawBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        kwgs: dict = dict(scroller_x_offset=-Button.border_width + 1, scroller_y_offset=0)
        self.scrollarea = ShelfScrollArea(self, **kwgs)

    def resizeEvent(self, a0):
        if 'scrollarea' in dir(self):
            bw: int = Button.border_width
            reach: dict = dict(bottom=self.height() - bw)
            pos(self.scrollarea, size=self, sub=bw * 2, left=bw, top=bw, reach=reach)

    class ScrollTransp(Base):
        """"""

    def init_draw(self):
        super().init_draw()

        if any(x not in dir(self) for x in ['scroll_btm_trans', 'scroll_top_trans']):

            w, h = self.master.paste_size()
            halv_h: int = h // 2
            lft: float = ((1 + self.width()) - w) * 0.5
            btm: int = self.geometry().bottom() - 10
            top: int = self.geometry().top() + lft - 1

            self.scroll_btm_trans = self.ScrollTransp(self.master)
            self.scroll_top_trans = self.ScrollTransp(self.master)
            self.scroll_top_trans.max_top = top
            self.scroll_top_trans.min_top = top - (lft - Button.border_width - 1)

            pos(self.scroll_btm_trans, size=[w, halv_h], left=lft, bottom=btm)
            pos(self.scroll_top_trans, size=[w, halv_h], left=lft, top=top)

            for scroll_trans in [self.scroll_btm_trans, self.scroll_top_trans]:
                style(scroll_trans, background='transparent')

                im = Image.new('RGBA', (w, halv_h), (0, 0, 0, 0))
                draw = ImageDraw(im)
                alpha: int = 10
                incr: float = 200 // halv_h

                if scroll_trans == self.scroll_btm_trans:
                    for y in range(im.height - 1):
                        draw.line((0, y, im.width - 1, y), fill=(10, 10, 10, alpha))
                        alpha += incr
                    draw.line((0, im.height - 1, im.width - 1, im.height - 1), fill=(10, 10, 10, alpha))
                else:
                    for y in range(im.height - 1, 0, -1):
                        draw.line((0, y, im.width - 1, y), fill=(10, 10, 10, alpha))
                        alpha += incr
                    draw.line((0, 0, im.width - 1, 0), fill=(10, 10, 10, alpha))

                imqt = ImageQt(im)
                qim = QImage(imqt)
                pixmap = QtGui.QPixmap.fromImage(qim)
                scroll_trans.setPixmap(pixmap)


class WriteArea(DrawBase):

    def init_draw(self):
        super().init_draw()

        self.qtextedit = QtWidgets.QTextEdit(self)
        bw: int = Button.border_width
        kwgs: dict = dict(size=self, sub=bw * 2, left=bw * 1, top=bw * 1)
        pos(self.qtextedit, **kwgs)
        style(self.qtextedit, background='rgb(25,25,25)', color='white', font=14)
        font: QFont = QFont('monospace')
        self.qtextedit.setFont(font)
        self.qtextedit.show()
