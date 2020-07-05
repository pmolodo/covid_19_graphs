'''Abstract Interfaces for DataRetriever and associated classes'''

import attr

import abc
import datetime
import inspect
import pandas
import pathlib
import os
import typing

from . import entities

from typing import List, Optional, Tuple, Type, Union

THIS_FILE = inspect.getsourcefile(lambda: None)


EntityTypeOrInstance = Union[Type[entities.Entity], entities.Entity]

@attr.s(auto_attribs=True, frozen=True)
class EntityDataType(object):
    entity: EntityTypeOrInstance
    data_type: str


@attr.s(auto_attribs=True, frozen=True)
class DataCacheKey(object):
    entity_data_type: EntityDataType
    source_id: str

    @classmethod
    def create(cls, *input: 'DataCacheKeyTuple') -> 'DataCacheKey':
        if len(input) == 1:
            if not isinstance(input[0], DataCacheKey):
                raise ValueError(
                    '{}.create with 1 arg must be a DataCacheKey - got: {}'
                        .format(cls.__name__, input[0]))
            return input[0]
        elif len(input) == 2:
            return cls(*input)
        elif len(input) == 3:
            return cls(EntityDataType(*input[:2]), input[2])
        else:
            raise ValueError('{}.create must have 1, 2 or 3 args - got: {}'
                             .format(cls.__name__, input))

DataCacheKeyTuple = Union[Tuple[DataCacheKey],
                          Tuple[EntityDataType, str],
                          Tuple[EntityTypeOrInstance, str, str]]
DataCacheKeyLike = Union[DataCacheKey, DataCacheKeyTuple]

@attr.s(auto_attribs=True, kw_only=True)
class DataSource(object):
    id: str
    name: str
    urls: typing.Dict[str, str]


@attr.s(auto_attribs=True)
class DataRetriever(abc.ABC):
    @abc.abstractmethod
    def source(self) -> DataSource:
        raise NotImplementedError()

    @abc.abstractmethod
    def data_types(self) -> List[EntityDataType]:
        raise NotImplementedError()

    @abc.abstractmethod
    def retrieve(self) -> pandas.DataFrame:
        raise NotImplementedError()

    @abc.abstractmethod
    def retrieve(self) -> pandas.DataFrame:
        raise NotImplementedError()


UPDATE_INTERVAL = datetime.timedelta(hours=1)


@attr.s(auto_attribs=True)
class DataCacheItem(object):
    retriever: DataRetriever
    update_time: Optional[datetime.datetime] = attr.ib(default=None, init=False)
    _data: Optional[pandas.DataFrame] = attr.ib(default=None, init=False)

    def get(self) -> pandas.DataFrame:
        now = datetime.datetime.utcnow()
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

    def __getitem__(self, key: DataCacheKeyLike) -> DataCacheItem:
        if isinstance(key, tuple):
            return self._cache[DataCacheKey.create(*key)]
        return self._cache[DataCacheKey.create(key)]

    def keys(self) -> typing.Iterable[DataCacheKey]:
        return self._cache.keys()

    def values(self) -> typing.Iterable[DataCacheItem]:
        return self._cache.values()

    def add(self, retriever: DataRetriever) -> None:
        source_id = retriever.source().id
        for data_type in retriever.data_types():
            key = DataCacheKey(data_type, source_id)
            self._cache[key] = DataCacheItem(retriever)

    def get(self, *key: DataCacheKeyTuple) -> pandas.DataFrame:
        '''Convenience accessor for just the data at a given key'''
        return self[DataCacheKey.create(key)].get()


@attr.s(auto_attribs=True)
class FileCachedRetriever(DataRetriever):
    remote_retriever: DataRetriever
    filename: str

    def data_types(self) -> List[EntityDataType]:
        return self.remote_retriever.data_types()

    def source(self) -> DataSource:
        return self.remote_retriever.source()

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
