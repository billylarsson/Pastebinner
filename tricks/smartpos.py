class QtPosition:
    def __init__(s, thing, **kwargs):
        s.x = thing.pos().x()
        s.y = thing.pos().y()
        s.w = thing.width()
        s.h = thing.height()

        extras = 'x_offset', 'y_offset', 'margin', 'add', 'sub'
        s.x_offset, s.y_offset, s.margin, s.add, s.sub = 0, 0, 0, 0, 0 # linter
        [setattr(s, extra, kwargs[extra] if extra in kwargs else 0) for extra in extras]
        s.sub = -s.sub if s.sub > 0 else s.sub

        for not_first_lap, (fn_name, orders) in enumerate({k:v for k,v in kwargs.items() if k not in extras}.items()):
            if not_first_lap:
                s.x, s.y, s.w, s.h = int(s.x), int(s.y), int(s.w), int(s.h)
            try:
                fn = getattr(s, fn_name)
            except AttributeError:
                continue

            fn(orders)

        s.gen_coords(**kwargs)
        s.set_coords(thing)

    def set_coords(s, thing):
        thing.setGeometry(*s.coords)

    def gen_coords(s, **kwargs):
        w_alter = (s.add + s.sub) if any(x in kwargs for x in ['size', 'width']) else 0
        h_alter = (s.add + s.sub) if any(x in kwargs for x in ['size', 'height']) else 0
        s.coords = int(s.x + s.x_offset), int(s.y + s.y_offset), int(s.w + w_alter), int(s.h + h_alter)

    def reach(s, dict_or_list):
        for orders in dict_or_list if isinstance(dict_or_list, (list, tuple)) else [dict_or_list]:
            if 'right' in orders:
                if isinstance(orders['right'], (int, float)):
                    s.w = orders['right'] - s.x
                else:
                    s.w = orders['right'].geometry().left() - s.x

            elif 'left' in orders:
                if isinstance(orders['left'], (int, float)):
                    s.w = s.w + (max(s.x, orders['left']) - min(s.x, orders['left']))
                    s.x -= (max(s.x, orders['left']) - min(s.x, orders['left']))
                else:
                    val = (max(s.x, orders['left'].geometry().right()) - min(s.x, orders['left'].geometry().right()))
                    s.w = s.w + val
                    s.x -= val

            elif 'bottom' in orders:
                if isinstance(orders['bottom'], (int, float)):
                    s.h = orders['bottom'] - s.y
                else:
                    s.h = orders['bottom'].geometry().top() - s.y

            elif 'top' in orders:
                if isinstance(orders['top'], (int, float)):
                    s.h = s.h + (max(s.y, orders['top']) - min(s.y, orders['top']))
                    s.y -= (max(s.y, orders['top']) - min(s.y, orders['top']))
                else:
                    val = (max(s.y, orders['top'].geometry().top()) - min(s.y, orders['top'].geometry().top()))
                    s.h = s.h + val
                    s.y -= val

    def size(s, some):
        if isinstance(some, (list, tuple)):
            s.w, s.h = some[0], some[1]
        else:
            s.w, s.h = some.width(), some.height()

    def top(s, some):
        if isinstance(some, (int, float)):
            s.y = some
        else:
            s.y = some.geometry().top()

    def bottom(s, some):
        if isinstance(some, (int, float)):
            s.y = some - (s.h + 1)
        else:
            s.y = some.geometry().bottom() - (s.h + 1)

    def below(s, some):
        s.y = some.geometry().bottom() + 1
        s.x = some.geometry().left()

    def after(s, some):
        s.y = some.geometry().top()
        s.x = some.geometry().right() + 1

    def before(s, some):
        s.y = some.geometry().top()
        s.x = some.geometry().left() - (1 + s.w)
        if s.x_offset > 0:
            s.x_offset = -s.x_offset

    def above(s, some):
        s.y = some.geometry().top() - (1 + s.h)
        s.x = some.geometry().left()
        if s.y_offset > 0:
            s.y_offset = -s.y_offset

    def left(s, some):
        if isinstance(some, (int, float)):
            s.x = some
        else:
            s.x = some.geometry().left()

    def right(s, some):
        if isinstance(some, (int, float)):
            s.x = some - s.w - 1
        else:
            s.x = (some.geometry().right() - s.w) + 1

    def coat(s, idol):
        s.x = idol.geometry().left()
        s.y = idol.geometry().top()
        s.w = idol.width()
        s.h = idol.height()

    def move_x(s, this_much):
        s.x += this_much

    def move_y(s, this_much):
        s.y += this_much

    def move(s, dual):
        s.move_x(dual[0])
        s.move_y(dual[1])

    def height(s, some):
        if isinstance(some, (int, float)):
            s.h = some
        else:
            s.h = some.height()

    def width(s, some):
        if isinstance(some, (int, float)):
            s.w = some
        else:
            s.w = some.width()



class DryQtPosition(QtPosition):
    def set_coords(s, *args, **kwargs):
        s.lft, s.top, s.w, s.h = s.coords
        s.btm = s.top + s.h
        s.rgt = s.lft + s.w


pos = QtPosition
drypos = DryQtPosition