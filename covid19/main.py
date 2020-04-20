# coding: utf-8

# helpful links:
# - https://towardsdatascience.com/data-visualization-with-bokeh-in-python-part-ii-interactions-a4cf994e2512
# - https://realpython.com/lessons/using-groupfilter-and-cdsview/

import pandas

import abc
import urllib

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.layouts import row, column
from bokeh.models import Button, Column, CustomJS, Div, Paragraph, Row, Select,\
    Spacer
from bokeh.models.widgets import CheckboxGroup
from bokeh.plotting import figure, show

from collections import OrderedDict, namedtuple

################################################################################
# Constants

state_to_abbrev = {
    'Alabama': 'AL',
    'Alaska': 'AK',
    'American Samoa': 'AS',
    'Arizona': 'AZ',
    'Arkansas': 'AR',
    'California': 'CA',
    'Colorado': 'CO',
    'Connecticut': 'CT',
    'Delaware': 'DE',
    'District of Columbia': 'DC',
    'Federated States of Micronesia': 'FM',
    'Florida': 'FL',
    'Georgia': 'GA',
    'Guam': 'GU',
    'Hawaii': 'HI',
    'Idaho': 'ID',
    'Illinois': 'IL',
    'Indiana': 'IN',
    'Iowa': 'IA',
    'Kansas': 'KS',
    'Kentucky': 'KY',
    'Louisiana': 'LA',
    'Maine': 'ME',
    'Marshall Islands': 'MH',
    'Maryland': 'MD',
    'Massachusetts': 'MA',
    'Michigan': 'MI',
    'Minnesota': 'MN',
    'Mississippi': 'MS',
    'Missouri': 'MO',
    'Montana': 'MT',
    'Nebraska': 'NE',
    'Nevada': 'NV',
    'New Hampshire': 'NH',
    'New Jersey': 'NJ',
    'New Mexico': 'NM',
    'New York': 'NY',
    'North Carolina': 'NC',
    'North Dakota': 'ND',
    'Northern Mariana Islands': 'MP',
    'Ohio': 'OH',
    'Oklahoma': 'OK',
    'Oregon': 'OR',
    'Palau': 'PW',
    'Pennsylvania': 'PA',
    'Puerto Rico': 'PR',
    'Rhode Island': 'RI',
    'South Carolina': 'SC',
    'South Dakota': 'SD',
    'Tennessee': 'TN',
    'Texas': 'TX',
    'Utah': 'UT',
    'Vermont': 'VT',
    'Virgin Islands': 'VI',
    'Virginia': 'VA',
    'Washington': 'WA',
    'West Virginia': 'WV',
    'Wisconsin': 'WI',
    'Wyoming': 'WY',
}


abbrev_to_state = dict((abbrev, state) for (state, abbrev) in state_to_abbrev.items())


NYC_BURROUGHS = [
    'New York County',
    'Kings County',
    'Bronx County',
    'Richmond County',
    'Queens County',
]


# make up nycity's fips as -1
NYCITY_FIPS = -1

SEP = ';'


################################################################################
# Colors

# Thanks to Kenneth Kelly + Ohad Schneider:
# https://stackoverflow.com/a/13781114/920545
kelly_colors_dict = OrderedDict(
    black=(0,0,0),
    vivid_yellow=(255, 179, 0),
    strong_purple=(128, 62, 117),
    vivid_orange=(255, 104, 0),
    very_light_blue=(166, 189, 215),
    vivid_red=(193, 0, 32),
    grayish_yellow=(206, 162, 98),
    medium_gray=(129, 112, 102),

    # these aren't good for people with defective color vision:
    vivid_green=(0, 125, 52),
    strong_purplish_pink=(246, 118, 142),
    strong_blue=(0, 83, 138),
    strong_yellowish_pink=(255, 122, 92),
    strong_violet=(83, 55, 122),
    vivid_orange_yellow=(255, 142, 0),
    strong_purplish_red=(179, 40, 81),
    vivid_greenish_yellow=(244, 200, 0),
    strong_reddish_brown=(127, 24, 13),
    vivid_yellowish_green=(147, 170, 0),
    deep_yellowish_brown=(89, 51, 21),
    vivid_reddish_orange=(241, 58, 19),
    dark_olive_green=(35, 44, 22),
)
kelly_colors = list(kelly_colors_dict.values())


################################################################################
# DataGrabbers

class DataGrabber(abc.ABC):

    _data = None

    @classmethod
    def get(cls):
        if cls._data is None:
            cls._data = cls.retrieve()
        return cls._data

    @classmethod
    @abc.abstractmethod
    def retrieve(cls):
        raise NotImplementedError

# County population data from us census
#   https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902

class USPopulationData(DataGrabber):
    LOCAL_FILE = './co-est2019-alldata.zip'

    @classmethod
    def retrieve(cls):
        # If we ever need to retrieve again, uncomment this:
        # orig_url = 'https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv'
        # orig_data = pandas.read_csv(orig_url, encoding='IBM850')
        # trimmed_data = orig_data[(orig_data.SUMLEV == 40)
        #                          | (orig_data.SUMLEV == 50)]
        # trimmed_data = trimmed_data[[
        #     'SUMLEV', 'STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'POPESTIMATE2019']]
        # compression_opts = {
        #     'method': 'zip',
        #     'archive_name': 'co-est2019-alldata.trimmed.csv',
        # }
        # trimmed_data.to_csv(cls.LOCAL_FILE, index=False,
        #                     compression=compression_opts)
        # assert trimmed_data[trimmed_data.STNAME.str.contains(SEP)].empty
        # assert trimmed_data[trimmed_data.CTYNAME.str.contains(SEP)].empty

        return pandas.read_csv(cls.LOCAL_FILE)


class CountyPopulationData(DataGrabber):
    @classmethod
    def retrieve(cls):
        all_pop_data = USPopulationData.get()

        county_pop_data = all_pop_data[all_pop_data.SUMLEV == 50][
            ['STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'POPESTIMATE2019']
        ]
        county_pop_data['fips'] = county_pop_data.STATE * 1000 + county_pop_data.COUNTY
        county_pop_data = county_pop_data[['fips', 'POPESTIMATE2019']]
        county_pop_data = county_pop_data.rename(columns={
            'POPESTIMATE2019': 'population',
        })
        county_pop_data = county_pop_data.set_index('fips')
        return cls.add_nyc(all_pop_data, county_pop_data)

    @classmethod
    def add_nyc(cls, all_pop_data, county_pop_data):
        # Fixup New York City

        # New York city is special - the city is divided into 5 counties (that's backward!)
        # It's obviously so weird that even the New York Times doesn't abide by this, and just lists
        # one entry for "New York City" - need to deal with this foolishness specially

        nycity_pop = 0
        for burrough in NYC_BURROUGHS:
            burrough_data = all_pop_data[
                (all_pop_data.STNAME == 'New York')
                & (all_pop_data.CTYNAME == burrough)]
            assert len(burrough_data) == 1
            nycity_pop += burrough_data.POPESTIMATE2019.iat[0]

        county_pop_data.loc[NYCITY_FIPS] = nycity_pop
        return county_pop_data


class StatePopulationData(DataGrabber):
    @classmethod
    def retrieve(cls):
        all_pop_data = USPopulationData.get()

        state_pop_data = all_pop_data[all_pop_data.SUMLEV == 40][
            ['STATE', 'STNAME', 'POPESTIMATE2019']
        ]
        state_pop_data = state_pop_data.rename(columns={
            'POPESTIMATE2019': 'population',
            'STATE': 'fips',
            'STNAME': 'state',
        })
        return state_pop_data.set_index('fips')

# Country population estimates from the UN
#   https://population.un.org/wpp/Download/Standard/CSV/

class CountryPopulationData(DataGrabber):
    LOCAL_FILE = './WPP2019_TotalPopulationBySex.zip'

    @classmethod
    def retrieve(cls):
        # If we ever need to retrieve again, uncomment this:
        # orig_url = 'https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/CSV_FILES/WPP2019_TotalPopulationBySex.csv'
        # un_pop_raw_data = pandas.read_csv(orig_url)
        # un_pop_data = un_pop_raw_data[un_pop_raw_data['Time'] == 2019]
        # # all data <= 2019 is automatically in "medium" variant - VarID = 2
        # drop_columns = ['Variant', 'VarID', 'Time', 'MidPeriod', 'PopMale', 'PopFemale', 'PopDensity']
        # un_pop_data = un_pop_data.drop(drop_columns, axis='columns')
        # un_pop_data = un_pop_data.reset_index(drop=True)
        # un_pop_data = un_pop_data.rename(columns={'Location': 'country', 'PopTotal': 'population'})
        # # un_pop_data is in thousands
        # un_pop_data['population'] *= 1000
        #
        # # Use "United States" both because it's shorter, and it's what OWID uses
        # un_pop_data = un_pop_data.replace(
        #     {'United States of America': 'United States'})
        # un_pop_data = un_pop_data.astype({'population': int})
        # compression_opts = {
        #     'method': 'zip',
        #     'archive_name': 'WPP2019_TotalPopulationBySex.trimmed.csv',
        # }
        # assert un_pop_data[un_pop_data.country.str.contains(SEP)].empty
        # un_pop_data.to_csv(cls.LOCAL_FILE, index=False,
        #                    compression=compression_opts)

        return pandas.read_csv(cls.LOCAL_FILE)


class CountyDeathsData(DataGrabber):
    URL = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'

    @classmethod
    def retrieve(cls):
        counties_raw_data = pandas.read_csv(cls.URL, parse_dates=['date'])

        #nycity_data = counties_raw_data[counties_raw_data.county == 'New York City'].copy()
        #nycity_data.fips = NYCITY_FIPS

        counties_raw_data.loc[counties_raw_data.county == 'New York City', 'fips'] = NYCITY_FIPS

        # Process county covid data

        counties_data = counties_raw_data[counties_raw_data.fips.notna()]
        counties_data = counties_data.astype({'fips': int})
        #counties_data['state_fips'] = counties_data.fips // 1000
        #counties_data['county_fips'] = counties_data.fips % 1000
        #counties_data['county_state'] = counties_data['county'].str.cat(counties_data['state'], sep =", ")
        #all_counties = (counties_data['county_state'].unique())

        # Confirm all counties in nytimes data have population data
        county_pop_data = CountyPopulationData.get()
        counties_fips = set(counties_data.fips.unique())
        county_pop_fips = set(county_pop_data.index.unique())
        assert len(counties_fips - county_pop_fips) == 0

        counties_states = set(counties_data.state.unique())
        abbrev_states = set(state_to_abbrev)
        assert len(counties_states - abbrev_states) == 0

        counties_data = pandas.merge(counties_data, county_pop_data, left_on='fips', right_on=county_pop_data.index)
        counties_data['cases_per_million'] = counties_data.cases / (counties_data.population / 1e6)
        counties_data['deaths_per_million'] = counties_data.deaths / (counties_data.population / 1e6)

        assert counties_data[counties_data.county.str.contains(SEP)].empty
        assert counties_data[counties_data.state.str.contains(SEP)].empty

        return counties_data


class StateDeathsData(DataGrabber):
    URL = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv'

    @classmethod
    def retrieve(cls):
        states_raw_data = pandas.read_csv(cls.URL, parse_dates=['date'])
        states_data = states_raw_data.astype({'fips': int})

        state_pop_data = StatePopulationData.get()

        # the nytimes data has some territories, for which we don't yet have pop data...
        state_pop_fips = set(state_pop_data.index.unique())
        # state_pop_data has 50 states + DC
        assert len(state_pop_fips) == 51
        states_fips = set(states_data.fips.unique())
        assert state_pop_fips.issubset(states_fips)

        states_data = pandas.merge(states_data, state_pop_data['population'], how='inner',
                                   left_on='fips', right_on=state_pop_data.index)
        states_data['cases_per_million'] = states_data.cases / (states_data.population / 1e6)
        states_data['deaths_per_million'] = states_data.deaths / (states_data.population / 1e6)

        # Confirm all states in nytimes data have abbreviations
        states_states = set(states_data.state.unique())
        abbrev_states = set(state_to_abbrev)
        assert len(states_states - abbrev_states) == 0

        assert states_data[states_data.state.str.contains(SEP)].empty

        return states_data


class CountryDeathsData(DataGrabber):
    @classmethod
    def retrieve(cls):
        country_deaths_data = cls._retrieve_raw()

        un_pop_data = CountryPopulationData.get()

        country_deaths_data = pandas.merge(country_deaths_data, un_pop_data[
            ['country', 'population']], how='inner',
                                           left_on='country',
                                           right_on='country')
        country_deaths_data[
            'deaths_per_million'] = country_deaths_data.deaths / (
                    country_deaths_data.population / 1e6)

        assert country_deaths_data[country_deaths_data.country.str.contains(SEP)].empty

        return country_deaths_data

    @classmethod
    @abc.abstractmethod
    def _retrieve_raw(cls):
        raise NotImplementedError


# Currently not used - doesn't have data for US, or summed data for Australia,
# and a few other countries
class JHUCountryDeathsData(CountryDeathsData):
    URL = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'

    @classmethod
    def _retrieve_raw(cls):
        country_deaths_raw_data = pandas.read_csv(cls.URL)
        country_deaths_data = country_deaths_raw_data.rename(columns={
            'Country/Region': 'country',
            'Province/State': 'province',
        })
        # filter out province / state data for now (might want to eventually support this)
        country_deaths_data = country_deaths_data[country_deaths_data.province.isna()]
        country_deaths_data = country_deaths_data.drop(['province', 'Lat', 'Long'], axis='columns')
        country_deaths_data = country_deaths_data.melt(id_vars=['country'], var_name='date', value_name='deaths')
        country_deaths_data['date'] = pandas.to_datetime(country_deaths_data.date)
        return country_deaths_data


class OWIDCountryDeathsData(CountryDeathsData):
    URL = 'https://covid.ourworldindata.org/data/ecdc/full_data.csv'

    @classmethod
    def _retrieve_raw(cls):
        country_deaths_raw_data = pandas.read_csv(cls.URL, parse_dates=['date'])
        country_deaths_data = country_deaths_raw_data.rename(columns={
            'location': 'country',
            'total_deaths': 'deaths',
        })
        country_deaths_data = country_deaths_data.drop(
            ['new_cases', 'new_deaths', 'total_cases'], axis='columns')
        return country_deaths_data


################################################################################
# Entities - Country / State / County data types

class Entity(object):
    def __str__(self):
        return ', '.join(str(x) for x in self)

    def serialize(self):
        return SEP.join(str(x) for x in self)

    @classmethod
    def deserialize(cls, raw):
        return cls(*raw.split(SEP))

class Country(Entity, namedtuple('CountryBase', ['name'])):
    pass

class State(Entity, namedtuple('State', ['name'])):
    def __new__(cls, *args, **kwargs):
        # force non-abbreviated name
        self = super().__new__(cls, *args, **kwargs)
        if self.name in abbrev_to_state:
            self = State(abbrev_to_state[self.name])
        return self

class County(Entity, namedtuple('CountyBase', ['name', 'state'])):
    def __new__(cls, *args, **kwargs):
        # force abbreviated state name
        self = super().__new__(cls, *args, **kwargs)
        if self.state in state_to_abbrev:
            self = County(self.name, state_to_abbrev[self.state])
        return self


DEFAULT_INITIAL_ENTITIES = [
    Country('Italy'),
    State('California'),
    State('New York'),
    County('Los Angeles', 'CA'),
    County('New York City', 'NY'),
]


################################################################################
# Bokeh application logic

# Model
class DisplayEntities(object):
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

    def serialize(self):
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
    def deserialize(cls, raw):
        countries = [Country.deserialize(x) for x in raw.get('countries', [])]
        states = [State.deserialize(x) for x in raw.get('states', [])]
        counties = [County.deserialize(x) for x in raw.get('counties', [])]
        hidden = raw.get('hidden')
        return cls(countries=countries, states=states, counties=counties,
                   hidden=hidden)

    def to_query(self):
        as_dict = self.serialize()
        return urllib.parse.urlencode(as_dict, doseq=True)

    @classmethod
    def from_query(cls, parsed_query):
        # unlike urllib.parse.urlencode, whatever bokeh uses to get
        # it's args back doesn't handle str (unicode), and leaves things as
        # bytes... so first, need to convert everything to str
        parsed_query = {key: [x.decode('utf-8') for x in val]
                        for key, val in parsed_query.items()}

        # only thing we need to do is convert otherwise is hidden indices from
        # str to int, since urllib.parse.urlencode doesn't preserve type
        hidden = parsed_query.pop('hidden', None)
        if hidden:
            hidden = [int(x) for x in hidden]
            parsed_query['hidden'] = hidden
        return cls.deserialize(parsed_query)


class Model(object):
    '''Only holds data
    Can be queried or altered, but has no knowledge of any other entities, or
    logic for handling callbacks / notifications'''
    def __init__(self):
        self.counties_data = CountyDeathsData.get()
        self.states_data = StateDeathsData.get()
        self.countries_data = OWIDCountryDeathsData.get()
        self.entities = DisplayEntities()

    def graphable_countries(self):
        return sorted(
            self.countries_data[self.countries_data.deaths_per_million >= 1.0]
                .country.unique()
        )

    def graphable_states(self):
        return sorted(
            self.states_data[self.states_data.deaths_per_million >= 1.0]
                .state.unique()
        )

    def graphable_counties(self, state_name):
        return sorted(
            self.counties_data[
                (self.counties_data.state == state_name)
                & (self.counties_data.deaths_per_million >= 1.0)
            ].county.unique()
        )

    def make_dataset(self):
        counties = self.counties_data
        states = self.states_data
        countries = self.countries_data

        to_graph_by_date = []
        for entity in self.entities.visible_ordered():
            if isinstance(entity, County):
                county, state_abbrev = entity
                state = abbrev_to_state[state_abbrev]
                data = counties[(counties.state == state)
                                & (counties.county == county)]
                assert len(data) > 0, f"no county data for {county}, {state}"
            elif isinstance(entity, State):
                state = entity.name
                data = states[states.state == state]
                assert len(data) > 0, f"no state data for {state}"
            elif isinstance(entity, Country):
                country = entity.name
                data = countries[countries.country == country]
                assert len(data) > 0, f"no country data for {country}"
            else:
                raise TypeError(entity)
            to_graph_by_date.append((entity, data))

        def get_data_since(data, condition_func):
            condition = condition_func(data)
            since_data = data[condition].reset_index(drop=True)
            day0 = since_data.date.min()
            since_data['days'] = (since_data.date - day0).apply(lambda x: x.days)
            return since_data

        def deaths_per_mill_greater_1(data):
            return data.deaths_per_million >= 1.0

        to_graph_by_since = []

        for entity, data in to_graph_by_date:
            since_data = get_data_since(data, deaths_per_mill_greater_1)
            to_graph_by_since.append((entity, since_data))
        return to_graph_by_since


class View(object):
    '''Contains the bokeh UI items, and is responsible for altering them

    May interact with model is a read-only manner'''
    def __init__(self, doc, model):
        self.model = model
        self.doc = doc
        self.controller = None

    # utility methods

    def color(self, entity):
        i = self.model.entities.index(entity)
        return kelly_colors[i % len(kelly_colors)]

    def set_controller(self, controller):
        self.controller = controller

    # build

    def build(self):
        '''constructs the main layout'''
        self.doc.title = "Covid-19 Graphs"

        self.entities_ui = self.build_entity_ui_rows()
        self.add_entity_panel = self.build_add_entity_panel()

        self.controls = column(self.entities_ui,
                               Div(text="<hr width=100>"),
                               self.add_entity_panel)
        self.controls.width_policy = "min"
        # Create a row layout

        # actual plot will be replace by make_plot when we have data, and
        # are ready to draw
        self.plot = figure(title="Dummy placeholder plot")

        self.controls_plot = Row(self.controls, self.plot)
        self.controls_plot.sizing_mode = "stretch_both"

        self.save_button = self.build_save_button()
        self.main_layout = Column(self.controls_plot, self.save_button,
                                  sizing_mode='stretch_both')
        self.doc.add_root(self.main_layout)

    def build_save_button(self):
        save_button = Button(label='Save/Share')

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
        js_callback = CustomJS(code=js_code)
        save_button.js_on_change("tags", js_callback)

        def on_click():
            querystr = self.model.entities.to_query()
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
        vis_check = CheckboxGroup(labels=[str(entity)], active=active,
                                  width_policy="min")

        def update_visible(attr, old_visible_indices, visible_indices):
            del old_visible_indices
            assert visible_indices == [] or visible_indices == [0]
            self.controller.update_visible(entity, bool(visible_indices),
                                           update_view=False)

        vis_check.on_change('active', update_visible)

        spacer = Spacer(sizing_mode="stretch_width")
        delete_button = Button(label="X", button_type="danger",
                               width_policy="min", height_policy="min")

        def remove_entity():
            self.controller.remove_entity(entity)

        delete_button.on_click(remove_entity)

        return row(vis_check, spacer, delete_button)

    def build_entity_ui_rows(self):
        rows = [self.build_entity_ui_row(e) for e in self.model.entities]
        entity_column = column(rows, width_policy="max")
        return entity_column

    def build_add_entity_panel(self):
        # Country
        all_countries = self.model.graphable_countries()
        self.pick_country_dropdown = Select(
            title="Country:", value="Spain", options=all_countries)
        self.add_country_button = Button(label="Add Country")

        def click_add_country():
            self.controller.add_entity(
                Country(self.pick_country_dropdown.value))

        self.add_country_button.on_click(click_add_country)

        # State
        all_states = self.model.graphable_states()
        self.pick_state_dropdown = Select(
            title="US State:", value="California", options=all_states)
        self.add_state_button = Button(label="Add State")

        def click_add_state():
            self.controller.add_entity(
                State(self.pick_state_dropdown.value))

        self.add_state_button.on_click(click_add_state)

        # County

        self.pick_county_dropdown = Select(title="US County:")
        self.add_county_button = Button(label="Add County")

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
            all_counties = self.model.graphable_counties(
                self.pick_state_dropdown.value)
            self.pick_county_dropdown.options = all_counties
            self.pick_county_dropdown.value = all_counties[0]

        self.pick_state_dropdown.on_change('value', pick_state_changed)

        # setup initial counties list
        pick_state_changed('value', None, self.pick_state_dropdown.value)

        # Misc extra display elements
        note1 = Paragraph(text="Note: graphable entities are filtered to"
                               " only those that meet the minimum criteria")

        spacer = Spacer(height=10)

        return column(
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

    def make_plot(self, data):
        plot = figure(title="Covid 19 - deaths since 1/million",
           x_axis_label='Days since 1 death/million', y_axis_label='Deaths/million',
           y_axis_type='log')

        for entity, line_data in data:
            plot.line(x='days', y='deaths_per_million', source=line_data,
                      line_width=3, color=self.color(entity),
                      legend_label=str(entity))

        plot.legend.location = "top_left"
        plot.sizing_mode = "stretch_both"
        return plot

    def update_plot(self, data):
        self.plot = self.make_plot(data)
        self.controls_plot.children[1] = self.plot

    def update_visibility(self):
        self.entities_ui = self.build_entity_ui_rows()
        self.controls.children[0] = self.entities_ui


class Controller(object):
    '''Main class for making changes

    Handles installation + coordination of callbacks / events.  All requests to
    change state must go through here.
    '''
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller(self)

    def setView(self, view):
        self.view = view

    def start(self, query=None):
        self.view.build()

        # initial entities to graph
        if not query:
            initial_entities = DEFAULT_INITIAL_ENTITIES
            for entity in initial_entities:
                self.model.entities.add(entity)
        else:
            self.model.entities = DisplayEntities.from_query(query)

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
    handler = FunctionHandler(modify_doc)
    app = Application(handler)

    # add something like this to the environment of a server
    #os.environ['BOKEH_ALLOW_WS_ORIGIN'] = 'localhost:8888,servername.com:80'

    show(app)
else:
    from bokeh.plotting import curdoc
    modify_doc(curdoc())
