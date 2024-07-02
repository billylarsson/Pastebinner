from PyQt6               import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets     import QApplication
from tricks.buttons      import ExpireBTN, GPGBar, LoadBTN, NewBTN, PrivacyBTN
from tricks.buttons      import PublishBTN, RefreshBTN, URLBTN
from tricks.database     import Pastes, db
from tricks.pastebin_api import EASY_REAL
from tricks.searchbars   import LeftSearchBar, RightTitleBar
from tricks.shelf        import Shelf, WriteArea
from tricks.smartpos     import pos
from tricks.styles       import style
from tricks.threadpool   import CustomThreadPool, ThreadThenMain
from tricks.widgets      import Base, PasteHeader
import sys, time, os


save_flag: str = '--save'
user_flags: str = f"\n{save_flag} permanently stores credentials, not recommended!\npython {__file__}"
for easy in EASY_REAL:
    if 'key' in easy:
        user_flags += f' --{easy}=your_apikey'
    elif 'user' in easy:
        user_flags += f' --{easy}=your_username'
    elif 'password' in easy:
        user_flags += f' --{easy}=your_password'

    var: str = f'--{easy}='
    for flag in sys.argv[1:]:
        if flag.startswith(var):
            useradds: str = flag[len(var):]
            save_key: str = EASY_REAL[easy]
            for user_args in sys.argv[1:]:
                if user_args.lower().startswith(save_flag):
                    db.save(save_key, useradds)
                    break
            else:
                os.environ[save_key]: str = useradds


print(user_flags, f'(optional: {save_flag})', '\n')


class Main(QtWidgets.QMainWindow):
    credentials_provided: bool = all(db.load_setting(real) is not None for _, real in EASY_REAL.items())

    def __init__(self, qapplication):
        self._qapplication = qapplication
        self.thread_then_main = ThreadThenMain()
        self.main_then_main = CustomThreadPool()
        super().__init__()
        self.change_window_title('Pastebinner v0.something-something ...')
        self.show()

        def fn1():
            self.screen_starting_geometry(x_factor=0.7, fixed=True)

        def fn2():
            self.startup()

        self.main_then_main(executable1_fn=fn1, executable2_fn=fn2, wait=0.1)
        #self.thread_then_main(wait=13.0, main_fn=lambda: sys.exit())

    def startup(self):
        self.shelf = Shelf(master=self)
        self.write_area = WriteArea(master=self)
        style(self.shelf, background='black')
        style(self.write_area, background='gray')

        self.refresh_btn = RefreshBTN(self)
        self.load_btn = LoadBTN(self)
        self.publish_btn = PublishBTN(self)
        self.privacy_btn = PrivacyBTN(self)
        self.lft_searchbar = LeftSearchBar(self)

        self.new_btn = NewBTN(self)
        self.expire_btn = ExpireBTN(self)
        self.rgt_titlebar = RightTitleBar(self)
        self.gpg_bar = GPGBar(self)

        self.reorganize_widgets()


        self.load_pastes()

        shortcut_fn = lambda: self.show_missing_setting_helper(True)
        self.help_shortcut = QtGui.QShortcut(QtGui.QKeySequence('F1'), self)
        self.help_shortcut.activated.connect(shortcut_fn)

    def show_missing_setting_helper(self, override: bool = False):
        if 'settings_helper' in dir(self):
            try:
                self.settings_helper.close()
            except (AttributeError, RuntimeError):
                ...
            finally:
                return

        elif not override and self.credentials_provided:
            return

        class SettingsHelper(Base):

            def mouseReleaseEvent(self, ev):
                self.lower()
                self.master.master.lft_searchbar.searchbar.setFocus()

            def closeEvent(self, a0):
                org_text: str = self.master.master.load_btn.btn_text
                self.master.master.load_btn.text_label.set_proper_text(org_text)
                try:
                    del self.master.master.settings_helper
                except (AttributeError, RuntimeError):
                    ...

        tooltip: str = "WRITE YOUR CREDENTIALS HERE"
        tooltip += "\nwrite them such as password=qwerty1234 for password just typing qwerty1234 wont work"
        tooltip += "\nyou must provide ALL credentials in a single string before they can be accepted by the system"
        tooltip += "\nonce credentials are provided, save the them by hitting the LOAD/SAVE button to the left"

        self.settings_helper: Base = SettingsHelper(self.lft_searchbar)
        self.settings_helper.setToolTip(tooltip)

        pos(self.settings_helper, size=self.lft_searchbar)
        style(self.settings_helper, background='rgb(200,200,200)', color='gray', border='black 3px', font=8)
        style(self.settings_helper, background='white', color='black', border='black', tooltip=True)

        vars: list = []
        for var in EASY_REAL:
            if 'key' in var:
                vars.append(f'{var}=your_apikey')
            elif 'user' in var:
                vars.append(f'{var}=your_username')
            elif 'password' in var:
                vars.append(f'{var}=your_password')

        help_text: str = "EXAMPLE:   " + "   ".join(vars)
        self.settings_helper.setText(help_text)


    def searchbar_credentials(self) -> [bool | dict]:
        text: str = self.lft_searchbar.searchbar.text()
        new_settings: dict = {k: None for k in EASY_REAL.keys()}
        for easy_key in EASY_REAL.keys():
            for any_key in easy_key, EASY_REAL[easy_key]:
                target: str = f'{any_key}='
                if target in text.lower():
                    ix: int = text.lower().find(target) + len(target)
                    str_val: str = ""
                    for char in text[ix:]:
                        if char not in ' ':
                            str_val += char
                        else:
                            break

                    new_settings[easy_key]: [str | None] = str_val or None

        all_present: bool = all(val is not None for _, val in new_settings.items())
        if all_present:
            self.load_btn.text_label.set_proper_text(text='SAVE')
            return new_settings
        else:
            return False
    def reorganize_widgets(self):
        void: int = 2
        top: int = void
        left: int = void
        btn_h: int = 32
        btn_w: int = 150

        pos(self.refresh_btn, left=left, top=top, size=[btn_w, btn_h])
        [x.init_draw() for x in (self.refresh_btn,)]
        pos(self.load_btn, after=self.refresh_btn, size=[btn_w, btn_h], x_offset=1)
        [x.init_draw() for x in (self.load_btn,)]

        reach: dict = dict(bottom=self.height() - (void * 2))
        w: int = (self.width() // 2) - (void * 4)
        kwgs: dict = dict(below=self.refresh_btn, width=w, reach=reach, y_offset=void)
        pos(self.shelf, **kwgs, left=left)
        pos(self.write_area, **kwgs, right=self.width() - void)
        reach: dict = dict(bottom=self.height() - (void * 2) - btn_h)
        pos(self.write_area, reach=reach)
        [x.init_draw() for x in (self.shelf, self.write_area,)]

        pos(self.privacy_btn, size=[btn_w, btn_h], below=self.write_area, y_offset=void)
        [x.init_draw() for x in (self.privacy_btn,)]
        pos(self.expire_btn, size=[btn_w, btn_h], after=self.privacy_btn, x_offset=void)
        [x.init_draw() for x in (self.expire_btn,)]

        reach = dict(right=self.shelf.geometry().right() - 1)
        pos(self.lft_searchbar, height=btn_h, after=self.load_btn, x_offset=void, reach=reach)
        [x.init_draw() for x in (self.lft_searchbar,)]

        kwgs: dict = dict(top=self.lft_searchbar, left=self.write_area)
        pos(self.new_btn, size=[btn_w, btn_h], **kwgs)
        [x.init_draw() for x in (self.new_btn,)]
        pos(self.publish_btn, size=[btn_w, btn_h], after=self.new_btn, x_offset=void)
        [x.init_draw() for x in (self.publish_btn,)]

        reach: dict = dict(right=self.write_area.geometry().right())
        pos(self.rgt_titlebar, after=self.publish_btn, height=self.lft_searchbar, x_offset=void, reach=reach)
        [x.init_draw() for x in (self.rgt_titlebar,)]

        reach: dict = dict(right=self.rgt_titlebar.geometry().right())
        pos(self.gpg_bar, after=self.expire_btn, height=self.expire_btn, reach=reach)
        self.gpg_bar.init_draw()

    def screen_starting_geometry(self,
                                 x_factor: float = 0.8,
                                 y_factor: float = 0.8,
                                 primary: bool = True,
                                 fixed: bool = False,
                                 ):

        for screen in self._qapplication.screens():
            primary_screen: bool = screen == QtGui.QGuiApplication.primaryScreen()
            criteria1: bool = primary and primary_screen
            criteria2: bool = not primary and not primary_screen
            if not criteria1 and not criteria2:
                continue

            x: int = screen.geometry().left()
            y: int = screen.geometry().top()
            w: int = screen.geometry().width()
            h: int = screen.geometry().height()

            x_bleed: int = (w - int(w * x_factor)) // 2
            y_bleed: int = (h - int(h * y_factor)) // 2

            new_w: int = int(w * x_factor) or 1280
            new_h: int = int(h * y_factor) or 768

            x_cent: int = x_bleed + x
            y_cent: int = y_bleed + y

            if not fixed:
                self.setGeometry(x_cent, y_cent, new_w, new_h)
            else:
                self.setFixedSize(new_w, new_h)
                self.move(x_cent, y_cent)
            break
        else:
            self.setGeometry(0, 0, 1280, 768)  # fallback

    def paste_size(self) -> tuple:
        void: int = self.height() - (self.shelf.geometry().bottom() - 1)
        bw: int = LoadBTN.border_width
        w: int = self.shelf.scrollarea.canvas.width() - ((bw * 3) + (void * 2))
        h: int = 40
        return w, h

    def load_pastes(self):
        widgets: list = self.shelf.scrollarea.widgets
        q: str = 'select * from pastes where missing is not 1'
        pastes: list = db.cursor.execute(q).fetchall()
        pastes.sort(key=lambda x:x[Pastes.date], reverse=True)

        for count in range(len(widgets) - 1, -1, -1):
            widgets[count].close()
            widgets.pop(count)

        self.paste_queue: list = [dict(paste=paste, drawn=False) for paste in pastes]
        self.draw_next_paste()

    def draw_next_paste(self):
        widgets: list = self.shelf.scrollarea.widgets
        void: int = self.height() - (self.shelf.geometry().bottom() - 1)
        bw: int = LoadBTN.border_width
        w, h = self.paste_size()

        for queue_box in self.paste_queue:
            if queue_box['drawn']:
                continue

            queue_box['drawn']: bool = True
            kwgs: dict = dict(widgets=widgets, paste=queue_box['paste'])
            header: PasteHeader = PasteHeader(self.shelf.scrollarea.canvas, self, **kwgs)
            if widgets:
                pos(header, size=[w, h], below=widgets[-1], y_offset=0)
            else:
                pos(header, size=[w, h], left=bw, top=bw, x_offset=void, y_offset=void)

            widgets.append(header)
            header.init_draw()
            self.main_then_main(executable1_fn=self.shelf.scrollarea.expand, executable2_fn=self.draw_next_paste)
            break

    def show_url_label(self, url: str):
        self.kill_url_label()
        self.url_label = URLBTN(self, monospace=True)
        self.url_label.btn_text = url
        pos(self.url_label, size=self.gpg_bar, above=self.privacy_btn, y_offset=7, x_offset=6)
        self.url_label.init_draw()
        flag = QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        self.url_label.text_label.setTextInteractionFlags(flag)

        class Hider(Base):
            def mousePressEvent(self, ev):
                self.master.text_label.mousePressEvent(ev)

            def mouseMoveEvent(self, ev):
                try:
                    self.master.text_label.mouseMoveEvent(ev)
                except AttributeError:
                    ...

            def mouseReleaseEvent(self, ev):
                if ev.button().value != 1:
                    text: str = self.master.text_label.selectedText()
                    if text:
                        QtWidgets.QApplication.clipboard().setText(text)
                        self.master.master.change_window_title(f'{text} copied to clipboard ...')
                    self.master.hide()

        self.url_label.rightclicker = Hider(self.url_label)
        pos(self.url_label.rightclicker, size=self.url_label)
        style(self.url_label.rightclicker, background='transparent')

    def kill_url_label(self):
        if 'url_label' in dir(self):
            try:
                self.url_label.close()
                del self.url_label
            except (AttributeError, RuntimeError):
                ...

    def change_window_title(self, title: str, delay: float = 5.0):
        try:
            self.org_title
        except AttributeError:
            self.org_title: str = title
            self.setWindowTitle(title)
            return

        self.setWindowTitle(title)
        sleeper = lambda: time.sleep(delay)
        shower = lambda: self.setWindowTitle(self.org_title)
        self.thread_then_main(sleeper, shower)

if '__main__' in __name__:
    app = QApplication(sys.argv)
    ui = Main(qapplication=app)
    app.exec()
