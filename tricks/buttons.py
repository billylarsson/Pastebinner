from PIL                    import Image
from PIL.ImageQt            import ImageQt, QImage
from PyQt6                  import QtGui, QtWidgets
from PyQt6.QtGui            import QFont
from tricks.database        import Pastes, db
from tricks.gpgthings       import encrypt_binary, encrypt_text, get_gpg_keys
from tricks.gpgthings       import keyid_in_keyring
from tricks.pastebin_api    import publish_paste, update_and_save_headers
from tricks.smartpos        import pos
from tricks.styles          import style
from tricks.widget_drawings import bordered_crackling_background
from tricks.widgets         import Base, PasteHeader, ShadedTextLabel
import io, os, time, zipfile

FOLDER_STARTSWITH_BLOCK: set = {'_', 'venv', 'env', '.'}
FILE_STARTSWITH_BLOCK: set = set()
FILE_EXTENSION_BLOCK: set = {'.sqlite'}

class Button(Base):
    border_width: int = 4

    col_border_idle: tuple = 145, 175, 175, 255
    col_background_idle: tuple = 150, 150, 150, 255
    col_text_idle: tuple = 20, 55, 55, 255

    col_border_hover: tuple = 175, 225, 225, 255
    col_background_hover: tuple = 175, 175, 175, 255
    col_text_hover: tuple = 5, 15, 15, 255

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init_draw(self):
        self.create_text_label()
        w: int = self.text_label.text_width()
        pos(self, width=w + (self.border_width * 6))

        kwgs: dict = dict(
            border=self.col_border_idle,
            background=self.col_background_idle,
            text_color=self.col_text_idle,
        )
        self.redraw(**kwgs)

    def redraw(
            self,
            border: tuple,
            background: tuple,
            text_color: [tuple | str] = 'black',
    ):

        w: int = self.width()
        h: int = self.height()
        key: str = f'w:{w} h:{h} bw:{self.border_width} border:{border} background:{background} color: {text_color}'

        try:
            im: Image = self._variants[key]['im']
        except (AttributeError, KeyError) as Error:
            if isinstance(Error, AttributeError):
                self._variants = {}

            im, draw = bordered_crackling_background(w, h, border, background, self.border_width)
            self._variants[key]: dict = dict(im=im, draw=draw)

        imqt = ImageQt(im)
        qim = QImage(imqt)
        pixmap = QtGui.QPixmap.fromImage(qim)

        self.setPixmap(pixmap)
        self.create_text_label(text_color=text_color)


    def create_text_label(self, text_color: [tuple | str] = 'black'):
        btn_w: int = self.width()
        btn_h: int = self.height()
        key: str = f'w:{btn_w} h:{btn_h} color: {text_color}'
        try:
            font_size: int = self.text_label.height_fontsize[key]
            text: str = self.text_label.text()
        except (AttributeError, KeyError) as Error:

            if isinstance(Error, AttributeError):
                self.text_label = ShadedTextLabel(self)
                self.text_label.height_fontsize = {}

            font_size: int = 6
            text: str = self.text_label.text() or self.btn_text

            while font_size < 48:
                font: QFont = self.text_label.font()
                font.setPixelSize(font_size)
                self.text_label.setFont(font)
                metrics = QtGui.QFontMetrics(font)
                height: int = metrics.boundingRect(text).height()
                if height > btn_h - ((self.border_width * 2) + 6):
                    break

                font_size += 1

            self.text_label.height_fontsize[key]: int = font_size
            pos(self.text_label, size=self)

        style(self.text_label, background='transparent', color=text_color, font=font_size, bold=True)
        self.text_label.set_proper_text(text)

    def enterEvent(self, event):
        kwgs: dict = dict(
            border=self.col_border_hover,
            background=self.col_background_hover,
            text_color=self.col_text_hover,
        )
        self.redraw(**kwgs)

    def leaveEvent(self, a0):
        kwgs: dict = dict(
            border=self.col_border_idle,
            background=self.col_background_idle,
            text_color=self.col_text_idle,
        )
        self.redraw(**kwgs)


class RefreshBTN(Button):
    btn_text: str = 'REFRESH'

    def mouseReleaseEvent(self, ev):
        update_and_save_headers()
        self.master.load_pastes()


class LoadBTN(Button):
    btn_text: str = 'LOAD'

    def mouseReleaseEvent(self, ev):
        self.inject_user_credentials()
        self.master.load_pastes()

    def inject_user_credentials(self):
        """hijacking the searchbar to alter the pastebinner settings, key=pastebin.api-key, username=you, password=x"""

        false_or_new_settings: [dict | False] = self.master.searchbar_credentials()
        if false_or_new_settings:
            from tricks.pastebin_api import EASY_REAL
            new_settings: dict = false_or_new_settings
            for easy_key, new_setting in new_settings.items():
                real_key: str = EASY_REAL[easy_key]
                db.save(real_key, new_setting)

            try:
                self.master.settings_helper.close()
            except (AttributeError, RuntimeError):
                ...


class NewBTN(Button):
    btn_text: str = 'NEW'

    def mouseReleaseEvent(self, ev):
        self.master.write_area.qtextedit.clear()
        self.master.rgt_titlebar.searchbar.clear()
        if 'gpg_decrypt_shade' in dir(self.master):
            self.master.gpg_decrypt_shade.suicide()

        self.master.kill_url_label()
        self.reset_publish_btn()

    def reset_publish_btn(self):
        try:
            self.master.shelf.scrollarea.widgets[0].reset_publish_btn()
        except (AttributeError, IndexError):
            ...

class PublishBTN(Button):
    btn_text: str = 'PUBLISH'
    tri_hold: int = 0
    use_newsize: bool = False

    def delete_expander(self):
        try:
            self.expand_label.close()
            delattr(self, 'expand_label')
        except (RuntimeError, AttributeError):
            ...
    def hold_expander(self):
        if self.tri_hold <= 0:
            self.delete_expander()
        else:
            try:
                self.expand_label
            except AttributeError:
                self.create_expand_label()

            if self.expand_label.ready_to_grow():
                bw: int = Button.border_width
                next_w: int = self.expand_label.width() + 1
                largest: int = self.width() - (bw * 2)
                pos(self.expand_label, width=min(next_w, largest))
                if next_w >= largest:
                    self.tri_hold = 2
                    return

            self.master.thread_then_main(main_fn=self.hold_expander, wait=0.01)

    def mousePressEvent(self, ev):
        self.tri_hold = 1
        self.hold_expander()

    def create_expand_label(self):
        if 'expand_label' not in dir(self):

            class ExpandLabel(Base):
                def __init__(self, *args, **kwargs):
                    self.ready_to_grow_least_time: float = time.time() + 0.50
                    super().__init__(*args, **kwargs)

                def ready_to_grow(self) -> bool:
                    return time.time() > self.ready_to_grow_least_time

            self.expand_label = ExpandLabel(self)
            bw: int = Button.border_width
            pos(self.expand_label, width=0, height=self.height() - (bw * 2), top=bw, left=bw)
            style(self.expand_label, background='rgba(250,150,150,150)', border='black 2px')

    def all_text_is_path(self) -> bool:
        text: str = self.master.write_area.qtextedit.toPlainText()
        rows: list = [row.strip() for row in text.split('\n') if row.strip()]
        return rows and all(os.path.exists(row) for row in rows)

    def inserting_encrypted_directories(self) -> int:
        if not self.all_text_is_path():
            return 0

        textedit: QtWidgets.QTextEdit = self.master.write_area.qtextedit
        text: str = textedit.toPlainText()
        rows: list = [row.strip() for row in text.split('\n') if row.strip()]

        dirs: dict = {x.rstrip(os.sep): {} for x in rows if os.path.isdir(x)}
        files: set = {x for x in rows if os.path.isfile(x)}
        src_dst: set[tuple[str, str]] = {(src, f'{src[src.rfind(os.sep) + 1:]}') for src in files}
        for lowest_dir in rows:
            for walk in os.walk(lowest_dir):
                dirs[lowest_dir].update({walk[0]: walk[2]})

        for lowest_dir in dirs:
            blocks: set = set()
            for folder in dirs[lowest_dir]:
                jumpstring: str = folder[len(lowest_dir):]
                parts: list = jumpstring.split(os.sep)
                for part in parts:
                    if part and self.block_foldername(part):
                        jump_ix: int = jumpstring.find(part) + len(part)
                        stay_below: str = lowest_dir + jumpstring[:jump_ix]
                        blocks.add(stay_below)

            for src_dir, files in dirs[lowest_dir].items():
                if any(src_dir.startswith(stay_below) for stay_below in blocks):
                    continue

                target_dname: str = lowest_dir[lowest_dir.rfind(os.sep) + 1:]
                dst_dir: str = f'{target_dname}{os.sep}{src_dir[len(lowest_dir) + 1:]}'.rstrip(os.sep)

                for fname in [fname for fname in files if not self.block_filename(fname)]:
                    src_path: str = f'{src_dir}{os.sep}{fname}'
                    arcname: str = f'{dst_dir}{os.sep}{fname}'
                    src_dst.add((src_path, arcname))

        uncompressed_size: int = sum(os.path.getsize(src) for src, _, in src_dst)
        if uncompressed_size > 200_000_000:
            size_in_gb: float = round(uncompressed_size / 1_000_000_000, 2)
            message: str = f'exceed max work size, no reason to continue. (size: {size_in_gb}gb)'
            print(message)
            self.master.change_window_title(message)
            return -1

        zip_list: list[tuple[str, str]] = list(src_dst)
        zip_list.sort(key=lambda x: x[1])
        zip_list.sort(key=lambda x: x[1].count(os.sep), reverse=True)

        fake_file = io.BytesIO()
        with zipfile.ZipFile(fake_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for src_path, arcname in zip_list:
                zipf.write(src_path, arcname=arcname)

        fake_file.seek(0)
        zip_data: bytes = fake_file.read()
        keyid: str = self.master.gpg_bar.current_key
        encrypted_armor: str = encrypt_binary(zip_data, keyid) if (keyid and zip_data) else ""
        if not encrypted_armor or encrypted_armor == text:
            message: str = f'problem while encrypting zipfile, abort'
            print(message)
            self.master.change_window_title(message)
            return -1

        headlist: list = []
        compressed_size: int = 0
        for info in zipfile.ZipFile(fake_file).filelist:
            compressed_size += info.compress_size
            arcname: str = str(info.filename)
            org_size: str = str(info.file_size)
            new_size: str = str(info.compress_size)
            headlist.append((arcname, org_size, new_size))

        if compressed_size > 9_900_000:
            size_in_gb: float = round(compressed_size / 1_000_000, 2)
            message: str = f'exceed max compressed size, no reason to continue. (size: {size_in_gb}mb)'
            print(message)
            self.master.change_window_title(message)
            return -1

        max_arcname: int = max(len(x[0]) for x in headlist)
        max_orgsize: int = max(len(x[1]) for x in headlist)
        max_newsize: int = max(len(x[2]) for x in headlist)

        headstring: str = ""
        for arcname, org_size, new_size in headlist:
            arcname_space: str = f'{arcname}{" " * (max_arcname - len(arcname))}'
            orgsize_space: str = f'{" " * (max_orgsize - len(org_size))}{org_size}'
            newsize_space: str = f'{" " * (max_newsize - len(new_size))}{new_size}'
            if self.use_newsize:
                headstring += f'{arcname_space} {orgsize_space} bytes {newsize_space} bytes\n'
            else:
                headstring += f'{arcname_space} {orgsize_space} bytes\n'

        mb_int: int = int(compressed_size / 1_000_000)
        if mb_int:
            kb_int: int = round(compressed_size - (mb_int * 1_000_000), 3)
            kb_str: str = f'{kb_int}0'
            size_txt: str = f'{mb_int}.{kb_str[:2]} MB'
        elif compressed_size // 1000:
            kb_str: str = f'{round(compressed_size / 1000)}'
            size_txt: str = f'{kb_str} KB'
        else:
            size_txt: str = f'{compressed_size} bytes'

        new: str = f'{headstring}\nTOTAL: {size_txt}\n\n{encrypted_armor}'
        textedit.setPlainText(new)

        return 1

    def block_foldername(self, string: str) -> bool:
        return any(string.startswith(x) for x in FOLDER_STARTSWITH_BLOCK)

    def block_filename(self, f: str) -> bool:
        return any(f.startswith(x) for x in FILE_STARTSWITH_BLOCK) or any(f.endswith(x) for x in FILE_EXTENSION_BLOCK)

    def mouseReleaseEvent(self, ev):
        treated_text: int = 0
        blocked_ongoing_press: bool = self.tri_hold > 0 and ev.button().value != 1
        blocked_by_user: bool = self.tri_hold == -1
        textscout_for_filesfolders: bool = self.tri_hold == 2
        self.tri_hold = 0
        self.delete_expander()

        if blocked_ongoing_press:
            self.tri_hold = -1
            return

        elif blocked_by_user:
            return

        elif textscout_for_filesfolders:
            treated_text = self.inserting_encrypted_directories()
            if treated_text == -1:
                return

        elif self.all_text_is_path():
            reminder_text: str = 'AGAIN!!'
            if self.text_label.text() != reminder_text:
                self.text_label.set_proper_text(reminder_text)
                return
            else:
                treated_text = self.inserting_encrypted_directories()
                if treated_text == -1:
                    return

        self.text_label.set_proper_text(self.btn_text)

        title: str = self.master.rgt_titlebar.searchbar.text() or "untitled"
        text: str = self.master.write_area.qtextedit.toPlainText()
        priv_val: int = db.load_setting(self.master.privacy_btn.load_save_var)
        if priv_val not in self.master.privacy_btn.trans:
            priv_val = max(self.master.privacy_btn.trans.keys())

        expire: [str | any] = db.load_setting(self.master.expire_btn.load_save_var)
        if expire not in self.master.expire_btn.options:
            expire = 'N'

        keyid: str = self.master.gpg_bar.current_key
        if keyid_in_keyring(keyid) and not treated_text:
            treated_text: str = encrypt_text(text, keyid)
            if treated_text == text:
                style(self.master.gpg_bar.text_label, background='red', border='black')
                fn = lambda: style(self.master.gpg_bar.text_label, background='transparent', border='transparent')
                self.master.thread_then_main(wait=5.0, main_fn=fn)
                return
        else:
            treated_text: str = text

        kwgs: dict = dict(title=title, text=treated_text, priv_val=priv_val, expire=expire)
        response: [str | None] = publish_paste(**kwgs)
        if '/' not in (response or ""):
            return

        key: str = response[response.rfind('/') + 1:]
        epoch: int = int(time.time())

        q, v = db.query_values('pastes')
        v[Pastes.date]: int = epoch
        v[Pastes.data]: str = treated_text
        v[Pastes.format_short]: str = 'text'
        v[Pastes.key]: str = key
        v[Pastes.missing]: bool = False
        v[Pastes.private]: int = priv_val
        v[Pastes.size]: int = len(treated_text)
        v[Pastes.title]: str = title
        v[Pastes.url]: int = response
        if expire not in 'N':
            v[Pastes.expire_date]: int = epoch + self.master.expire_btn.options[expire]['ticks']


        with db.connection:
            q_del: str = 'delete from pastes where key is (?)'
            v_del: tuple = key,
            db.cursor.execute(q_del, v_del)

            vals: tuple = tuple(v)
            db.cursor.execute(q, vals)

        q: str = 'select * from pastes where key is (?)'
        v: tuple = key,
        recent_paste: [tuple | None] = db.cursor.execute(q, v).fetchone()

        widgets: list = self.master.shelf.scrollarea.widgets
        if len(widgets) <= 2 or not recent_paste:
            self.master.load_pastes()
        else:
            tops: list = [x.geometry().top() for x in widgets]
            tops.sort()
            y_delta: int = tops[1] - tops[0]
            top: int = min(tops)
            left: int = widgets[0].geometry().left()
            w: int = widgets[0].width()
            h: int = widgets[0].height()
            for i in widgets:
                pos(i, move=[0, y_delta])

            kwgs: dict = dict(widgets=widgets, paste=recent_paste)
            header: PasteHeader = PasteHeader(self.master.shelf.scrollarea.canvas, self.master, **kwgs)
            pos(header, size=[w, h], left=left, top=top)
            header.init_draw()
            widgets.append(header)
            self.master.shelf.scrollarea.expand()

        self.master.change_window_title(f'new paste created {response}')
        self.master.show_url_label(response)


class PrivacyBTN(Button):
    load_save_var: str = 'privacy_settings'
    btn_text: str = 'PRIVACY'
    trans: dict = {0: 'PUBLIC', 1: 'SECRET', 2: 'PRIVATE'}
    coating_rgba: dict = {0: 'rgba(200,0,0,25)', 1: 'rgba(0,200,0,25)', 2: 'rgba(0,0,200,25)'}

    def mouseReleaseEvent(self, ev):
        privacy: [int | any] = db.load_setting(self.load_save_var)
        try:
            if ev.button().value == 1:
                if privacy >= max(self.trans.keys()):
                    privacy = min(self.trans.keys())
                else:
                    privacy += 1
            else:
                if privacy <= min(self.trans.keys()):
                    privacy = max(self.trans.keys())
                else:
                    privacy -= 1
        except (TypeError, ValueError):
            privacy = max(self.trans.keys())

        self.change_save_and_visualize(privacy=privacy)

    def change_save_and_visualize(self, privacy: int):
        db.save_setting(self.load_save_var, privacy)
        self.show_privacy()

    def init_draw(self):
        super().init_draw()
        self.show_privacy()

    def show_privacy(self):
        privacy: [int | any] = db.load_setting(self.load_save_var)
        if privacy is None:
            privacy = max(self.trans.keys())
            db.save_setting(self.load_save_var, privacy)

        try:
            text: str = self.trans[privacy]
        except KeyError:
            privacy = max(self.trans.keys())
            text: str = self.trans[privacy]

        self.text_label.set_proper_text(text)

        try:
            self.text_label.color_coating
        except AttributeError:
            bw: int = Button.border_width
            self.text_label.color_coating = Base(self)
            self.text_label.color_coating.lower()
            pos(self.text_label.color_coating, size=self.text_label, sub=bw * 2, top=bw, left=bw)

        style(self.text_label.color_coating, background=self.coating_rgba[privacy])


class ExpireBTN(Button):
    btn_text: str = 'NEVER EXPIRE'
    load_save_var: str = 'expire_value'
    options: dict = {
        'N': dict(text='NEVER EXPIRE', key='N', ticks=0),
        '10M': dict(text='10 MINUTES', key='10M', ticks=60 * 10),
        '1H': dict(text='1 HOUR', key='1H', ticks=60 * 60),
        '1D': dict(text='1 DAY', key='1D', ticks=86400),
        '1W': dict(text='1 WEEK', key='1W', ticks=86400 * 7),
        '2W': dict(text='2 WEEKS', key='2W', ticks=86400 * 14),
        '1M': dict(text='1 MONTH', key='1M', ticks=86400 * 30),
        '6M': dict(text='6 MONTHS', key='6M', ticks=86400 * 180),
        '1Y': dict(text='1 YEAR', key='1Y', ticks=86400 * 365),
    }

    def mouseReleaseEvent(self, ev):
        key: [str | any] = db.load_setting(self.load_save_var) or 'N'
        try:
            current_box: dict = self.options[key]
        except KeyError:
            self.change_save_and_visualize(key='N')
            return

        increase: bool = ev.button().value == 1
        cycle_options: list = [v for _, v in self.options.items()]
        cycle_options.sort(key=lambda x:x['ticks'], reverse=not increase)
        for box in cycle_options:

            if increase and box['ticks'] > current_box['ticks']:
                new_key: str = box['key']
                break

            elif not increase and box['ticks'] < current_box['ticks']:
                new_key: str = box['key']
                break
        else:
            new_key: str = cycle_options[0]['key']

        self.change_save_and_visualize(key=new_key)


    def change_save_and_visualize(self, key: str):
        db.save_setting(self.load_save_var, key)
        self.show_expire()

    def init_draw(self):
        super().init_draw()
        self.show_expire()

    def show_expire(self):
        key: [str | any] = db.load_setting(self.load_save_var)
        if key is None:
            key = 'N'
            db.save_setting(self.load_save_var, key)

        try:
            text: str = self.options[key]['text']
        except KeyError:
            text: str = self.options['N']['text']

        self.text_label.set_proper_text(text)

class GPGBar(Button):
    btn_text: str = "......................".upper()
    keys: list = []
    load_save_var: str = 'current_gpg_key'
    current_key: str = '-1'

    def init_draw(self):
        self.create_text_label()
        self.show_gpg_keys()

        kwgs: dict = dict(
            border=self.col_border_idle,
            background=self.col_background_idle,
            text_color=self.col_text_idle,
        )
        self.redraw(**kwgs)

    def mouseReleaseEvent(self, ev):
        key_id: str = self.current_key
        dummy: dict = dict(keyid='-1', uids=[self.btn_text])

        for count in range(len(self.keys)):
            box: dict = self.keys[count]
            if self.current_key in box['keyid']:
                if ev.button().value == 1:
                    if (count + 1) == len(self.keys):
                        box = dummy
                    else:
                        box = self.keys[count + 1]
                else:
                    if count == 0:
                        box = dummy
                    else:
                        box = self.keys[count - 1]

                key_id = box['keyid']
                break
        else:
            for box in self.keys:
                key_id = box['keyid']
                break

        if key_id != self.current_key:
            db.save_setting(self.load_save_var, key_id)
            self.show_gpg_keys()

    def show_gpg_keys(self):
        if not self.keys:
            self.keys += [x for x in get_gpg_keys()]

        current_key: [str | None] = db.load_setting(self.load_save_var)
        if isinstance(current_key, str):
            self.current_key = current_key

        text: str = self.btn_text
        for box in self.keys:
            if self.current_key in box['keyid']:
                text = box['uids'][0]
                break

        self.text_label.set_proper_text(text)

class URLBTN(Button):
    btn_text: str = ''

    def mouseReleaseEvent(self, ev):
        if ev.button().value != 1:
            self.hide()

