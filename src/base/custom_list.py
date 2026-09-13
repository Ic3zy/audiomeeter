from collections import UserList


class ObservableList(UserList):

    def __init__(self, initial_data=None, on_change=None):
        super().__init__(initial_data or [])
        self._on_change = on_change

    def _notify(self, action, *args):
        if callable(self._on_change):
            self._on_change(action, self.data, *args)

    def append(self, item):
        super().append(item)
        self._notify("append", item)

    def extend(self, other):
        super().extend(other)
        self._notify("extend", other)

    def insert(self, i, item):
        super().insert(i, item)
        self._notify("insert", i, item)

    def remove(self, item):
        super().remove(item)
        self._notify("remove", item)

    def pop(self, i=-1):
        item = super().pop(i)
        self._notify("pop", i, item)
        return item

    def clear(self):
        super().clear()
        self._notify("clear")

    def sort(self, *args, **kwargs):
        super().sort(*args, **kwargs)
        self._notify("sort")

    def reverse(self):
        super().reverse()
        self._notify("reverse")

    def __setitem__(self, i, item):
        super().__setitem__(i, item)
        self._notify("setitem", i, item)

    def __delitem__(self, i):
        super().__delitem__(i)
        self._notify("delitem", i)

    def __iadd__(self, other):
        super().__iadd__(other)
        self._notify("iadd", other)
        return self
