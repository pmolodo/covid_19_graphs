'''Abstract Interfaces for DataRetriever and associated classes'''

import attr

import abc
import datetime
import inspect
import pandas
import pathlib
import os
import typing

from typing import Optional


THIS_FILE = inspect.getsourcefile(lambda: None)


@attr.s(auto_attribs=True, kw_only=True)
class DataSource(object):
    name: str
    urls: typing.Dict[str, str]


@attr.s(auto_attribs=True)
class DataRetriever(abc.ABC):
    @abc.abstractmethod
    def source(self) -> DataSource:
        raise NotImplementedError()

    @abc.abstractmethod
    def data_name(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def retrieve(self) -> pandas.DataFrame:
        raise NotImplementedError()


UPDATE_INTERVAL = datetime.timedelta(minutes=1)


@attr.s(auto_attribs=True)
class DataCacheItem(object):
    retriever: DataRetriever
    update_time: Optional[datetime.datetime] = attr.ib(default=None, init=False)
    _data: Optional[pandas.DataFrame] = attr.ib(default=None, init=False)

    def get(self) -> pandas.DataFrame:
        now = datetime.datetime.now()
        if self._data is None or (now - self.update_time) > UPDATE_INTERVAL:
            self._data = self.retriever.retrieve()
            self.update_time = now
        return self._data

    def max_date(self) -> Optional[pandas._libs.tslibs.timestamps.Timestamp]:
        '''Convenience method for querying the maximum date in the data'''
        data = self.get()
        if 'date' in data.columns:
            return data.date.max()
        return None


@attr.s(auto_attribs=True)
class DataCache(object):
    _cache: typing.Dict[str, DataCacheItem] = \
        attr.ib(init=False, default=attr.Factory(dict))

    def __getitem__(self, key: str) -> DataCacheItem:
        return self._cache[key]

    def values(self) -> typing.Iterable[DataCacheItem]:
        return self._cache.values()

    def add(self, key: str, retriever: DataRetriever) -> None:
        self._cache[key] = DataCacheItem(retriever)

    def get(self, key: str) -> pandas.DataFrame:
        '''Convenience accessor for just the data at a given key'''
        return self[key].get()


@attr.s(auto_attribs=True)
class FileCachedRetriever(DataRetriever):
    remote_retriever: DataRetriever
    filename: str

    def source(self) -> DataSource:
        return self.remote_retriever.source()

    def data_name(self) -> str:
        return self.remote_retriever.data_name()

    def local_path(self) -> pathlib.Path:
        # if we've imported as a module, use the path of this module
        if THIS_FILE and os.path.isfile(THIS_FILE):
            return pathlib.Path(THIS_FILE).parent.parent / self.filename
        # otherwise, assume that cwd is the repo root!
        return pathlib.Path('.') / self.filename

    def retrieve(self) -> pandas.DataFrame:
        local_path = self.local_path()
        if local_path.is_file():
            return pandas.read_csv(str(local_path))

        # use the remote retriever, save out to local_path
        data = self.remote_retriever.retrieve()
        compression_opts = {
            'method': 'zip',
            'archive_name': local_path.with_suffix('.csv').name,
        }
        data.to_csv(str(local_path), index=False, compression=compression_opts)
        return data
