# -*- coding: utf-8 -*-

import vim
try:
    from pipes import quote
except ImportError:
    from shlex import quote

from completor import Completor, get_encoding
from completor.compat import to_bytes

import platform
import os

ACTION_MAP = {
    b'complete': 'complete',
    b'definition': 'find-definition'
}


class Racer(Completor):
    filetype = 'rust'
    trigger = r'(?:\w{2,}\w*|\.\w*|::\w*)$'

    def format_cmd(self):
        binary = self.get_option('racer_binary') or 'racer'
        return [binary, 'daemon']

    def get_cmd_info(self, action):
        binary = self.get_option('racer_binary') or 'racer'
        return vim.Dictionary(
            cmd=[binary, 'daemon'],
            is_daemon=True,
            ftype=self.filetype,
            is_sync=False
        )

    def prepare_request(self, action):
        line, col = self.cursor
        is_cygwin = platform.system().find("CYGWIN") != -1
        cmd = 'cygpath -a -w {}'.format(self.filename)
        cyg_filename = os.popen(cmd).read().strip().replace('\\', '\\\\')
        cmd = 'cygpath -a -w {}'.format(self.tempname)
        cyg_tempname = os.popen(cmd).read().strip().replace('\\', '\\\\')
        filename = cyg_filename if is_cygwin else quote(self.filename)
        tempname = cyg_tempname if is_cygwin else quote(self.tempname)
        return ' '.join([ACTION_MAP[action], str(line), str(col),filename, tempname])

    def is_message_end(self, msg):
        return msg == b'END'

    def on_definition(self, items):
        ret = []
        for item in items:
            if not item.startswith(b'MATCH'):
                continue
            parts = item.split(b',')
            if len(parts) < 4:
                continue
            ret.append({'filename': parts[3], 'lnum': int(parts[1]),
                        'col': int(parts[2]) + 1, 'text': parts[0]})
        return ret

    # items: list of bytes
    def on_complete(self, items):
        if self.is_comment_or_string() or '///' in self.input_data:
            return []

        input_data = to_bytes(self.input_data, get_encoding())

        completions = []
        for item in items:
            if not item.startswith(b'MATCH'):
                continue

            parts = item.split(b',')
            if len(parts) < 6:
                continue

            name = parts[0][6:]
            kind = parts[4].lower()
            spec = b'mod' if kind == b'module' else b', '.join(parts[5:])
            if spec.startswith(b'pub '):
                spec = spec[4:]

            if spec.startswith(input_data):
                continue

            completions.append({
                'word': name,
                'menu': spec,
                'dup': 0
            })
        return completions
