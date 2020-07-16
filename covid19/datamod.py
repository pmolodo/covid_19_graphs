'''Concrete Implementations of DataRetrievers and DataCache'''

import attr
import pandas

from typing import List, Type

from . import constants

from .entities import Country, County, State
from .retrievers import DataSource, DataRetriever, DataCache, DataCacheItem, \
    EntityDataType, FileCachedRetriever

@attr.s(auto_attribs=True)
class UsPopulationRetriever(DataRetriever):
    _source = DataSource(
        id='us_census',
        name='United States Census Bureau',
        urls={
            'site': 'https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902',
            'data': 'https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv',
        },
    )

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [EntityDataType(Country('United States'), 'population')]

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
    def data_types(cls) -> List[EntityDataType]:
        return [EntityDataType(County, 'population')]

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
        for burrough in constants.NYC_BURROUGHS:
            burrough_data = all_pop_data[
                (all_pop_data.STNAME == 'New York')
                & (all_pop_data.CTYNAME == burrough)]
            assert len(burrough_data) == 1
            nycity_pop += burrough_data.POPESTIMATE2019.iat[0]

        county_pop_data.loc[constants.NYCITY_FIPS] = nycity_pop
        return county_pop_data


@attr.s(auto_attribs=True)
class StatePopulationRetriever(DataRetriever):
    us_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self.us_pop_cache_item.retriever.source()

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [EntityDataType(State, 'population')]

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
class UNCountryPopulationRetriever(DataRetriever):
    _source = DataSource(
        id='UN',
        name="United Nations Department of Economic and Social Affairs",
        urls={
            'site': 'https://population.un.org/wpp/Download/Standard/CSV/',
            'data': 'https://population.un.org/wpp/Download/Files/1_Indicators%20(Standard)/CSV_FILES/WPP2019_TotalPopulationBySex.csv',
        },
    )

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [EntityDataType(Country, 'population')]

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
class NYTimesCountyDataRetriever(DataRetriever):
    _source = DataSource(
        id='nytimes',
        name="New York Times Covid-19 County Data",
        urls={
            'site': 'https://github.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
        },
    )

    county_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [
            EntityDataType(County, 'deaths'),
            EntityDataType(County, 'cases'),
        ]

    def retrieve(self) -> pandas.DataFrame:
        url = self.source().urls['data']
        counties_raw_data = pandas.read_csv(url, parse_dates=['date'])

        #nycity_data = counties_raw_data[counties_raw_data.county == 'New York City'].copy()
        #nycity_data.fips = NYCITY_FIPS

        counties_raw_data.loc[counties_raw_data.county == 'New York City', 'fips'] = constants.NYCITY_FIPS

        # Process county covid data

        counties_data = counties_raw_data[counties_raw_data.fips.notna()]
        counties_data = counties_data.astype({'fips': int})
        #counties_data['state_fips'] = counties_data.fips // 1000
        #counties_data['county_fips'] = counties_data.fips % 1000
        #counties_data['county_state'] = counties_data['county'].str.cat(counties_data['state'], sep =", ")
        #all_counties = (counties_data['county_state'].unique())

        # Filter to only remaining counties that have population data
        county_pop_data = self.county_pop_cache_item.get()
        #counties_fips = set(counties_data.fips.unique())
        #county_pop_fips = set(county_pop_data.index.unique())
        counties_data = counties_data[counties_data.fips.isin(county_pop_data.index)]

        counties_states = set(counties_data.state.unique())
        assert len(counties_states - constants.US_STATES) == 0

        counties_data = pandas.merge(counties_data, county_pop_data, left_on='fips', right_on=county_pop_data.index)

        return counties_data.rename(columns={'county': 'name'})


@attr.s(auto_attribs=True)
class NYTimesStateDataRetriever(DataRetriever):
    _source = DataSource(
        id='nytimes',
        name="New York Times Covid-19 State Data",
        urls={
            'site': 'https://github.com/nytimes/covid-19-data',
            'data': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv',
        },
    )

    state_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [
            EntityDataType(State, 'deaths'),
            EntityDataType(State, 'cases'),
        ]

    def retrieve(self) -> pandas.DataFrame:
        # final columns: name, fips, population, cases, deaths
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

        # Confirm all states in nytimes data have abbreviations
        states_states = set(states_data.state.unique())
        assert len(states_states - constants.US_STATES) == 0

        return states_data.rename(columns={'state': 'name'})


# Note: I think this could be genericized to also handle
# NYTimesCountyDataRetriever / NYTimesStateDataRetriever.  Only thing those
# do differently is that they also do validation between the pop data + the
# deaths data, so would need a way to handle that (probably with a parameter,
# to say no validation / subset validation / exact match validation... as
# well as parameters to say what fields to join on)
@attr.s(auto_attribs=True)
class PopModifiedDeathsRetriever(DataRetriever):
    '''Modifies the raw_retriever to add in popuplation data'''
    raw_retreiver: DataRetriever
    pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self.raw_retreiver.source()

    def data_types(self) -> List[EntityDataType]:
        return self.raw_retreiver.data_types()

    def retrieve(self) -> pandas.DataFrame:
        country_deaths_data = self.raw_retreiver.retrieve()

        pop_data = self.pop_cache_item.get()
        country_deaths_data = pandas.merge(country_deaths_data, pop_data[
            ['country', 'population']], how='inner',
                                           left_on='name',
                                           right_on='country')
        return country_deaths_data


@attr.s(auto_attribs=True)
class JHUCountryDeathsData(DataRetriever):
    _source = DataSource(
        id='JHU',
        name="Johns Hopkins University Center for Systems Science and Engineering",
        urls={
            'site': 'https://github.com/CSSEGISandData/COVID-19',
            'data': 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv',
        },
    )

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [
            EntityDataType(Country, 'deaths'),
            EntityDataType(Country, 'cases'),
        ]

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
class OWIDCountryDataRetriever(DataRetriever):
    _source = DataSource(
        id='OWID',
        name='Our World In Data',
            urls={
            'site': 'https://github.com/owid/covid-19-data/tree/master/public/data',
            'data': 'https://covid.ourworldindata.org/data/ecdc/full_data.csv',
        },
    )

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [
            EntityDataType(Country, 'deaths'),
            EntityDataType(Country, 'cases'),
        ]

    def retrieve(self) -> pandas.DataFrame:
        country_raw_data = pandas.read_csv(self.source().urls['data'],
                                                  parse_dates=['date'])
        country_data = country_raw_data.rename(columns={
            'location': 'name',
            'total_deaths': 'deaths',
            'total_cases': 'cases',
        })
        country_data = country_data.drop(
            ['new_cases', 'new_deaths'], axis='columns')
        return country_data


@attr.s(auto_attribs=True)
class CovidTrackingStateDataRetriever(DataRetriever):
    _source = DataSource(
        id='covid_tracking',
        name='Covid Tracking Project',
            urls={
            'site': 'https://covidtracking.com/data/api',
            'data': 'https://covidtracking.com/api/v1/states/daily.csv',
        },
    )

    state_pop_cache_item: DataCacheItem

    def source(self) -> DataSource:
        return self._source

    @classmethod
    def data_types(cls) -> List[EntityDataType]:
        return [
            EntityDataType(State, 'deaths'),
            EntityDataType(State, 'cases'),
            EntityDataType(State, 'hospitalizations'),
            # EntityDataType(State, 'icu'),
            # EntityDataType(State, 'ventilator'),
        ]

    def retrieve(self) -> pandas.DataFrame:
        # final columns:
        #   name, fips, population,
        #   cases,
        #   deaths,
        #   hospitalizations, hospitalizations:current,
        #   icu, icu:current,
        #   ventilator, ventilator:current

        raw_data = pandas.read_csv(self.source().urls['data'],
                                                  parse_dates=['date'])

        # start by dropping fields project itself has declared deprecated
        DEPRECATED = [
            'checkTimeEt',
            'commercialScore',
            'dateChecked',
            'dateModified',
            'grade',
            'hash',
            'hospitalized',
            'negativeIncrease',
            'negativeRegularScore',
            'negativeScore',
            'posNeg',
            'positiveScore',
            'score',
            'total',
        ]

        # ...and fields we currently don't use...
        unused = [
            'positiveCasesViral',
            'positiveTestsViral',
            'negative',
            'pending',
            'recovered',
            'dataQualityGrade',
            'lastUpdateEt',
            'totalTestsViral',
            'negativeTestsViral',
            'positiveIncrease',
            'totalTestResults',
            'totalTestResultsIncrease',
            'deathIncrease',
            'hospitalizedIncrease',
        ]
        data = raw_data.drop(DEPRECATED + unused, axis='columns')

        data = data.rename(columns={
            'positive': 'cases',
            'death': 'deaths',
            'hospitalizedCumulative': 'hospitalizations',
            'hospitalizedCurrently': 'hospitalizations:current',
            'inIcuCumulative': 'icu',
            'inIcuCurrently': 'icu:current',
            'onVentilatorCumulative': 'ventilator',
            'onVentilatorCurrently': 'ventilator:current',
        })

        # kept_as_is = ['date', 'fips']

        state_pop_data = self.state_pop_cache_item.get()

        # data has some territories, for which we don't yet have pop data...
        state_pop_fips = set(state_pop_data.index.unique())
        # state_pop_data has 50 states + DC
        assert len(state_pop_fips) == 51
        states_fips = set(data.fips.unique())
        assert state_pop_fips.issubset(states_fips)

        data = pandas.merge(data, state_pop_data['population'], how='inner',
                            left_on='fips', right_on=state_pop_data.index)

        # Convert all states to unabbreviated values
        data['name'] = [constants.ABBREV_TO_STATE[x] for x in data.state]
        data = data.drop(['state'], axis='columns')

        # the covid tracking project data goes by date, descending - put it
        # ascending
        data = data.sort_values(['date']).reset_index(drop=True)

        return data


data_cache = DataCache()

data_cache.add(FileCachedRetriever(
    UsPopulationRetriever(),
    'co-est2019-alldata.zip',
))

data_cache.add(CountyPopulationRetriever(
    data_cache[Country('United States'), 'population', 'us_census']))

data_cache.add(StatePopulationRetriever(
    data_cache[Country('United States'), 'population', 'us_census']))

data_cache.add(FileCachedRetriever(
    UNCountryPopulationRetriever(),
    'WPP2019_TotalPopulationBySex.zip',
))

data_cache.add(NYTimesCountyDataRetriever(
    data_cache[County, 'population', 'us_census'],
))

# data_cache.add(NYTimesStateDataRetriever(
#     data_cache[State, 'population', 'us_census'],
# ))

data_cache.add(CovidTrackingStateDataRetriever(
    data_cache[State, 'population', 'us_census'],
))

data_cache.add(PopModifiedDeathsRetriever(
    OWIDCountryDataRetriever(),
    data_cache[Country, 'population', 'UN'],
))

# Currently not used - doesn't have data for US, or summed data for Australia,
# and a few other countries

# data_cache.add(PopModifiedDeathsRetriever(
#     JHUCountryDeathsData(),
#     data_cache[Country, 'population', 'UN'],
# ))

