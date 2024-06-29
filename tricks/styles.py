def stylesheet_font(font: any) -> int:
    return int("".join(x for x in str(font) if x.isdigit()))

def stylesheet_border(border: any) -> dict:
    if isinstance(border, int):
        return dict(style='solid', size=1, color='black')
    else:
        lines = 'dashed', 'dot-dash', 'dot-dot-dash', 'dotted', 'double', 'groove', 'inset', 'outset', 'ridge', 'solid'
        for line_type in lines:
            if line_type in border:
                border_style = line_type
                border = border.replace(border_style, "")
                break
        else:
            border_style = 'solid'

        px_val = ""
        if 'px' in border:

            fwd_ix = border.find('px') + 2
            rew_ix = border.find('px') - 1
            fwd_cnt, rew_cnt = 0, 0
            fwd_wrd, rew_wrd = "", ""

            while fwd_ix < len(border) and not fwd_wrd:
                while fwd_ix < len(border) and border[fwd_ix].isdigit():
                    fwd_wrd += border[fwd_ix]
                    fwd_ix += 1
                fwd_ix += 1
                fwd_cnt += 1 + len(fwd_wrd)

            while rew_ix >= 0 and not rew_wrd:
                while rew_ix >= 0 and border[rew_ix].isdigit():
                    rew_wrd = border[rew_ix] + rew_wrd
                    rew_ix -= 1
                rew_ix -= 1
                rew_cnt += 1 + len(rew_wrd)

            if ((fwd_wrd and rew_wrd) and (fwd_cnt <= rew_cnt)) or (fwd_wrd and not rew_wrd):
                px_val = fwd_wrd
                border = border[:border.find('px')] + border[border.find('px') + fwd_cnt + 1:]

            elif ((fwd_wrd and rew_wrd) and (rew_cnt < fwd_cnt)) or (rew_wrd and not fwd_wrd):
                px_val = rew_wrd
                border = border[:border.find('px') - rew_cnt + 1] + border[border.find('px') + 2:]

        if not px_val:
            skip = set()
            if 'rgb' in border.lower():
                cut1 = border.lower().find('rgb')
                cut2 = border[cut1:].find(')')
                skip = {x for x in range(cut1, (cut2 + cut1 + 1))} if cut2 != -1 else skip

            ix = 0
            while ix < len(border):
                if ix not in skip:
                    if not border[ix].isdigit() and px_val:
                        break
                    elif border[ix].isdigit():
                        px_val += border[ix]
                ix += 1

            border = border[:ix - len(px_val)] + border[ix:] if px_val else border

        color = "".join(border.split())
        return dict(style=border_style, size=int(px_val or 1), color=color)

def stylesheet_font_str(font: any) -> str:
    size = stylesheet_font(font)
    return f'{size}pt'

def stylesheet_border_str(border: any) -> str:
    dictionary = stylesheet_border(border)
    return f'{dictionary["size"]}px {dictionary["style"]} {dictionary["color"]}'

def string_color(some_col: any) -> str or None:
    if not some_col:
        return some_col
    elif isinstance(some_col, str):
        if some_col.count(',') >= 2:
            if any(x.upper().startswith(x) for x in ['RGB', 'RGBA']):
                return some_col
            else:
                tmp_col = some_col.strip('([])')
        else:
            return some_col
    else:
        tmp_col = str(some_col)

    # uses tmp_col:str from here-on
    if isinstance(some_col, tuple):
        tmp_col = tmp_col.strip('()')
    elif isinstance(some_col, list):
        tmp_col = tmp_col.strip('[]')

    if tmp_col.count(',') == 2:
        return f'rgb({tmp_col})'
    elif tmp_col.count(',') == 3:
        return f'rgba({tmp_col})'
    else:
        return tmp_col

def construct_stylesheet_dict(
        thing,
        background: [str | tuple | list] = None,
        color: [str | tuple | list] = None,
        font: [str | int] = None,
        weight: [str | int] = None,
        border: [str | tuple | list] = None,
        bold: [None | bool] = None,
        tooltip: bool = False,
) -> dict:

    construct: dict = {
        'border': stylesheet_border_str(border) if border else border,
        'background-color': string_color(background),
        'font': stylesheet_font_str(font) if font else font,
        'color': string_color(color),
        'font-weight': '600' if bold else weight,
    }
    base_dict: dict = {k: None if tooltip else v for k, v in construct.items()}
    tool_dict: dict = {k: v if tooltip else None for k, v in construct.items()}

    stylesheet: str = thing.styleSheet()
    classname: str = thing.metaObject().className()

    if '}' not in stylesheet:
        base_style = stylesheet
        tool_style = ""
    else:
        base_style = ""
        tool_style = ""
        while '}' in stylesheet:
            cut = stylesheet.find('}')
            tmp = stylesheet[:cut].strip()
            if '{' in tmp:
                parts = tmp.split('{')
                if 'QToolTip' in parts[0]:
                    tool_style = parts[-1]
                else:
                    base_style = parts[-1]

            stylesheet = stylesheet[cut + 1:]

    for this_dict, string in [(base_dict, base_style), (tool_dict, tool_style)]:
        for i in string.split(';'):
            for var, arg in this_dict.items():
                if not arg and i.strip().startswith(var):
                    twinsplit = i.split(':')
                    this_dict[var] = twinsplit[-1].strip()


    final: dict = {}
    if any(v for _, v in base_dict.items()):
        final.update({classname: {k: v for k, v in base_dict.items() if v}})

    if any(v for _, v in tool_dict.items()):
        final.update({'QToolTip': {k: v for k, v in tool_dict.items() if v}})

    return final

def construct_stylesheet_str(construct: dict) -> str:
    string: str = ""
    for class_name, stylesheet in construct.items():
        keys_vals: str = ';'.join(f'{k}:{v}' for k, v in stylesheet.items() if v)
        string += class_name + '{' + keys_vals + '}'

    return string if "  " not in string else " ".join(string.split())

def style(thing, **kwargs):
    dict_sheet: dict = construct_stylesheet_dict(thing, **kwargs)
    string_sheet: str = construct_stylesheet_str(dict_sheet)
    thing.setStyleSheet(string_sheet) if string_sheet != thing.styleSheet() else ...

def copy_stylesheet(destination, source, **kwargs):
    class_name: str = destination.metaObject().className()
    construct: dict = construct_stylesheet_dict(source)
    construct = {class_name if k != 'QToolTip' else k: v for k,v in construct.items()}
    [construct[class_name].update({k: v}) for k, v in kwargs.items()] if class_name in construct else ...
    str_sheet: str = construct_stylesheet_str(construct)
    destination.setStyleSheet(str_sheet) if str_sheet != destination.styleSheet() else ...