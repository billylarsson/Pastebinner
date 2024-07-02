from tricks.cutout   import Cutouter
from tricks.database import Pastes, db
from tricks.techs    import tmpfile
import os, time, urllib, urllib.error, urllib.parse, urllib.request

CALL_URL: dict = {
    'post': 'https://pastebin.com/api/api_post.php',
    'login': 'https://pastebin.com/api/api_login.php',
    'raw': 'https://pastebin.com/api/api_raw.php',
}
EASY_REAL: dict = {
    'key': 'api_dev_key',
    'username': 'api_user_name',
    'password': 'api_user_password',
}


def params_to_string(params: dict) -> str:
    keys: list = list(params.keys())
    save_params: dict = {k: params[k] for k in sorted(keys)}
    return str(save_params)


def params_to_path(params: dict) -> str:
    str_params: str = params_to_string(params)
    path: str = tmpfile(fname=str_params, ext='dat')
    return path


def saving_cache(params: dict, data: str) -> bool:
    if params['api_option'] in ['list', 'show_paste']:
        path: str = params_to_path(params)
        overwrite: bool = os.path.exists(path)
        with open(path, 'w') as f:
            f.write(data)

        return overwrite
    return False


def using_cache(params: dict) -> [False, str]:
    if params['api_option'] in ['list', 'show_paste']:
        path: str = params_to_path(params)
        if os.path.exists(path):
            with open(path) as f:
                cont: str = f.read()
                return cont

    return False


def load_credentials() -> bool:
    for _, var in EASY_REAL.items():
        if var not in os.environ:
            value: [str | None] = db.load_setting(var)
            if value:
                os.environ[var]: str = value
            else:
                return False

    return True

def reset_cached_user_key():
    db.save('api_user_key', None)

def get_api_user_key() -> [bytes | None]:
    if not load_credentials():
        print(f'error loading pastebin.com credentials')
        return False

    api_user_key, expire_date = db.load('api_user_key') or ("", 0.0)
    if time.time() < expire_date:
        return api_user_key

    api_url: str = CALL_URL['login']
    login_params: dict = {v: os.environ[v] for _, v in EASY_REAL.items()}
    pastebin_params = urllib.parse.urlencode(login_params).encode('utf8')

    try:
        req = urllib.request.Request(api_url, pastebin_params)
        with urllib.request.urlopen(req) as req_response:
            api_user_key: str = req_response.read()
            key_and_epoch: tuple = api_user_key, time.time() + (86400.0 * 30.0),
            db.save('api_user_key', key_and_epoch)
            return api_user_key

    except urllib.error.HTTPError as Error:
        print(f'HTTPError {Error.reason} {Error.status}')


def communicate(params: dict) -> str:
    basic_params: dict = {k: v for k, v in params.items()}
    cache: str = using_cache(basic_params)
    if cache is not False:
        return cache

    for _ in range(2):
        api_user_key: [bytes | None] = get_api_user_key()
        if not api_user_key:
            return ""

        api_url: str = CALL_URL['post']
        api_dev_key: str = os.environ[EASY_REAL['key']]
        params.update(
            dict(
                api_dev_key=api_dev_key,
                api_user_key=api_user_key,
            )
        )
        pastebin_params = urllib.parse.urlencode(params).encode('utf8')
        try:
            response = urllib.request.urlopen(api_url, pastebin_params)
            if response:
                data: str = response.read().decode('utf8')
                saving_cache(params=basic_params, data=data)
                return data

        except urllib.error.HTTPError:
            reset_cached_user_key()

    return ""


def list_pastes(limit: int = 1000):
    params: dict = dict(
        api_option='list',
        api_results_limit=limit,
    )
    path: str = params_to_path(params)
    if os.path.exists(path):
        try:
            os.remove(path)
        except PermissionError:
            ...
    return communicate(params)


def download_paste(paste_key: str):
    params: dict = dict(
        api_option='show_paste',
        api_paste_key=paste_key,
    )
    return communicate(params)

def publish_paste(title: str, text: str, priv_val: int, expire: str) -> [str | None]:
    params: dict = dict(
        api_option='paste',
        api_paste_code=text,
        api_paste_expire_date=expire,
        api_paste_name=title,
        api_paste_private=priv_val,
    )
    response: str = communicate(params)
    if response:
        return response
    return None

def delete_paste(paste_key: str) -> bool:
    params: dict = dict(
        api_option='delete',
        api_paste_key=paste_key,
    )
    response: str = communicate(params)
    return 'paste removed' in response.lower()

def update_and_save_headers():
    all_pastes: str = list_pastes(limit=1000)
    if load_credentials() is True and all_pastes == "" and get_api_user_key() is None:
        return

    pastes: list = all_pastes.split('\n</paste>')
    keys: dict = dict(
        key = str,
        date = int,
        title = str,
        size = int,
        expire_date = int,
        private = int,
        format_long = str,
        format_short = str,
        url = str,
        hits = int,
    )
    q_many, org_v = db.query_values('pastes')
    many_pastes: dict = {}

    for paste in pastes:
        values: list = [None for _ in org_v]
        values[Pastes.missing]: bool = False
        co = Cutouter(paste, autostart=False)

        for key, db_type in keys.items():
            key_ix: int = getattr(Pastes, key)
            begin: str = f'<paste_{key}>'
            end: str = f'</paste_{key}>'

            co(first_find=begin, then_find=end)
            if db_type is str:
                values[key_ix]: [str | None] = None if co.text == 'None' else (co.text or None)
            else:
                try:
                    values[key_ix]: int = int(co.text)
                except ValueError:
                    values[key_ix] = None

        if all(values[getattr(Pastes, x)] for x in ['key', 'url']):
            many_pastes[values[Pastes.key]] = values

    q: str = 'select * from pastes'
    prev: list = db.cursor.execute(q).fetchall()
    for paste in prev:
        key: str = paste[Pastes.key]

        if key not in many_pastes:
            new_paste: list = list(paste)
            new_paste[Pastes.missing]: bool = True
            many_pastes[key]: tuple = tuple(new_paste)

        elif paste[Pastes.data]:
            old_paste: list = list(many_pastes[key])
            old_paste[Pastes.data]: str = paste[Pastes.data]
            many_pastes[key]: tuple = tuple(old_paste)

    q_deltable: str = 'delete from pastes;'
    many_list: list = [v for _, v in many_pastes.items()]
    many_list.sort(key=lambda x: x[Pastes.date])

    with db.connection:
        db.cursor.execute(q_deltable)
        db.cursor.executemany(q_many, many_list)