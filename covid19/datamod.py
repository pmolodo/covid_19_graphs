'''Concrete Implementations of DataRetrievers and DataCache'''

import attr
import pandas

from .retrievers import DataSource, DataRetriever, DataCache, DataCacheItem, \
    FileCachedRetriever

NYC_BURROUGHS = [
    'New York County',
    'Kings County',
    'Bronx County',
    'Richmond County',
    'Queens County',
]


# make up nycity's fips as -1
NYCITY_FIPS = -1

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


@attr.s(auto_attribs=True)
class UsPopulationRetriever(DataRetriever):
    _source: DataSource

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "US Population Data"

    def retrieve(self) -> pandas.DataFrame:
        orig_url = self.source().urls['data']
        orig_data = pandas.read_csv(orig_url, encoding='IBM850')
        trimmed_data = orig_data[(orig_data.SUMLEV == 40)
                                 | (orig_data.SUMLEV == 50)]
        trimmed_data = trimmed_data[[
            'SUMLEV', 'STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'POPESTIMATE2019']]
        return trimmed_data


@attr.s(auto_attribs=True)
class CountyPopulationRetriever(DataRetriever):
    us_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self.us_pop_cache_item.retriever.source()

    @classmethod
    def data_name(cls) -> str:
        return "US County Population Data"

    def retrieve(self) -> pandas.DataFrame:
        all_pop_data = self.us_pop_cache_item.get()
        county_pop_data = all_pop_data[all_pop_data.SUMLEV == 50][
            ['STATE', 'COUNTY', 'POPESTIMATE2019']
        ]
        county_pop_data[
            'fips'] = county_pop_data.STATE * 1000 + county_pop_data.COUNTY
        county_pop_data = county_pop_data[['fips', 'POPESTIMATE2019']]
        county_pop_data = county_pop_data.rename(columns={
            'POPESTIMATE2019': 'population',
        })
        county_pop_data = county_pop_data.set_index('fips')
        return self.add_nyc(all_pop_data, county_pop_data)

    def add_nyc(self, all_pop_data: pandas.DataFrame,
                county_pop_data: pandas.DataFrame) -> pandas.DataFrame:
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


@attr.s(auto_attribs=True)
class StatePopulationRetriever(DataRetriever):
    us_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self.us_pop_cache_item.retriever.source()

    @classmethod
    def data_name(cls) -> str:
        return "US State Population Data"

    def retrieve(self) -> pandas.DataFrame:
        all_pop_data = self.us_pop_cache_item.get()

        state_pop_data = all_pop_data[all_pop_data.SUMLEV == 40][
            ['STATE', 'STNAME', 'POPESTIMATE2019']
        ]
        state_pop_data = state_pop_data.rename(columns={
            'POPESTIMATE2019': 'population',
            'STATE': 'fips',
            'STNAME': 'state',
        })
        return state_pop_data.set_index('fips')


@attr.s(auto_attribs=True)
class CountryPopulationRetriever(DataRetriever):
    _source: DataSource

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "Global Country Population Data"

    def retrieve(self) -> pandas.DataFrame:
        orig_url = self.source().urls['data']
        un_pop_raw_data = pandas.read_csv(orig_url)
        un_pop_data = un_pop_raw_data[un_pop_raw_data['Time'] == 2019]
        # all data <= 2019 is automatically in "medium" variant - VarID = 2
        drop_columns = ['Variant', 'VarID', 'Time', 'MidPeriod', 'PopMale', 'PopFemale', 'PopDensity']
        un_pop_data = un_pop_data.drop(drop_columns, axis='columns')
        un_pop_data = un_pop_data.reset_index(drop=True)
        un_pop_data = un_pop_data.rename(columns={'Location': 'country', 'PopTotal': 'population'})
        # un_pop_data is in thousands
        un_pop_data['population'] *= 1000

        # Use "United States" both because it's shorter, and it's what OWID uses
        un_pop_data = un_pop_data.replace(
            {'United States of America': 'United States'})
        un_pop_data = un_pop_data.astype({'population': int})
        return un_pop_data


@attr.s(auto_attribs=True)
class CountyDeathsRetriever(DataRetriever):
    _source: DataSource
    county_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "US County Deaths Data"

    def retrieve(self) -> pandas.DataFrame:
        url = self.source().urls['data']
        counties_raw_data = pandas.read_csv(url, parse_dates=['date'])

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
        county_pop_data = self.county_pop_cache_item.get()
        counties_fips = set(counties_data.fips.unique())
        county_pop_fips = set(county_pop_data.index.unique())
        assert len(counties_fips - county_pop_fips) == 0

        counties_states = set(counties_data.state.unique())
        abbrev_states = set(state_to_abbrev)
        assert len(counties_states - abbrev_states) == 0

        counties_data = pandas.merge(counties_data, county_pop_data, left_on='fips', right_on=county_pop_data.index)
        counties_data['cases_per_million'] = counties_data.cases / (counties_data.population / 1e6)
        counties_data['deaths_per_million'] = counties_data.deaths / (counties_data.population / 1e6)

        return counties_data.rename(columns={'county': 'name'})


@attr.s(auto_attribs=True)
class StateDeathsRetriever(DataRetriever):
    _source: DataSource
    state_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "US State Deaths Data"

    def retrieve(self) -> pandas.DataFrame:
        states_raw_data = pandas.read_csv(self.source().urls['data'],
                                          parse_dates=['date'])
        states_data = states_raw_data.astype({'fips': int})

        state_pop_data = self.state_pop_cache_item.get()

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

        return states_data.rename(columns={'state': 'name'})


# Note: I think this could be genericized to also handle CountyDeathsRetriever /
# StateDeathsRetriever.  Only thing those do differently is that they also
# do validation between the pop data + the deaths data, so would need a way to
# handle that (probably with a parameter, to say no validation /
# subset validation / exact match validation... as well as parameters to say
# what fields to join on)
@attr.s(auto_attribs=True)
class PopModifiedDeathsRetriever(DataRetriever):
    '''Modifies the raw_retriever to add in popuplation data'''
    raw_retreiver: DataRetriever
    pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self.raw_retreiver.source()

    def data_name(self) -> str:
        return self.raw_retreiver.data_name()

    def retrieve(self) -> pandas.DataFrame:
        country_deaths_data = self.raw_retreiver.retrieve()

        pop_data = self.pop_cache_item.get()

        country_deaths_data = pandas.merge(country_deaths_data, pop_data[
            ['country', 'population']], how='inner',
                                           left_on='name',
                                           right_on='country')
        country_deaths_data[
            'deaths_per_million'] = country_deaths_data.deaths / (
                    country_deaths_data.population / 1e6)
        return country_deaths_data


@attr.s(auto_attribs=True)
class JHUCountryDeathsData(DataRetriever):
    _source: DataSource

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "Country Deaths Data"

    def retrieve(self) -> pandas.DataFrame:
        country_deaths_raw_data = pandas.read_csv(self.source().urls['data'])
        country_deaths_data = country_deaths_raw_data.rename(columns={
            'Country/Region': 'name',
            'Province/State': 'province',
        })
        # filter out province / state data for now (might want to eventually support this)
        country_deaths_data = country_deaths_data[country_deaths_data.province.isna()]
        country_deaths_data = country_deaths_data.drop(['province', 'Lat', 'Long'], axis='columns')
        country_deaths_data = country_deaths_data.melt(id_vars=['country'], var_name='date', value_name='deaths')
        country_deaths_data['date'] = pandas.to_datetime(country_deaths_data.date)
        return country_deaths_data


@attr.s(auto_attribs=True)
class OWIDCountryDeathsRetriever(DataRetriever):
    _source: DataSource

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_name(cls) -> str:
        return "Country Deaths Data"

    def retrieve(self) -> pandas.DataFrame:
        country_deaths_raw_data = pandas.read_csv(self.source().urls['data'],
                                                  parse_dates=['date'])
        country_deaths_data = country_deaths_raw_data.rename(columns={
            'location': 'name',
            'total_deaths': 'deaths',
        })
        country_deaths_data = country_deaths_data.drop(
            ['new_cases', 'new_deaths', 'total_cases'], axis='columns')
        return country_deaths_data


data_cache = DataCache()

data_cache.add('us_pop', FileCachedRetriever(
    UsPopulationRetriever(
        DataSource(
            name="United States Census Bureau",
            urls={
                'site': 'https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902',
                'data': 'https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv',
            },
        )
    ),
    'co-est2019-alldata.zip',
))

data_cache.add('county_pop', CountyPopulationRetriever(data_cache['us_pop']))

data_cache.add('state_pop', StatePopulationRetriever(data_cache['us_pop']))

data_cache.add('country_pop', FileCachedRetriever(
    CountryPopulationRetriever(
        DataSource(
            name="United Nations Department of Economic and Social Affairs",
            urls={
                'site': 'https://population.un.org/wpp/Download/Standard/CSV/',
                'data': 'https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/CSV_FILES/WPP2019_TotalPopulationBySex.csv',
            },
        )
    ),
    'WPP2019_TotalPopulationBySex.zip',
))


data_cache.add('county_deaths', CountyDeathsRetriever(
    DataSource(
        name="New York Times Covid-19 Data",
        urls={
            'site': 'https://raw.githubusercontent.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
        },
    ),
    data_cache['county_pop'],
))

data_cache.add('state_deaths', StateDeathsRetriever(
    DataSource(
        name="New York Times Covid-19 Data",
        urls={
            'site': 'https://raw.githubusercontent.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv',
        },
    ),
    data_cache['state_pop'],
))

data_cache.add('country_deaths', PopModifiedDeathsRetriever(
    OWIDCountryDeathsRetriever(
        DataSource(
            name="Our World In Data",
                urls={
                'site': 'https://github.com/owid/covid-19-data/tree/master/public/data',
                'data': 'https://covid.ourworldindata.org/data/ecdc/full_data.csv',
            },
        )
    ),
    data_cache['country_pop'],
))

# Currently not used - doesn't have data for US, or summed data for Australia,
# and a few other countries

# data_cache.add('JHUcountry_deaths', PopModifiedDeathsRetriever(
#     JHUCountryDeathsData(
#         DataSource(
#             name="Johns Hopkins University Center for Systems Science and Engineering",
#             urls={
#                 'site': 'https://github.com/CSSEGISandData/COVID-19',
#                 'data': 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv',
#             },
#         )
#     ),
#     data_cache['country_pop'],
# ))
