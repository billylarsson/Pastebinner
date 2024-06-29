from tricks.cutout import Cutouter
from tricks.techs  import tmpfile
import gnupg, os, subprocess
def gpg_connection() -> [object | None]:
    userhome: str = os.path.expanduser('~')
    gpgdir: str = userhome + os.sep + '.gnupg'
    kwgs: dict = dict(homedir=gpgdir)
    try:
        gpg_connection = gnupg.GPG(**kwgs)
        gpg_connection.encoding = 'utf-8'
    except:
        kwgs: dict = dict(gnupghome=gpgdir)
        try:
            gpg_connection = gnupg.GPG(**kwgs)
            gpg_connection.encoding = 'utf-8'
        except:
            return

    return gpg_connection

def get_gpg_keys() -> list:
    connection = gpg_connection()
    gpg_keys: list = connection.list_keys()
    return gpg_keys

def keyid_in_keyring(keyid: str) -> bool:
    keys: set = {x['keyid'] for x in get_gpg_keys()}
    return keyid in keys

def encrypt_any(bytes_or_string: [str | bytes], keyid: str) -> str:
    connection = gpg_connection()
    for box in get_gpg_keys():
        if keyid == box['keyid']:
            if isinstance(bytes_or_string, str):
                args: tuple = bytes_or_string, box['fingerprint'],
                kwargs: dict = dict(always_trust=True, armor=True)
                try:
                    gpg_obj = connection.encrypt(*args, **kwargs)
                    armor: str = gpg_obj.data.decode('utf-8')
                    return armor
                except:
                    ...
            else:
                # not sure why but gpg cannot encrypt bytes-object properly without using subprocess
                tmp_file_zip: str = tmpfile(ext='zip', delete=True)
                tmp_file_asc: str = tmpfile(ext='asc', delete=True)
                suborders: list = ['gpg', '-e', '-a', '-r', box['fingerprint'], '--trust-model', 'always']
                suborders += ['-o', tmp_file_asc, tmp_file_zip]
                try:
                    with open(tmp_file_zip, 'wb') as f:
                        f.write(bytes_or_string)

                    subprocess.run(suborders)
                    with open(tmp_file_asc, 'r') as f:
                        armor: str = f.read()

                    [os.remove(path) for path in {tmp_file_asc, tmp_file_zip}]
                    return armor
                except:
                    ...
    return ""

def encrypt_binary(*args, **kwargs) -> str:
    return encrypt_any(*args, **kwargs)

def encrypt_text(*args, **kwargs) -> str:
    return encrypt_any(*args, **kwargs)


def decrypt_armor(armor: str, into_string: bool = False, into_bytes: bool = False) -> [str | bytes | None]:
    parts: list = []
    connection = gpg_connection()
    begin_str: str = '-----BEGIN PGP MESSAGE-----'
    end_str: str = '-----END PGP MESSAGE-----'
    kwgs: dict = dict(first_find=begin_str, then_find=end_str)
    co: Cutouter = Cutouter(armor, **kwgs, autoplow=True)

    while bool(co):
        into_string: bool = into_string or any(isinstance(part, str) for part in parts)
        into_bytes: bool = into_bytes or any(isinstance(part, bytes) for part in parts)

        cont: str = f'{begin_str}{co.text}{end_str}'
        decryptobj = connection.decrypt(cont, always_trust=True)
        as_text: str = decryptobj.data.decode('utf-8')

        if into_bytes or (not into_string and (len(as_text) > 64 and as_text.count('�') > len(as_text) // 10)):
            as_bytes: bytes = bytes(decryptobj.data)
            parts.append(as_bytes)
        else:
            parts.append(as_text)

        co(**kwgs)


    if into_string or any(isinstance(part, str) for part in parts):
        return '\n\n'.join(parts) or ""

    elif into_bytes or any(isinstance(part, bytes) for part in parts):
        return parts[0] if parts else b''


