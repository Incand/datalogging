from typing import Dict, Tuple, Any, Iterable, Union


def _split_vpath(vpath: str) -> Tuple[str, str]:
    """splits a virtual path so that there are always exactly two elements in the result.

    >>> _split_vpath('foo')
    ('foo', '')

    >>> _split_vpath('foo/bar/baz')
    ('foo', 'bar/baz')
    """
    paths = vpath.split('/', 1)
    return tuple(paths) if len(paths) == 2 else (paths[0], '')


def _rsplit_vpath(vpath: str) -> Tuple[str, str]:
    """rsplits a virtual path so that there are always exactly two elements in the result.

    >>> _rsplit_vpath('foo')
    ('', 'foo')

    >>> _rsplit_vpath('foo/bar/baz')
    ('foo/bar', 'baz')
    """
    paths = vpath.rsplit('/', 1)
    return tuple(paths) if len(paths) == 2 else ('', paths[0])


class LogNode:
    def __init__(self, data: Dict[str, list] = None, children: Dict[str, 'LogNode'] = None):
        self.data = data or {}
        self.children = children or {}

    def clear(self):
        for child in self.children.values():
            child.clear()
        self.data = {}

    def parse(self):
        result = dict(self.data)
        for key, child in self.children.items():
            parsed = child.parse()
            if parsed:
                result[key] = parsed
        return result


class Logger:
    """in-memory logger for diverse data.

    Can be considered as a directory containing files (data) and sub-directories (child logger).
    A virtual path is needed for most methods, which denotes where to look for data and child loggers.
    """
    def __init__(self, root: LogNode = None):
        self._root = root or LogNode()

    def __contains__(self, vpath: str) -> bool:
        if vpath == '':
            return True
        current_node = self._root
        *dir_keys, last_key = vpath.split('/')
        for key in dir_keys:
            current_children = current_node.children
            if key not in current_children:
                return False
            current_node = current_children[key]
        return last_key in current_node.children or last_key in current_node.data

    def _traverse(self, vpath: str, create: bool = False) -> LogNode:
        """Get the node after traversing the tree via the given path.

        Creates new nodes on the go if create is set to True, else raises a KeyError.
        """
        if vpath == '':
            return self._root
        if not create and vpath not in self:
            raise KeyError(f'vpath {vpath} does not exist.')
        current_node = self._root
        for key in vpath.split('/'):
            current_node = current_node.children.setdefault(key, LogNode())
        return current_node

    def _do_data_op(self, vpath, op, create: bool = False, *args, **kwargs):
        dir_path, data_key = _rsplit_vpath(vpath)
        node_data = self._traverse(dir_path, create).data
        lst = node_data.setdefault(data_key, []) if create else node_data[data_key]
        return op(lst, *args, **kwargs)

    def make_child(self, vpath: str) -> 'Logger':
        """Get a logger at the given vpath, relativ so the logger the mathod was called from.

        Data in the sublogger will also be visible in the parent but not vice-versa (expect when created at the correct
        vpath).
        """
        return self.__class__(self._traverse(vpath, create=True))

    def __getitem__(self, vpath: str) -> list:
        """Return a reference to the data at vpath."""
        return self._do_data_op(vpath, lambda lst: lst)

    def get(self, vpath: str, default=None) -> list:
        """Return a reference to the data at vpath if it exists, else return the provided default."""
        if vpath in self:
            node_or_list = self[vpath]
            if isinstance(node_or_list, list):
                return node_or_list
        return default

    def _log_vpaths_vals(self, vpath_vals_dict: Dict[str, Any]):
        for vpath, val in vpath_vals_dict.items():
            self._do_data_op(vpath, list.extend if isinstance(val, Iterable) else list.append, True, val)

    def log(self, *args):
        """Logs data in-memory to a list container, associated with a unix-path-like key.

        Args:
            **either**
            vpath (str): Virtual path
            value (Any): Value to store
            **or**
            vpath_value_map (Dict[str, Any]): Mapping of vpaths and values to store

        Raises:
            TypeError -- Wrong number of arguments.
        """
        len_ = len(args)
        if 1 <= len_ <= 2:
            self._log_vpaths_vals(args[0] if len_ == 1 else {args[0]: args[1]})
        else:
            raise TypeError("Method has to be called with either one or two arguments.")

    def clear(self):
        """Clears all data in this repository"""
        self._root.clear()

    def as_dict(self):
        """Parses the underlying tree-structure of data into nested dictionaries."""
        return self._root.parse()
