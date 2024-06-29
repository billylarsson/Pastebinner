from PIL                 import Image
from PIL.ImageDraw       import ImageDraw
from tricks.cutout       import Cutouter
from tricks.database     import Pastes, db
from tricks.gpgthings    import decrypt_armor
from tricks.pastebin_api import download_paste
from tricks.techs        import tmpfile
import io, os


SPECIAL_PRIVACY_TITLE: str = 'Pastebinner WEBP privacy images'

class GrabImages:
    less_cool_images: dict = {}

    def __call__(self, priv_var: str, *args, **kwargs) -> [Image.Image | None]:
        priv_im: [None | Image.Image] = db.load_image(priv_var)
        return priv_im or self.grab_hidden_paste(priv_var) or self.random_new_image(priv_var)

    def random_new_image(self, priv_var: str):
        try:
            return self.less_cool_images[priv_var]
        except KeyError:

            from widgets import add, sub
            im: Image.Image = Image.new('RGB', (100, 60), (0, 0, 0, 0))
            draw: ImageDraw = ImageDraw(im)

            rgt: int = im.width - 1
            btm: int = im.height - 1

            if 'max' in priv_var:
                r, g, b, a = 150, 80, 50, 255
            elif 'min' in priv_var:
                r, g, b, a = 50, 110, 70, 255
            else:
                r, g, b, a = 10, 80, 150, 255

            for cnr in range(min(im.width, im.height) // 2):
                r: int = add(r, factor=0.03)
                g: int = add(g, factor=0.03)
                b: int = add(b, factor=0.03)

                lighter_rgba: tuple = r, g, b, a,
                square_xy: tuple = cnr, cnr, rgt - cnr, btm - cnr,
                rect_work: list = [(square_xy, lighter_rgba)]

                darker_rgba: tuple = sub(r, factor=0.2), sub(g, factor=0.2), sub(b, factor=0.2), a,
                s_wall: tuple = cnr, btm - cnr, rgt - cnr, btm - cnr,
                e_wall: tuple = rgt - cnr, cnr, rgt - cnr, btm - cnr,
                line_work: list = [(s_wall, darker_rgba), (e_wall, darker_rgba)]

                for xy, rgba in rect_work:
                    draw.rectangle(xy, rgba)

                for xy, rgba in line_work:
                    draw.line(xy, rgba)

            self.less_cool_images[priv_var] = im
            return self.less_cool_images[priv_var]

    def grab_hidden_paste(self, priv_var: str) -> [Image.Image | None]:
        header: str = f'[{priv_var}]'
        path: str = tmpfile(fname=header, ext='webp')
        if os.path.exists(path):
            try:
                im: Image.Image = Image.open(path)
                db.save_image(var=priv_var, im=im, w=im.width, h=im.height)
                return im
            except:
                try:
                    os.remove(path)
                except (PermissionError, FileNotFoundError):
                    print(f'{SPECIAL_PRIVACY_TITLE}, couldnt delete: {path}')

        q: str = 'select * from pastes where title is (?)'
        v: tuple = SPECIAL_PRIVACY_TITLE,
        data: list = db.cursor.execute(q, v).fetchall()
        for paste in [x for x in data]:
            if not paste[Pastes.data]:
                key: str = data[Pastes.key]
                text: str = download_paste(paste_key=key)
                if text:
                    data = db.cursor.execute(q, v).fetchall()
                    update_q: str = 'update pastes set data = (?) where id is (?)'
                    update_v: tuple[int] = paste[Pastes.id],
                    with db.connection:
                        db.cursor.execute(update_q, update_v)

        for text in [x[Pastes.data] for x in data if header in (x[Pastes.data] or "")]:
            begin_str: str = '-----BEGIN PGP MESSAGE-----'
            end_str: str = '-----END PGP MESSAGE-----'
            co = Cutouter(text, first_find=[header, begin_str], then_find=end_str)
            if bool(co):
                cont: str = f'{begin_str}{co.text}{end_str}'
                webp_image: bytes = decrypt_armor(cont, into_bytes=True)
                if webp_image != b'':
                    try:
                        fake_file = io.BytesIO()
                        fake_file.write(webp_image)
                        fake_file.seek(0)
                        im: Image.Image = Image.open(fake_file)
                        db.save_image(var=priv_var, im=im, w=im.width, h=im.height)
                        return im
                    except:
                        print(f'{SPECIAL_PRIVACY_TITLE}, couldnt load: {header}')


grabimages: GrabImages = GrabImages()