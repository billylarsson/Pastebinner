from PIL            import Image
from PIL.ImageDraw  import ImageDraw
from PyQt6          import QtCore
from tricks.widgets import add, sub
import random, threading


def draw_crackling_background(w: int, h: int, im: Image, draw: ImageDraw, background: tuple):
    rgt: int = im.width - 1  # far x pixel starts with 0, y pixels starts with 0
    btm: int = im.height - 1

    draw_all: dict = {}
    for _ in range(10):
        x: int = random.randint(0, rgt)
        y: int = random.randint(0, btm)
        flow_min: int = int((w * h) * 0.10)
        flow_max: int = int((w * h) * 0.30)
        flow: int = random.randint(flow_min, flow_max)
        r, g, b, a = background

        start_vals: int = r
        end_vals: int = min(int(r * random.uniform(1.1, 1.3)), 255)
        col_incr: bool = True

        per_cycle: float = (end_vals - start_vals) / flow
        flow_fill: float = 0.0

        while col_incr or r != start_vals:
            rnd: int = random.randint(1, 6)

            if rnd == 1:
                y = min(btm, y + 1)
            elif rnd == 2:
                y = max(0, y - 1)
            elif rnd == 3 or rnd == 4:
                x = min(rgt, x + 1)
            else:
                x = max(0, x - 1)

            draw_all[(x, y)]: tuple = r, g, b, a

            flow_fill += per_cycle
            if flow_fill > 1.0:
                flow_fill = 0.0
                if col_incr:
                    r = add(r, max_val=end_vals)
                    b = add(b, max_val=end_vals)
                    g = add(g, max_val=end_vals)
                    col_incr = (r != end_vals)
                else:
                    r = sub(r, min_val=start_vals)
                    b = sub(b, min_val=start_vals)
                    g = sub(g, min_val=start_vals)

    for xy, rgba in draw_all.items():
        draw.point(xy, rgba)

def draw_border(im: Image, draw: ImageDraw, border: tuple, bw: int):
    rgt: int = im.width - 1  # far x pixel starts with 0, y pixels starts with 0
    btm: int = im.height - 1

    r, g, b, a = border

    for n in range(1, bw):
        x: int = n
        y: int = n
        rect_w: int = rgt - n
        rect_h: int = btm - n
        r = sub(r, factor=0.10)
        g = sub(g, factor=0.10)
        b = sub(b, factor=0.10)
        draw.rectangle((x, y, rect_w, rect_h), outline=(r, g, b, a))

    xy_width_height: tuple = bw, bw, (rgt - bw), (btm - bw)
    draw.rectangle(xy_width_height, outline=(65, 65, 65, 255))  # inner border
    draw.rectangle((0, 0, rgt, btm), outline=(10, 10, 10, 255))  # outer border

def bordered_crackling_background(w: int, h: int, border: tuple, background: tuple, bw: int) -> tuple:
    im = Image.new('RGBA', (w, h), background)
    draw = ImageDraw(im)
    draw_crackling_background(w, h, im, draw, background)
    draw_border(im, draw, border, bw)
    return im, draw

def bordered(w: int, h: int, border: tuple, background: tuple, bw: int) -> tuple:
    im = Image.new('RGBA', (w, h), background)
    draw = ImageDraw(im)
    draw_border(im, draw, border, bw)
    return im, draw

class RunnerSignal(QtCore.QObject):
    finished = QtCore.pyqtSignal(dict)

def thread_runner(signal: RunnerSignal, emit_dict: dict, draw_fn, kwgs: dict):
    im, draw = draw_fn(**kwgs)
    for rgba in im.getdata():
        emit_dict['datas'].append(rgba)

    signal.finished.emit(emit_dict)

def thread_draw(draw_fn, emit_fn, w: int, h: int, **kwargs):
    signal: RunnerSignal = RunnerSignal()
    signal.finished.connect(emit_fn)
    kwgs: dict = {'w': w, 'h': h}
    [kwgs.update({k: v}) for k,v in kwargs.items()]
    emit_dict: dict = {'w': w, 'h': h, 'datas': []}
    args: tuple = signal, emit_dict, draw_fn, kwgs,
    threading.Thread(target=thread_runner, args=args, daemon=True).start()