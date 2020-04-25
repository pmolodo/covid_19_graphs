# coding: utf-8

# helpful links:
# - https://towardsdatascience.com/data-visualization-with-bokeh-in-python-part-ii-interactions-a4cf994e2512
# - https://realpython.com/lessons/using-groupfilter-and-cdsview/

import pandas

import abc
import datetime
import inspect
import re
import os
import pathlib
import urllib

import bokeh.application.handlers
import bokeh.layouts as lyt
import bokeh.models as mdl
import bokeh.plotting

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
# DataGrabbers

class DataGrabber(abc.ABC):

    _data = None
    last_update_time = None

    @classmethod
    def get(cls):
        # Want to make sure we this the _data on THIS class, not any parent
        # classes...
        if '_data' not in cls.__dict__:
            cls._data = cls.retrieve()
        return cls._data

    @classmethod
    def retrieve(cls):
        result = cls._retrieve()
        cls.last_update_time = datetime.datetime.now()
        result.grabber = cls
        return result

    @classmethod
    @abc.abstractmethod
    def data_name(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def source_name(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def source_urls(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _retrieve(cls):
        raise NotImplementedError

    @classmethod
    def max_date(cls):
        if 'date' in cls._data.columns:
            return cls._data.date.max()
        return None

    # TODO: this should probably be moved into it's own subclass...?
    @classmethod
    def local_file(cls):
        # if we've imported as a module, use the path of this module
        this_file = pathlib.Path(inspect.getsourcefile(DataGrabber))
        if this_file.is_file():
            return str(this_file.parent.parent / cls.LOCAL_FILE)
        # otherwise, assume that cwd is the repo root!
        return os.path.join('.', cls.LOCAL_FILE)


class USPopulationData(DataGrabber):
    LOCAL_FILE = 'co-est2019-alldata.zip'

    @classmethod
    def data_name(cls):
        return "US Population Data"

    @classmethod
    def source_name(cls):
        return "United States Census Bureau"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902',
            'data': 'https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv',
        }

    @classmethod
    def _retrieve(cls):
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
        # trimmed_data.to_csv(cls.local_file(), index=False,
        #                     compression=compression_opts)
        # assert trimmed_data[trimmed_data.STNAME.str.contains(SEP)].empty
        # assert trimmed_data[trimmed_data.CTYNAME.str.contains(SEP)].empty

        return pandas.read_csv(cls.local_file())


class CountyPopulationData(USPopulationData):
    @classmethod
    def data_name(cls):
        return "US County Population Data"

    @classmethod
    def _retrieve(cls):
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


class StatePopulationData(USPopulationData):
    @classmethod
    def data_name(cls):
        return "US State Population Data"

    @classmethod
    def _retrieve(cls):
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
    LOCAL_FILE = 'WPP2019_TotalPopulationBySex.zip'

    @classmethod
    def data_name(cls):
        return "Global Country Population Data"

    @classmethod
    def source_name(cls):
        return "United Nations Department of Economic and Social Affairs"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://population.un.org/wpp/Download/Standard/CSV/',
            'data': 'https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/CSV_FILES/WPP2019_TotalPopulationBySex.csv',
        }

    @classmethod
    def _retrieve(cls):
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
        # un_pop_data.to_csv(cls.local_file(), index=False,
        #                    compression=compression_opts)

        return pandas.read_csv(cls.local_file())


class CountyDeathsData(DataGrabber):
    @classmethod
    def data_name(cls):
        return "US County Deaths Data"

    @classmethod
    def source_name(cls):
        return "New York Times Covid-19 Data"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://raw.githubusercontent.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
        }

    @classmethod
    def _retrieve(cls):
        counties_raw_data = pandas.read_csv(cls.source_urls()['data'],
                                            parse_dates=['date'])

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
    @classmethod
    def data_name(cls):
        return "US State Deaths Data"

    @classmethod
    def source_name(cls):
        return "New York Times Covid-19 Data"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://raw.githubusercontent.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv',
        }

    @classmethod
    def _retrieve(cls):
        states_raw_data = pandas.read_csv(cls.source_urls()['data'],
                                          parse_dates=['date'])
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
    def data_name(cls):
        return "Country Deaths Data"

    @classmethod
    def _retrieve(cls):
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
    @classmethod
    def source_name(cls):
        return "Johns Hopkins University Center for Systems Science and Engineering"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://github.com/CSSEGISandData/COVID-19',
            'data': 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv',
        }

    @classmethod
    def _retrieve_raw(cls):
        country_deaths_raw_data = pandas.read_csv(cls.source_urls()['data'])
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
    @classmethod
    def source_name(cls):
        return "Our World In Data"

    @classmethod
    def source_urls(cls):
        return {
            'site': 'https://github.com/owid/covid-19-data/tree/master/public/data',
            'data': 'https://covid.ourworldindata.org/data/ecdc/full_data.csv',
        }

    @classmethod
    def _retrieve_raw(cls):
        country_deaths_raw_data = pandas.read_csv(cls.source_urls()['data'],
                                                  parse_dates=['date'])
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


class Model(object):
    '''Only holds data
    Can be queried or altered, but has no knowledge of any other entities, or
    logic for handling callbacks / notifications'''
    def __init__(self):
        self.counties_data = CountyDeathsData.get()
        self.states_data = StateDeathsData.get()
        self.countries_data = OWIDCountryDeathsData.get()
        self.entities = DisplayEntities()

    def last_update_time(self):
        return max(x.grabber.last_update_time for x in
                   [self.counties_data, self.states_data, self.countries_data])

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

    def serialize(self):
        return self.entities.serialize()

    def to_query(self):
        as_dict = self.serialize()
        return urllib.parse.urlencode(as_dict, doseq=True)

    def set_from_query(self, parsed_query):
        # unlike urllib.parse.urlencode, whatever bokeh uses to get
        # it's args back doesn't handle str (unicode), and leaves things as
        # bytes... so first, need to convert everything to str
        parsed_query = {key: [x.decode('utf-8') for x in val]
                        for key, val in parsed_query.items()}

        # otherwise, only thing we need to convert is hidden indices, from
        # str to int, since urllib.parse.urlencode doesn't preserve type
        hidden = parsed_query.pop('hidden', None)
        if hidden:
            hidden = [int(x) for x in hidden]
            parsed_query['hidden'] = hidden
        self.entities = DisplayEntities.deserialize(parsed_query)


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

        self.entities_layout = lyt.column([], width_policy="max")
        self.build_entity_ui_rows(self.entities_layout)
        self.add_entity_layout = self.build_add_entity_layout()
        self.sources_layout = self.build_sources_layout()

        # Make tabs
        self.view_tab = mdl.Panel(child=self.entities_layout,
                                  title='View/Remove')
        self.add_tab = mdl.Panel(child=self.add_entity_layout, title='Add')
        self.sources_tab = mdl.Panel(child=self.sources_layout, title='Info')
        self.tabs = mdl.Tabs(tabs=[self.view_tab,
                                   self.add_tab,
                                   self.sources_tab])
        for tab in self.tabs.tabs:
            tab.child.width_policy = 'min'
        self.tabs.width_policy = 'min'

        # Create a row layout for tabs + plot

        # actual plot will be replace by make_plot when we have data, and
        # are ready to draw
        self.plot = bokeh.plotting.figure(title="Dummy placeholder plot")

        self.controls_plot = mdl.Row(self.tabs, self.plot)
        self.controls_plot.sizing_mode = "stretch_both"

        self.save_button = self.build_save_button()
        self.main_layout = mdl.Column(self.controls_plot, self.save_button,
                                      sizing_mode='stretch_both')
        self.doc.add_root(self.main_layout)

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
            querystr = self.model.to_query()
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
        all_countries = self.model.graphable_countries()
        self.pick_country_dropdown = mdl.Select(
            title="Country:", value="Spain", options=all_countries)
        self.add_country_button = mdl.Button(label="Add Country")

        def click_add_country():
            self.controller.add_entity(
                Country(self.pick_country_dropdown.value))

        self.add_country_button.on_click(click_add_country)

        # State
        all_states = self.model.graphable_states()
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
            all_counties = self.model.graphable_counties(
                self.pick_state_dropdown.value)
            self.pick_county_dropdown.options = all_counties
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

    def build_sources_layout(self):
        grabbers = [
            USPopulationData,
            CountryPopulationData,
            CountyDeathsData,
            StateDeathsData,
            # Currently not used
            # JHUCountryDeathsData,
            OWIDCountryDeathsData,
        ]
        divs = []
        for grabber in grabbers:
            lines = []
            lines.append('{} from:'.format(grabber.data_name()))
            lines.append('{}'.format(grabber.source_name()))
            links = ['<a href="{}">{}</a>'.format(url, name)
                     for name, url in grabber.source_urls().items()]
            links = ', '.join(links)
            print(grabber)
            date = grabber.max_date()
            if date is not None:
                date = date.strftime('%a, %x')
                lines.append('Most recent data: {}'.format(date))
            lines.append('Links: {}'.format(links))
            divs.append(mdl.Div(text='<br>'.join(lines)))
        return lyt.column(divs)

    def make_plot(self, data):
        plot = bokeh.plotting.figure(title="Covid 19 - deaths since 1/million",
           x_axis_label='Days since 1 death/million', y_axis_label='Deaths/million',
           y_axis_type='log')
        user_agent = self.doc.session_context.request.headers.get('User-Agent')
        is_mobile = is_mobile_agent(user_agent)
        if is_mobile:
            # disable the toolbar on mobile, as it's annoying
            plot.toolbar_location = None
            plot.toolbar.active_drag = None
            plot.toolbar.active_scroll = None

        last_update_time = self.model.last_update_time()
        updated_str = last_update_time.strftime('Updated: %a, %x %X')
        updated = mdl.Title(text=updated_str, align="right",
                            text_font_size="8pt", text_font_style="normal")
        plot.add_layout(updated, "below")

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
        self.view.build()

        # initial entities to graph
        if not query:
            initial_entities = DEFAULT_INITIAL_ENTITIES
            for entity in initial_entities:
                self.model.entities.add(entity)
        else:
            self.model.set_from_query(query)

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
    handler = bokeh.application.handlers.FunctionHandler(modify_doc)
    app = bokeh.application.Application(handler)

    # add something like this to the environment of a server
    #os.environ['BOKEH_ALLOW_WS_ORIGIN'] = 'localhost:8888,servername.com:80'

    bokeh.plotting.show(app)
elif __name__.startswith('bokeh_app_'):
    from bokeh.plotting import curdoc
    modify_doc(curdoc())
