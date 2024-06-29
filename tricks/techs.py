from uuid import uuid4
import hashlib, os, pathlib, tempfile, time


APPNAME: str = __file__.split(os.sep)[-3] or "_fallback1!"
WORKDIR: str = f"{'/mnt/ramdisk' if os.path.exists('/mnt/ramdisk') else tempfile.gettempdir()}{os.sep}{APPNAME}"

def md5string(string: str = "") -> str:
    string: str = f'f12H{string or uuid4()}S4Lt'
    str_bytes: bytes = string.encode()
    return hashlib.md5(str_bytes).hexdigest()


def tmpdir(dname: str = "", hash_str: bool = True, create: bool = True, justbase: bool = False) -> str:
    if justbase:
        new_dir: str = WORKDIR
    elif dname and not hash_str:
        new_dir: str = f'{WORKDIR}{os.sep}{dname}'
    else:
        sub_dir: str = md5string(dname)
        new_dir: str = f'{WORKDIR}{os.sep}{sub_dir}'

    if create and not os.path.exists(new_dir):
        try:
            pathobj: pathlib.Path = pathlib.Path(new_dir)
            pathobj.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            sub_dir: str = "" if justbase else dname if (dname and not hash_str) else md5string(dname)
            fallback_dir: str = f'{tempfile.gettempdir()}{os.sep}{APPNAME}{os.sep}{sub_dir}'.rstrip(os.sep)
            print(f'no permission to create: {new_dir} now trying: {fallback_dir}')
            if not os.path.exists(fallback_dir):
                try:
                    pathobj: pathlib.Path = pathlib.Path(fallback_dir)
                    pathobj.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    ...
                finally:
                    if os.path.exists(fallback_dir):
                        print(f'successfully created: {fallback_dir}')
                        return fallback_dir
            return tempfile.gettempdir()
    return new_dir


def tmpfile(fname: str = "", delete: bool = False, days: int = 0, hash_str: bool = True, ext: str = "") -> str:
    tmp_dir: str = tmpdir(justbase=True)
    tmp_fname: str = fname if (fname and not hash_str) else md5string(fname)
    tmp_ext: str = f'.{ext.lstrip(".")}' if ext else ""
    tmp_fname += f'{tmp_ext if (tmp_ext and not tmp_fname.endswith(tmp_ext)) else ""}'
    tmp_path: str = f'{tmp_dir}{os.sep}{tmp_fname}'

    if (days or delete) and os.path.exists(tmp_path):
        if delete or os.path.getmtime(tmp_path) < time.time() - (86400.0 * float(days)):
            try:
                os.remove(tmp_path)
            except PermissionError:
                print(f'permission missing to remove: {tmp_path}')
    return tmp_path

