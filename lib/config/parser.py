import collections
import itertools
from pathlib import Path
import yaml


class IncludeLoader(yaml.SafeLoader):
    """ Loader that allows `!include` constructor. Include a yaml file under the given
        key. Wildcards in the filename are allowed but the behavior is undefined in case
        of recusive includes or in case of heterogeneous files.

        WARNING: When loading a collection of mappings thanks to a wildcard, if two of more
        mappings share the same key the behavior for this key is undefined.
    """

    def __init__(self, stream):
        super().__init__(stream)
        self.add_constructor("!include", type(self).include)
        try:
            self.cwd = Path(stream.name).parent
        except AttributeError:
            self.cwd = Path.cwd()

    def include(self, node):
        pattern = self.construct_scalar(node)
        if pattern.startswith("/"):
            wd = Path("/")
            pattern = Path(pattern).relative_to(wd).as_posix()
            files = wd.glob(pattern)
        else:
            files = self.cwd.glob(pattern)
        return IncludeLoader.merge(IncludeLoader._load_paths(files))

    @staticmethod
    def _load_paths(paths):
        """ Load several yaml files from an iterable of paths

        :param paths: an iterable of paths
        :returns: a generator of loaded yaml

        """
        for p in paths:
            with open(p, "rb") as fd:
                yield yaml.load(fd, Loader=IncludeLoader)

    @staticmethod
    def merge(iterable):
        """ Merge elements of an iterable of Mappings or Sequences into either a Mapping
            or a Sequence. UB if iterable is heterogeneous.

        :param iterable: iterable of Mapping or Sequence
        :returns: A Mapping containing all Mappings or a Sequence containing all
            Sequences

        """
        try:
            it = iter(iterable)
            first = next(it)
        except StopIteration:
            return []

        if isinstance(first, collections.abc.Mapping):
            mapping = collections.ChainMap(first, *it)
            mapping.maps.reverse()
            return mapping
        else:
            return itertools.chain.from_iterable(itertools.chain(iter((first,)), it))
