# -*- coding: utf-8 -*-

import importlib
import os
import re
import vim

current_completer = None


def _find(file):
    cwd = os.getcwd()
    while True:
        path = os.path.join(cwd, file)
        if os.path.exists(path):
            return path
        if os.path.dirname(cwd) == cwd:
            break
        cwd = os.path.split(cwd)[0]


def _read_args(path):
    try:
        with open(path) as f:
            return [l.strip() for l in f.readlines()]
    except Exception:
        return []


class Meta(type):
    def __init__(cls, name, bases, attrs):
        if name not in ('Completor', 'Base'):
            Completor._registry[cls.filetype] = cls()

        return super(Meta, cls).__init__(name, bases, attrs)

Base = Meta('Base', (object,), {})


class Unusable(object):
    def __get__(self, inst, owner):
        raise RuntimeError('unusable')


class Completor(Base):
    _registry = {}
    _commons = None

    filetype = Unusable()
    name = Unusable()

    common = False
    daemon = False
    sync = False
    trigger = None

    _type_map = {
        'c': 'cpp'
    }

    _arg_cache = {}

    def __init__(self):
        self.input_data = ''

    def commons(cls):
        if cls._commons is None:
            cls._commons = tuple(c for c in cls._registry.values()
                                 if c.common)
        return cls._commons

    @property
    def current_directory(self):
        return vim.eval('expand("%:p:h")')

    @property
    def tempname(self):
        return vim.eval('completor#utils#tempname()')

    @property
    def filename(self):
        return vim.current.buffer.name

    @property
    def cursor(self):
        return vim.current.window.cursor

    # use cached property
    @property
    def filetype_map(self):
        m = vim.eval('get(g:, "completor_filetype_map", {})')
        self._type_map.update(m)
        return self._type_map

    def get_binary(self, key):
        return vim.eval('get(g:, "{}", "")'.format(key))

    def match(self, input_data):
        if self.trigger is None:
            return True
        if isinstance(self.trigger, str):
            self.trigger = re.compile(self.trigger, re.X)

        return bool(self.trigger.search(input_data))

    def format_cmd(self):
        return ''

    def parse_config(self, file):
        key = "{}-{}-{}".format(self.filetype, self.name, file)
        if key not in self._arg_cache:
            path = _find(file)
            self._arg_cache[key] = [] if path is None else _read_args(path)
        return self._arg_cache[key]

_completor = Completor()


def _load(ft, input_data):
    commons = _completor.commons()
    for c in commons:
        if c.match(input_data):
            return c

    if not ft:
        return None

    ft = _completor.filetype_map.get(ft, ft)

    if ft not in _completor._registry:
        try:
            importlib.import_module("completers.{}".format(ft))
        except ImportError:
            return None
    return _completor._registry.get(ft)


def load_completer(ft, input_data):
    c = _load(ft, input_data)
    if c is None or not (c.common or c.match(input_data)):
        c = _completor._registry['buffer']
    c.input_data = input_data
    return c