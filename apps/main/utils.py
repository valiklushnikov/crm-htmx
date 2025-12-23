import difflib

import threading
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.contrib.contenttypes.models import ContentType

def html_diff(old, new):
    old = '' if old is None else str(old)
    new = '' if new is None else str(new)
    diff = difflib.ndiff(old.splitlines(), new.splitlines())
    lines = []
    for line in diff:
        # +, -, ? prefixes - можно оформить в spans
        if line.startswith('+ '):
            lines.append(f"<div class='added'>{escape(line[2:])}</div>")
        elif line.startswith('- '):
            lines.append(f"<div class='removed'>{escape(line[2:])}</div>")
        elif line.startswith('  '):
            lines.append(f"<div>{escape(line[2:])}</div>")
    return mark_safe(''.join(lines))


_user = threading.local()

def set_change_user(user):
    _user.value = user

def get_change_user():
    return getattr(_user, "value", None)