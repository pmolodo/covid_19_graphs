# coding: utf-8

# helpful links:
# - https://towardsdatascience.com/data-visualization-with-bokeh-in-python-part-ii-interactions-a4cf994e2512
# - https://realpython.com/lessons/using-groupfilter-and-cdsview/

from . import datamod

import abc
import enum
import inspect
import re
import urllib

import bokeh.application.handlers
import bokeh.layouts as lyt
import bokeh.models as mdl
import bokeh.plotting

from collections import namedtuple

from .constants import KELLY_COLORS
from .entities import Country, County, Entity, State
from .retrievers import DataCacheKey, EntityDataType


################################################################################
# Utilities

MOBILE_REG_B = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
MOBILE_REG_V = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

def is_mobile_agent(user_agent):
    if not user_agent:
        return False
    if MOBILE_REG_B.search(user_agent):
        return True
    return bool(MOBILE_REG_V.search(user_agent[0:4]))

################################################################################

DEFAULT_INITIAL_ENTITIES = [
    Country('Italy'),
    State('California'),
    State('New York'),
    County('Los Angeles', 'CA'),
    County('New York City', 'NY'),
]


################################################################################
# Bokeh application logic

class QuerySerializeable(abc.ABC):
    '''Mixin class that defines how to serialize to and from a query string'''

    @classmethod
    @abc.abstractmethod
    def valid_query_keys(cls):
        '''Return a set of all allowable keys that may be in to_query_dict
        '''
        raise NotImplementedError()

    def to_query_dict(self):
        '''Returns a dict that may be passed to urllib.parse.urlencode

        ...with doseq=True
        '''
        query_dict = self._to_query_dict()
        assert not (set(query_dict) - self.valid_query_keys())
        return query_dict

    @abc.abstractmethod
    def _to_query_dict(self):
        '''Overriddeable implementation for to_query_dict'''
        raise NotImplementedError()

    @classmethod
    def from_query(cls, query_dict):
        '''Given a dict that was parsed from a query string, return an instance
        of this class.
        '''
        assert not (set(query_dict) - cls.valid_query_keys())
        return cls._from_query(query_dict)

    @classmethod
    @abc.abstractmethod
    def _from_query(cls, query_dict):
        '''Overriddeable implementation for from_query'''
        raise NotImplementedError()

# For option enums, the name will be what is saved in queries, the value is
# what will be displayed in UIs

@enum.unique
class YAxisStat(enum.Enum):
    deaths = 'deaths'
    cases = 'cases'
    hospitalizations = 'hospitalizations'

@enum.unique
class YAxisScaling(enum.Enum):
    log = 'logarithmic'
    linear = 'linear'

@enum.unique
class DailyCumulativeCurrent(enum.Enum):
    daily = 'daily increase'
    cumulative = 'cumulative'
    current = 'current'

@enum.unique
class PopulationAdjustment(enum.Enum):
    raw = 'raw'
    per_million = 'per million'

Option = namedtuple('Option', ['name', 'default', 'type'])

class Options(QuerySerializeable):
    OPTIONS_LIST = [
        Option('ystat', YAxisStat.deaths, YAxisStat),
        Option('yscale', YAxisScaling.log, YAxisScaling),
        Option('population_adjustment', PopulationAdjustment.per_million,
               PopulationAdjustment),
        Option('daily', DailyCumulativeCurrent.cumulative,
               DailyCumulativeCurrent),
        Option('daily_average_size', 7, int)
    ]

    OPTIONS = {x.name: x for x in OPTIONS_LIST}

    # check for duplicate names
    assert len(OPTIONS) == len(OPTIONS_LIST)

    @classmethod
    def valid_query_keys(cls):
        return set(cls.OPTIONS)

    def _to_query_dict(self):
        as_dict = {}
        for name, val in self._values.items():
            option = self.OPTIONS[name]
            if val != option.default:
                # devise alternative if if-branching gets unwieldy

                # because it's more compact, convert bools to 0/1
                if option.type is bool:
                    val = int(val)
                elif issubclass(option.type, enum.Enum):
                    val = val.name
                as_dict[name] = val
        return as_dict

    @classmethod
    def _from_query(cls, query_dict):
        import numbers

        initial_vals = {}
        for key, val in query_dict.items():
            option = cls.OPTIONS[key]
            # devise alternative if if-branching gets unwieldy
            if option.type is bool:
                # all things we get from the parsed query are lists
                assert len(val) == 1
                val = bool(int(val[0]))
            elif issubclass(option.type, enum.Enum):
                assert len(val) == 1
                val = getattr(option.type, val[0])
            elif issubclass(option.type, numbers.Real):
                assert len(val) == 1
                val = option.type(val[0])
            initial_vals[key] = val
        return cls(initial_vals)

    def __init__(self, initial_vals=None):
        self._values = {name: opt.default for name, opt in self.OPTIONS.items()}
        if initial_vals:
            for key, val in initial_vals.items():
                assert key in self.OPTIONS
                self._values[key] = val

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        assert key in self.OPTIONS
        self._values[key] = value


class DisplayEntities(QuerySerializeable):
    def __init__(self, countries=(), states=(), counties=(), visible=None,
                 hidden=None):
        self._countries = set(countries)
        self._states = set(states)
        self._counties = set(counties)
        self._visible = set()
        self._callbacks = {}
        self._invalidate()

        if visible is not None:
            if hidden is not None:
                raise ValueError("may only specify one of visible or hidden")
            self.set_all_visible(visible)
        elif hidden is not None:
            self.set_all_hidden(hidden)
        else:
            self.set_all_visible(self)

    def __iter__(self):
        return iter(self.ordered())

    def __len__(self):
        return len(self._countries) + len(self._states) + len(self._counties)

    def __getitem__(self, i):
        return self.ordered()[i]

    def __contains__(self, item):
        if isinstance(item, Country):
            return item in self._countries
        elif isinstance(item, State):
            return item in self._states
        elif isinstance(item, County):
            return item in self._counties
        return False

    def _invalidate(self):
        self._ordered = None
        self._indices = None
        self._visible_ordered = None

    def ordered(self):
        if self._ordered is None:
            self._ordered = sorted(self._countries) + sorted(self._states) \
                            + sorted(self._counties)
        return self._ordered

    def indices(self):
        if self._indices is None:
            self._indices = {
                entity: i for i, entity in enumerate(self.ordered())
            }
        return self._indices

    def index(self, entity):
        return self.indices()[entity]

    def add(self, entity):
        if isinstance(entity, Country):
            self._countries.add(entity)
        elif isinstance(entity, State):
            self._states.add(entity)
        elif isinstance(entity, County):
            self._counties.add(entity)
        else:
            raise TypeError("must be a Country, State, or County - got: {!r}"
                            .format(entity))
        self.set_visibility(entity, True)
        self._invalidate()

    def remove(self, entity):
        if isinstance(entity, Country):
            self._countries.remove(entity)
        elif isinstance(entity, State):
            self._states.remove(entity)
        elif isinstance(entity, County):
            self._counties.remove(entity)
        else:
            raise TypeError("must be a Country, State, or County - got: {!r}"
                            .format(entity))
        self.set_visibility(entity, False)
        self._invalidate()

    def set_visibility(self, entity, is_visible):
        if is_visible:
            self._visible.add(entity)
        else:
            self._visible.discard(entity)
        self._visible_ordered = None

    def set_all_visible(self, visible):
        if all(isinstance(x, int) for x in visible):
            ordered = self.ordered()
            visible = [ordered[i] for i in visible]
        elif not all(isinstance(x, Entity) for x in visible):
            raise ValueError('all inputs must be either Entity objects or '
                             'integer indices')
        self._visible.update(visible)
        self._visible_ordered = None

    def set_all_hidden(self, hidden):
        if all(isinstance(x, int) for x in hidden):
            ordered = self.ordered()
            hidden = [ordered[i] for i in hidden]
        elif not all(isinstance(x, Entity) for x in hidden):
            raise ValueError('all inputs must be either Entity objects or '
                             'integer indices')
        self._visible.clear()
        self._visible.update(set(self) - set(hidden))
        self._visible_ordered = None

    def is_visible(self, entity):
        return entity in self._visible

    def visible(self):
        return set(self._visible)

    def visible_ordered(self):
        if self._visible_ordered is None:
            self._visible_ordered = [x for x in self.ordered()
                                     if x in self._visible]
        return self._visible_ordered

    @classmethod
    def valid_query_keys(cls):
        return {'countries', 'states', 'counties', 'hidden'}

    def _to_query_dict(self):
        # when serializing, we output invisible, instead of visible, since we
        # assume that will be smaller
        result = {}
        if self._countries:
            result['countries'] = sorted(x.serialize() for x in self._countries)
        if self._states:
            result['states'] = sorted(x.serialize() for x in self._states)
        if self._counties:
            result['counties'] = sorted(x.serialize() for x in self._counties)
        hidden = [x for x in self if x not in self._visible]
        if hidden:
            # ordering is well defined, so can use indices, which avoids needing
            # to specify the type (Country/State/County) of each entry in
            # hidden, and is also more compact
            result['hidden'] = [self.index(x) for x in hidden]
        return result

    @classmethod
    def _from_query(cls, raw):
        countries = [Country.deserialize(x) for x in raw.get('countries', [])]
        states = [State.deserialize(x) for x in raw.get('states', [])]
        counties = [County.deserialize(x) for x in raw.get('counties', [])]
        hidden = raw.get('hidden')
        if hidden:
            # we need to convert hidden indices, from str to int
            hidden = [int(x) for x in hidden]
        return cls(countries=countries, states=states, counties=counties,
                   hidden=hidden)


class Model(object):
    '''Only holds data
    Can be queried or altered, but has no knowledge of any other entities, or
    logic for handling callbacks / notifications'''

    def __init__(self):
        self.entities = DisplayEntities()
        self.options = Options()
        self.data_items = {}
        self.set_data()

    def set_data(self):
        all_keys = datamod.data_cache.keys()
        self.data_items.clear()
        for entity in (Country, State, County):
            # TODO: make data_cache use hierarchical keying
            stat = self.options['ystat'].name
            desired_datatype = EntityDataType(entity, stat)
            valid_keys = []
            for key in all_keys:
                if key.entity_data_type == desired_datatype:
                    valid_keys.append(key)

            if not valid_keys:
                continue
            elif len(valid_keys) == 1:
                key = valid_keys[0]
            else:
                # right now, hard-code state data to covid_tracking
                assert entity == State
                key = [x for x in valid_keys
                       if x.source_id == 'covid_tracking'][0]
            self.data_items[entity] = datamod.data_cache[key]

    def last_update_time(self):
        return max(item.update_time for item in self.data_items.values())

    @staticmethod
    def deaths_per_mill_greater_1(data):
        return data.deaths / (data.population / 1e6) >= 1.0

    def graphable_entities(self, entity_type, **conditions):
        from .entities import filter_dataframe
        if entity_type not in self.data_items:
            return []
        dataframe = self.data_items[entity_type].get()
        dataframe = filter_dataframe(
            dataframe, self.deaths_per_mill_greater_1(dataframe), **conditions)
        return sorted(dataframe.name.unique())

    def make_dataset(self):
        to_graph = []
        pop_adj = self.options['population_adjustment']

        def get_data_since(data, condition_func):
            condition = condition_func(data)
            since_data = data[condition].reset_index(drop=True)
            day0 = since_data.date.min()
            since_data['days'] = (since_data.date - day0).apply(lambda x: x.days)
            return since_data

        for entity in self.entities.visible_ordered():
            try:
                data = self.data_items[type(entity)].get()
            except KeyError:
                continue
            data = entity.filter_dataframe(data)
            data = get_data_since(data, self.deaths_per_mill_greater_1)

            assert len(data) > 0, f"no {entity.__class__.__name__} data for {entity}"
            stat_name = self.options['ystat'].name
            if self.options['daily'] == DailyCumulativeCurrent.current:
                stat_name += ':current'
            if stat_name not in data.columns:
                continue
            data = data[data[stat_name].notna()]
            if data.empty:
                continue
            data = data.reset_index(drop=True)
            y_data = data[stat_name]
            if self.options['daily'] == DailyCumulativeCurrent.daily:
                y_data = y_data.diff()
                # The very first entry will be NaN, set to 0 instead
                y_data[0] = 0
                average_size = self.options['daily_average_size']
                if average_size > 1:
                    y_data = y_data.rolling(
                        window=average_size, min_periods=1).mean()

            if pop_adj == PopulationAdjustment.per_million:
                # for some reason, using /= here causes a different result
                y_data = y_data / (data.population / 1e6)
            elif pop_adj != PopulationAdjustment.raw:
                raise ValueError(pop_adj)
            data['y'] = y_data

            to_graph.append((entity, data))
        return to_graph

    def serializeable_members(self):
        def is_serializeable(x):
            return isinstance(x, QuerySerializeable)
        return dict(inspect.getmembers(self, is_serializeable))

    def to_query_str(self):
        as_dict = {}

        all_possible_keys = set()
        for serializeable in self.serializeable_members().values():
            # ensure there's no key overlap between things we're serializing
            new_keys = serializeable.valid_query_keys()
            num_old_keys = len(all_possible_keys)
            all_possible_keys.update(new_keys)
            assert num_old_keys + len(new_keys) == len(all_possible_keys)

            as_dict.update(serializeable.to_query_dict())

        return urllib.parse.urlencode(as_dict, doseq=True)

    def set_from_query_dict(self, parsed_query):
        # unlike urllib.parse.urlencode, whatever bokeh uses to get
        # it's args back doesn't handle str (unicode), and leaves things as
        # bytes... so first, need to convert everything to str
        parsed_query = {key: [x.decode('utf-8') for x in val]
                        for key, val in parsed_query.items()}

        for name, serializeable in self.serializeable_members().items():
            these_items = {}
            for key in serializeable.valid_query_keys():
                if key in parsed_query:
                    these_items[key] = parsed_query.pop(key)
                    print(these_items[key])
            print(name, these_items)
            setattr(self, name, serializeable.from_query(these_items))

        if parsed_query:
            # make this more obvious to user?
            bad_keys = ', '.join(sorted(parsed_query))
            print("WARNING: unrecognized query keys: {}".format(bad_keys))


class View(object):
    '''Contains the bokeh UI items, and is responsible for altering them

    May interact with model is a read-only manner'''

    UPDATE_FETCHING = 'Updated: Fetching'

    def __init__(self, doc, model):
        self.model = model
        self.doc = doc
        self.controller = None
        self._last_data = None

    # utility methods

    def color(self, entity):
        i = self.model.entities.index(entity)
        return KELLY_COLORS[i % len(KELLY_COLORS)]

    def set_controller(self, controller):
        self.controller = controller

    # build

    def build(self):
        '''constructs the main layout'''
        self.doc.title = "Covid-19 Graphs"

        self.entities_layout = lyt.column([], width_policy="max")
        self.build_entity_ui_rows(self.entities_layout)
        self.add_entity_layout = self.build_add_entity_layout()
        self.options_layout = self.build_options_layout()
        self.sources_layout = self.build_sources_layout()

        # Make tabs
        self.view_tab = mdl.Panel(child=self.entities_layout,
                                  title='View/Remove')
        self.add_tab = mdl.Panel(child=self.add_entity_layout, title='Add')
        self.options_tab = mdl.Panel(child=self.options_layout, title='Options')
        self.sources_tab = mdl.Panel(child=self.sources_layout, title='Info')
        self.tabs = mdl.Tabs(tabs=[self.view_tab,
                                   self.add_tab,
                                   self.options_tab,
                                   self.sources_tab])
        for tab in self.tabs.tabs:
            tab.child.width_policy = 'min'
        self.tabs.width_policy = 'min'

        # Create a row layout for tabs + plot

        # actual plot will be replace by make_plot when we have data, and
        # are ready to draw
        self.plot = bokeh.plotting.figure(title="Dummy placeholder plot")
        self.updated = mdl.Title(text=self.UPDATE_FETCHING, align="right",
                                 text_font_size="8pt", text_font_style="normal")
        self.plot.add_layout(self.updated, "below")

        self.controls_plot = mdl.Row(self.tabs, self.plot)
        self.controls_plot.sizing_mode = "stretch_both"

        self.save_button = self.build_save_button()
        self.main_layout = mdl.Column(self.controls_plot, self.save_button,
                                      sizing_mode='stretch_both')
        self.doc.add_root(self.main_layout)

        self.add_updated_local_time_callback()

    def add_updated_local_time_callback(self):
        """Add callbacks to display the last-updated time in the browser-local
        timezone.
        """
        # Unfortunately, getting the timezone to show in the users's local time
        # (instead of the server timezone) was tricky - the only thing that
        # "knows" the local time is the browser, which means the updated time
        # display string has to be updated via a javascript-callback;
        # unfortunately, getting a javascript callback to fire just once, when
        # the whole graph is first built (and not when, say, the user clicks a
        # button) proved problematic - the only way I found was to make use
        # of a periodic_callback, which modified a value that a javascript
        # on change callback was watching.

        # Thanks to _jm and Bryan for their responses on this thread:
        #    https://discourse.bokeh.org/t/how-to-display-last-updated-information-in-local-time/5870

        update_time_cds = mdl.ColumnDataSource(
            data={'t': [self.model.last_update_time()]})

        update_text_cb = mdl.CustomJS(args=dict(source=update_time_cds),
                                      code="""
            var localUpdateTime = new Date(source.data['t'][0])
            cb_obj.text = "Updated: " + localUpdateTime.toString();
        """)
        self.updated.js_on_change('text', update_text_cb)

        periods_holder = [0]
        def modify_updated_time_placeholder(*args, **kwargs):
            if not self.updated.text.startswith(self.UPDATE_FETCHING):
                # print("periodic_callback removed...")
                self.doc.remove_periodic_callback(periodic_callback)
                return

            # Just cycle between values with 1 to 3 trailing "." - this just
            # makes sure that the value is always changed, so that as soon
            # as javascript is "available", the javascript "on change" callback
            # will fire.
            num_periods = periods_holder[0]
            # print("periodic_callback fired! {} - {} - {}"
            #       .format(num_periods, args, kwargs))
            periods_holder[0] = num_periods + 1
            ellipsis = '.' * (num_periods % 3 + 1)
            self.updated.text = self.UPDATE_FETCHING + ellipsis

        periodic_callback = self.doc.add_periodic_callback(
            modify_updated_time_placeholder, 1000)

    def build_save_button(self):
        save_button = mdl.Button(label='Save/Share', button_type="success")

        # want to have a click call python code (to calculate the url), and
        # then javascript (to do the dialog)
        # only way to do this that I found was to chain callbacks, as shown here
        # (thanks ChesuCR):
        #   https://stackoverflow.com/a/49095082/920545

        # We trigger the JS callback on a change to "tags" since that shouldn't
        # affect anything else
        js_code = r"""
            prompt("Copy the following url to save this graph:", url);
        """
        js_callback = mdl.CustomJS(code=js_code)
        save_button.js_on_change("tags", js_callback)

        def on_click():
            querystr = self.model.to_query_str()
            # TODO: don't hardcode directory portion
            host = self.doc.session_context.request.headers['Host']
            url = f'http://{host}/covid19?{querystr}'

            # we could change js_callback.code, but easier to change args
            js_callback.args = {'url': url}

            # now trigger the javascript, by changing tags
            tags = save_button.tags
            SENTINEL = 'click_toggle'
            if SENTINEL in tags:
                tags.remove(SENTINEL)
            else:
                tags.append(SENTINEL)
            # this should trigger the javascript
            save_button.tags = tags

        save_button.on_click(on_click)

        return save_button

    def build_entity_ui_row(self, entity):
        is_visible = self.model.entities.is_visible(entity)
        if is_visible:
            active = [0]
        else:
            active = []
        vis_check = mdl.CheckboxGroup(labels=[str(entity)], active=active,
                                      width_policy="min")

        def update_visible(attr, old_visible_indices, visible_indices):
            del old_visible_indices
            assert visible_indices == [] or visible_indices == [0]
            self.controller.update_visible(entity, bool(visible_indices),
                                           update_view=False)

        vis_check.on_change('active', update_visible)

        spacer = mdl.Spacer(sizing_mode="stretch_width")
        delete_button = mdl.Button(label="X", button_type="danger",
                                   max_height=25, width_policy="min",
                                   height_policy="min")

        def remove_entity():
            self.controller.remove_entity(entity)

        delete_button.on_click(remove_entity)

        return lyt.row(vis_check, spacer, delete_button)

    def build_entity_ui_rows(self, entity_layout):
        entity_layout.children = [self.build_entity_ui_row(e)
                                  for e in self.model.entities]

    def build_add_entity_layout(self):
        # Country
        all_countries = self.model.graphable_entities(Country)
        self.pick_country_dropdown = mdl.Select(
            title="Country:", value="Spain", options=all_countries)
        self.add_country_button = mdl.Button(label="Add Country")

        def click_add_country():
            self.controller.add_entity(
                Country(self.pick_country_dropdown.value))

        self.add_country_button.on_click(click_add_country)

        # State
        all_states = self.model.graphable_entities(State)
        self.pick_state_dropdown = mdl.Select(
            title="US State:", value="California", options=all_states)
        self.add_state_button = mdl.Button(label="Add State")

        def click_add_state():
            self.controller.add_entity(
                State(self.pick_state_dropdown.value))

        self.add_state_button.on_click(click_add_state)

        # County

        self.pick_county_dropdown = mdl.Select(title="US County:")
        self.add_county_button = mdl.Button(label="Add County")

        def click_add_county():
            self.controller.add_entity(
                County(self.pick_county_dropdown.value,
                       self.pick_state_dropdown.value))

        self.add_county_button.on_click(click_add_county)

        # update county values when state changes

        # Note that this callback is down here, because it does not involve
        # changing any data external to the View
        def pick_state_changed(attr, old_state, new_state):
            assert attr == 'value'
            del old_state
            all_counties = self.model.graphable_entities(
                County, state=self.pick_state_dropdown.value)
            self.pick_county_dropdown.options = all_counties
            if all_counties:
                self.pick_county_dropdown.value = all_counties[0]

        self.pick_state_dropdown.on_change('value', pick_state_changed)

        # setup initial counties list
        pick_state_changed('value', None, self.pick_state_dropdown.value)

        # Misc extra display elements
        note1 = mdl.Paragraph(text="Note: graphable entities are filtered to"
                                   " only those that meet the minimum criteria")

        spacer = mdl.Spacer(height=10)

        return lyt.column(
            self.pick_country_dropdown,
            self.add_country_button,
            spacer,
            self.pick_state_dropdown,
            self.add_state_button,
            spacer,
            self.pick_county_dropdown,
            self.add_county_button,
            spacer,
            note1,
        )

    def build_options_layout(self):
        self.option_uis = {}
        self._build_enumerated_option('ystat', "Statistic to graph:")
        ystat_select_ui = self.option_uis['ystat']
        ystat_select_ui.on_change('value',
                                  lambda attr, old, new: self.model.set_data())
        self._build_enumerated_option('yscale', "Graph scaling:")
        self._build_enumerated_option('population_adjustment',
                                      "Popluation Adjustment:")
        self._build_enumerated_option('daily', "Daily/Cumulative:")
        self._build_int_option('daily_average_size',
                               "Averge daily value over past X days:")
        return lyt.column(list(self.option_uis.values()))

    def _build_enumerated_option(self, option_name, title):
        option_def = Options.OPTIONS[option_name]
        enum_type = option_def.type
        assert issubclass(enum_type, enum.Enum)
        val_to_inst = {x.value: x for x in enum_type}

        current = self.model.options[option_name].value
        select_ui = mdl.Select(
            title=title, value=current,
            options=[x.value for x in enum_type])

        def on_change(attr, old_state, new_state):
            assert attr == 'value'
            del old_state
            self.controller.set_option(option_name, val_to_inst[new_state])

        select_ui.on_change('value', on_change)
        self.option_uis[option_name] = select_ui
        return select_ui

    def _build_int_option(self, option_name, title):
        current = self.model.options[option_name]
        select_ui = mdl.Slider(
            title=title, value=current, start=1, end=30)

        def on_change(attr, old_state, new_state):
            assert attr == 'value'
            del old_state
            self.controller.set_option(option_name, new_state)

        select_ui.on_change('value', on_change)
        self.option_uis[option_name] = select_ui

    def build_sources_layout(self):
        divs = []
        # was initially going to make this a set, but Source objects have a
        # dict, and aren't immutable... also, number of sources is small enough
        # that iterating over list should be fine
        seen = []
        for cache_item in datamod.data_cache.values():
            retriever = cache_item.retriever
            source = retriever.source()
            if source in seen:
                continue
            seen.append(source)
            lines = []
            for data_type in retriever.data_types():
                entity = data_type.entity
                if isinstance(entity, Entity):
                    entity_name = str(entity)
                else:
                    entity_name = entity.__name__
                lines.append('<b>{} {}:</b>'.format(entity_name,
                                                    data_type.data_type))
            lines.append('{}'.format(source.name))
            links = ['<a href="{}">{}</a>'.format(url, name)
                     for name, url in source.urls.items()]
            links = ', '.join(links)
            date = cache_item.max_date()
            if date is not None:
                date = date.strftime('%a, %x')
                lines.append('Most recent data: {}'.format(date))
            lines.append('Links: {}'.format(links))
            divs.append(mdl.Div(text='<br>'.join(lines)))
        return lyt.column(divs)

    def make_plot(self, data):
        y_label = '{} {}'.format(
            self.model.options['daily'].value.title(),
            self.model.options['ystat'].value.title(),
        )
        pop_adj = self.model.options['population_adjustment']
        if pop_adj == PopulationAdjustment.per_million:
            y_label += '/million'
        elif pop_adj != PopulationAdjustment.raw:
            raise ValueError(pop_adj)
        title = "Covid 19 - {} since 1 death/million".format(y_label)
        plot = bokeh.plotting.figure(title=title,
           x_axis_label='Days since 1 death/million', y_axis_label=y_label,
           y_axis_type=self.model.options['yscale'].name)
        user_agent = self.doc.session_context.request.headers.get('User-Agent')
        is_mobile = is_mobile_agent(user_agent)
        if is_mobile:
            # disable the toolbar on mobile, as it's annoying
            plot.toolbar_location = None
            plot.toolbar.active_drag = None
            plot.toolbar.active_scroll = None

        plot.add_layout(self.updated, "below")

        for entity, line_data in data:
            plot.line(x='days', y='y', source=line_data,
                      line_width=3, color=self.color(entity),
                      legend_label=str(entity))

        plot.legend.location = "top_left"
        plot.sizing_mode = "stretch_both"
        return plot

    def update_plot(self, data=None):
        if data is None:
            if self._last_data is None:
                raise RuntimeError(
                    "The first time {}.update_plot is called, the data arg must"
                    " be supplied".format(type(self).__name__))
            data = self._last_data
        else:
            self._last_data = data
        self.plot = self.make_plot(data)
        self.controls_plot.children[1] = self.plot

    def update_visibility(self):
        self.build_entity_ui_rows(self.entities_layout)


class Controller(object):
    '''Main class for making changes

    Handles installation + coordination of callbacks / events.  All requests to
    change state must go through here.
    '''
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller(self)

    def start(self, query=None):
        # initial entities to graph
        if not query:
            initial_entities = DEFAULT_INITIAL_ENTITIES
            for entity in initial_entities:
                self.model.entities.add(entity)
        else:
            self.model.set_from_query_dict(query)

        # build view after getting the model, so initial settings are right
        self.view.build()

        # update the visibility widget and the plot
        self.update_all_visible()

    def add_entity(self, entity):
        if entity in self.model.entities:
            return
        self.model.entities.add(entity)
        assert self.model.entities.is_visible(entity)
        self.view.update_visibility()
        self.update_plot()

    def remove_entity(self, entity):
        self.model.entities.remove(entity)
        self.view.update_visibility()
        self.update_plot()

    def set_option(self, option_name, value):
        self.model.options[option_name] = value
        self.update_plot()

    def update_plot(self):
        self.view.update_plot(self.model.make_dataset())

    def update_all_visible(self, visible_entities=None, update_view=True,
                           update_plot=True):
        if visible_entities is not None:
            for entity in visible_entities:
                self.update_visible(entity, update_view=False,
                                    update_plot=False)
        if update_view:
            self.view.update_visibility()
        if update_plot:
            self.update_plot()

    def update_visible(self, entity, visible, update_view=True,
                       update_plot=True):
        self.model.entities.set_visibility(entity, visible)
        if update_view:
            self.view.update_visibility()
        if update_plot:
            self.update_plot()


def modify_doc(doc):
    model = Model()
    view = View(doc, model)
    controller = Controller(model, view)
    query = doc.session_context.request.arguments
    controller.start(query=query)


if __name__ == '__main__':
    # Set up an application
    handler = bokeh.application.handlers.FunctionHandler(modify_doc)
    app = bokeh.application.Application(handler)

    # add something like this to the environment of a server
    #os.environ['BOKEH_ALLOW_WS_ORIGIN'] = 'localhost:8888,servername.com:80'

    bokeh.plotting.show(app)
elif __name__.startswith('bokeh_app_'):
    from bokeh.plotting import curdoc
    modify_doc(curdoc())
