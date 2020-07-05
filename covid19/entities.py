import attr

# Entities - Country / State / County data types

from collections import namedtuple

from . import constants

def filter_dataframe(dataframe, *misc_conditions, **equality_conditions):
    if not misc_conditions and not equality_conditions:
        return dataframe
    conditions = list(misc_conditions)
    for key, value in equality_conditions.items():
        conditions.append(getattr(dataframe, key) == value)

    joint_condition = None
    for condition in conditions:
        if joint_condition is None:
            joint_condition = condition
        else:
            joint_condition &= condition
    return dataframe[joint_condition]

# TODO: convert to using attribs instead of named_tuple subclasses
class Entity(object):
    def __str__(self):
        return ', '.join(str(x) for x in self)

    def serialize(self):
        for piece in self:
            assert constants.SEP not in piece, \
                "Name {!r} contained invalid character {}".format(piece,
                                                                  constants.SEP)
        return constants.SEP.join(str(x) for x in self)

    @classmethod
    def deserialize(cls, raw):
        return cls(*raw.split(constants.SEP))

    def dataframe_conditions(self):
        return {field: value for field, value in zip(self._fields, self)}

    def filter_dataframe(self, dataframe):
        return filter_dataframe(dataframe, **self.dataframe_conditions())


class Country(Entity, namedtuple('CountryBase', ['name'])):
    pass

class State(Entity, namedtuple('StateBase', ['name'])):
    def __new__(cls, *args, **kwargs):
        # force non-abbreviated name
        self = super().__new__(cls, *args, **kwargs)
        if self.name in constants.ABBREV_TO_STATE:
            self = State(constants.ABBREV_TO_STATE[self.name])
        return self

class County(Entity, namedtuple('CountyBase', ['name', 'state'])):
    def __new__(cls, *args, **kwargs):
        # force abbreviated state name
        self = super().__new__(cls, *args, **kwargs)
        if self.state in constants.STATE_TO_ABBREV:
            self = County(self.name, constants.STATE_TO_ABBREV[self.state])
        return self

    def dataframe_conditions(self):
        conditions = super().dataframe_conditions()
        conditions['state'] = constants.ABBREV_TO_STATE[conditions['state']]
        return conditions
