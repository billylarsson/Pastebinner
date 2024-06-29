from PIL import Image
import io, os, pathlib, pickle, sqlite3

def get_db_path() -> str:
    parts: list = __file__.split(os.sep)
    ending: str = f'{os.sep}database.sqlite'
    db_primary_dir: str = os.path.expanduser("~") + os.sep + 'Documents'
    db_secondary_dir: str = os.sep.join(parts[:-1])
    if os.path.exists(db_primary_dir):
        APPNAME: str = __file__.split(os.sep)[-3] or "_fallback1!"
        db_primary_dir += (os.sep + APPNAME)
        if not os.path.exists(db_primary_dir):
            try:
                pathlib.Path(db_primary_dir).mkdir(parents=True, exist_ok=True)
            except PermissionError:
                ...
    return (db_primary_dir + ending) if os.path.exists(db_primary_dir) else (db_secondary_dir + ending)

DB_PATH: str = get_db_path()

class Settings:
    ...


class Pastes:
    ...


class DB:
    def __init__(self, path: str):
        self.establish_connection(path)
        self.create_tables_and_columns()
        self.bind_all_enums()

    def establish_connection(self, path: str):
        if not os.path.exists(path):
            try:
                with open(path, 'w'):
                    ...
                print(f'"{path}" didnt exist therefore an empty file was created')
            except PermissionError:
                print(f'no persmission to access "{path}" therefore sqlite will only work in memory')
                self.connection = sqlite3.connect(':memory:')
                self.cursor = self.connection.cursor()
        try:
            self.connection = sqlite3.connect(path)
            self.cursor = self.connection.cursor()
        except:
            print(f'couldnt connect to "{path}" therefore a memory connection will be provided')
            self.connection = sqlite3.connect(':memory:')
            self.cursor = self.connection.cursor()

    @staticmethod
    def type_to_string(val: any) -> str:
        if val == float:
            return 'FLOAT'
        elif val == int:
            return 'INTEGER'
        elif val == bool:
            return 'BINT'
        elif val == bytes:
            return 'BLOB'
        else:
            return 'TEXT'

    def create_tables_and_columns(self):
        q: str = "SELECT name FROM sqlite_master WHERE type='table'"
        tmp_data: list = self.cursor.execute(q).fetchall()
        tables = {k[0] for k in tmp_data if 'sqlite_sequence' not in k}

        jobs: list = self.default_integrity()
        for job in jobs:

            table: str = job['table_name']
            name_type: dict = job['columns']
            auto: bool = job.get('auto', False)

            if table not in tables:
                colname_typestring: list = [f'{k} {self.type_to_string(v)}' for k, v in name_type.items()]
                colname_typestring.sort()
                colname_typestring.insert(0, 'id INTEGER PRIMARY KEY AUTOINCREMENT') if auto else ...
                col_string: str = f'({', '.join(colname_typestring)})'
                q: str = f'create table {table} {col_string}'
                with self.connection:
                    self.cursor.execute(q)
            else:
                q_pragma: str = f'PRAGMA table_info({table})'
                cols: dict = {x[1]: x[0] for x in self.cursor.execute(q_pragma).fetchall()}

                if auto and 'id' not in cols:
                    q: str = f'select * from {table}'
                    backup_data: list = self.cursor.execute(q).fetchall()
                    for rewcount in range(len(backup_data)):
                        backup: list = [None] + list(backup_data[rewcount])
                        backup_data[rewcount]: tuple = tuple(backup)

                    with self.connection:
                        q: str = f'drop table {table}'
                        self.cursor.execute(q)

                    with self.connection:
                        colname_typestring: list = [f'{k} {self.type_to_string(v)}' for k, v in name_type.items()]
                        colname_typestring.sort()
                        colname_typestring.insert(0, 'id INTEGER PRIMARY KEY AUTOINCREMENT')
                        col_string: str = f'({', '.join(colname_typestring)})'
                        q: str = f'create table {table} {col_string}'
                        self.cursor.execute(q)

                    with self.connection:
                        q, _ = self.query_values(table)
                        self.cursor.executemany(q, backup_data)

                for col, coltype in name_type.items():
                    if col in cols:
                        continue

                    q: str = f'alter table {table} add column {col} {self.type_to_string(coltype)}'
                    with self.connection:
                        self.cursor.execute(q)

    def bind_all_enums(self):
        jobs: list = self.default_integrity()
        for job in jobs:
            table: str = job['table_name']
            bind_to: object = job['bind_to']
            q_pragma: str = f'PRAGMA table_info({table})'
            cols: dict = {x[1]: x[0] for x in self.cursor.execute(q_pragma).fetchall()}
            [setattr(bind_to, k, v) for k, v in cols.items()]

    def query_values(self, table: str) -> tuple:
        pragmas: list = self.cursor.execute(f'PRAGMA table_info({table})').fetchall()
        table_len: int = len(pragmas)
        marks: list = ['?' for _ in range(table_len)]
        q: str = f'insert into {table} values({','.join(marks)})'
        v: list = [None for _ in range(table_len)]
        return q, v

    def default_integrity(self) -> list:
        """should be overruled by the child at all times"""
        return []


class PastebinnerDB(DB):

    def default_integrity(self) -> list:
        job: list = [
            dict(
                table_name='pastes',
                auto=False,
                bind_to=Pastes,
                columns={
                    'date': int,
                    'missing': bool,
                    'key': str,
                    'title': str,
                    'size': int,
                    'expire_date': int,
                    'private': int,
                    'format_long': str,
                    'format_short': str,
                    'url': str,
                    'hits': int,
                    'data': str,
                },
            ),
            dict(
                table_name='settings',
                auto=True,
                bind_to=Settings,
                columns={
                    'datas': bytes,
                    'images': bytes,
                },
            ),
        ]
        return job

    def get_settings(self) -> dict:
        try:
            return self._settings
        except AttributeError:
            self.create_pickled_storages('_settings', 'datas')
            return self._settings

    def get_images(self) -> dict:
        try:
            return self._images
        except AttributeError:
            self.create_pickled_storages('_images', 'images')
            return self._images
    def create_pickled_storages(self, variable: str, db_column: str):
        box: dict = {}
        setattr(self, variable, box)
        q: str = f'select {db_column} from settings order by id desc limit 1'
        data: [tuple | None] = db.cursor.execute(q).fetchone()
        if data:
            raw_data: bytes = data[0]
            try:
                unpickled: dict = pickle.loads(raw_data)
                [box.update({k: v}) for k,v in unpickled.items()]
            except:
                print(f'error while trying to unpickle settings data, a blank one has been provided instead')
        else:
            print(f'no settings has been fetched therefore a blank settingsdata will be inserted')
            q, v = db.query_values(table='settings')
            v[getattr(Settings, db_column)]: bytes = pickle.dumps(box)
            with db.connection:
                db.cursor.execute(q, v)


    def load_setting(self, var: any) -> any:
        settings: dict = self.get_settings()
        return settings.get(var, None)

    def save_setting(self, var: any, val: any):
        settings: dict = self.get_settings()
        if var in settings and settings[var] == val:
            return

        settings[var]: any = val

        q1: str = 'select id from settings order by id desc limit 1'
        v1: tuple = db.cursor.execute(q1).fetchone()

        q2: str = 'update settings set datas = (?) where id is (?)'
        v2: tuple = pickle.dumps(settings), v1[0],

        with db.connection:
            db.cursor.execute(q2, v2)

    def load_image(self, var: any) -> [Image.Image | None]:
        images: dict = self.get_images()
        try:
            unpacked_images: dict = self._unpacked_images
        except AttributeError:
            self._unpacked_images: dict = {}
            unpacked_images: dict = self._unpacked_images

        try:
            return unpacked_images[var]
        except KeyError:
            webp_image: [bytes | None] = images.get(var, None)
            if not webp_image:
                unpacked_images[var] = None
            else:
                try:
                    fake_file = io.BytesIO()
                    fake_file.write(webp_image)
                    fake_file.seek(0)
                    im: Image.Image = Image.open(fake_file)
                    unpacked_images[var] = im
                except:
                    unpacked_images[var] = None

            return unpacked_images[var]

    def save_image(self,
                   var: any,
                   path: [str | None] = None,
                   im: [Image.Image | None] = None,
                   w: int = 300,
                   h: int = 200,
                   quality: int = 80,
                   ):
        if path:
            try:
                im = Image.open(path)
            except:
                ...
        if not im:
            print(f'couldnt load {path if path else "Image"}')
            return

        images: dict = self.get_images()
        make_thumb: bool = im.width > w or im.height > h
        if not make_thumb and path:
            with open(path, 'rb') as f:
                blob: bytes = f.read()
        else:
            size: tuple = min(w, im.width), min(h, im.height)
            im.thumbnail(size, resample=Image.Resampling.LANCZOS)
            fake_file = io.BytesIO()
            im.save(fake_file, 'WEBP', method=6, quality=quality)
            fake_file.seek(0)
            blob: bytes = fake_file.read()

        images[var]: bytes = blob
        present_images: dict = {k: v for k,v in images.items() if v is not None}

        q1: str = 'select id from settings order by id desc limit 1'
        v1: tuple = db.cursor.execute(q1).fetchone()

        q2: str = 'update settings set images = (?) where id is (?)'
        v2: tuple = pickle.dumps(present_images), v1[0],

        with db.connection:
            db.cursor.execute(q2, v2)

        # REMOVES "NONE" FROM SMART CACHE
        self._unpacked_images.pop(var) if ('_unpacked_images' in dir(self) and var in self._unpacked_images) else ...


    def save(self, *args, **kwargs) -> any:
        return self.save_setting(*args, **kwargs)

    def load(self, *args, **kwargs) -> any:
        return self.load_setting(*args, **kwargs)

db = PastebinnerDB(path=DB_PATH)
