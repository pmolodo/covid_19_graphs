# coding: utf-8

# helpful links:
# - https://towardsdatascience.com/data-visualization-with-bokeh-in-python-part-ii-interactions-a4cf994e2512
# - https://realpython.com/lessons/using-groupfilter-and-cdsview/

# In[1]:


import pandas
import math


# In[2]:


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


# In[3]:


# County population data from us census
#     https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902
#     https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv

all_pop_data = pandas.read_csv('./co-est2019-alldata.csv', encoding='IBM850')
#with open('./co-est2019-alldata.csv') as f:
#    text = f.read()
county_pop_data = all_pop_data[all_pop_data.SUMLEV == 50][
    ['STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'POPESTIMATE2019']
]
county_pop_data['fips'] = county_pop_data.STATE * 1000 + county_pop_data.COUNTY
county_pop_data[county_pop_data.fips == 6037]


# In[4]:


county_pop_data = county_pop_data[['fips', 'POPESTIMATE2019']]
county_pop_data = county_pop_data.rename(columns={
    'POPESTIMATE2019': 'population',
})
county_pop_data = county_pop_data.set_index('fips')
county_pop_data[county_pop_data.index == 6037]


# In[5]:


state_pop_data = all_pop_data[all_pop_data.SUMLEV == 40][
    ['STATE', 'STNAME', 'POPESTIMATE2019']
]
state_pop_data = state_pop_data.rename(columns={
    'POPESTIMATE2019': 'population',
    'STATE': 'fips',
    'STNAME': 'state',
})
state_pop_data = state_pop_data.set_index('fips')
state_pop_data[state_pop_data.index == 6]


# In[6]:


nytimes_counties_url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'
counties_raw_data = pandas.read_csv(nytimes_counties_url, parse_dates=['date'])
# fips codes are left out for, ie, New York City, and "Unknown" groupings for states


# In[7]:


# New York city is special - the city is divided into 5 counties (that's backward!)
# It's obviously so weird that even the New York Times doesn't abide by this, and just lists
# one entry for "New York City" - need to deal with this foolishness specially

new_york_burroughs = [
    'New York County',
    'Kings County',
    'Bronx County',
    'Richmond County',
    'Queens County',
]

nycity_pop = 0
for burrough in new_york_burroughs:
    burrough_data = all_pop_data[(all_pop_data.STNAME == 'New York') & (all_pop_data.CTYNAME == burrough)]
    assert len(burrough_data) == 1
    nycity_pop += burrough_data.POPESTIMATE2019.iat[0]

    # make up nycity's fips as -1
NYCITY_FIPS = -1

county_pop_data.loc[NYCITY_FIPS] = nycity_pop

#nycity_data = counties_raw_data[counties_raw_data.county == 'New York City'].copy()
#nycity_data.fips = NYCITY_FIPS

counties_raw_data.loc[counties_raw_data.county == 'New York City', 'fips'] = NYCITY_FIPS
counties_raw_data[counties_raw_data.county == 'New York City']

county_pop_data[county_pop_data.index == NYCITY_FIPS]


# In[8]:


counties_data = counties_raw_data[counties_raw_data.fips.notna()]
counties_data = counties_data.astype({'fips': int})
#counties_data['state_fips'] = counties_data.fips // 1000
#counties_data['county_fips'] = counties_data.fips % 1000
#counties_data['county_state'] = counties_data['county'].str.cat(counties_data['state'], sep =", ")
#all_counties = (counties_data['county_state'].unique())

# Confirm all counties in nytimes data have population data
counties_fips = set(counties_data.fips.unique())
county_pop_fips = set(county_pop_data.index.unique())
assert len(counties_fips - county_pop_fips) == 0

counties_data = pandas.merge(counties_data, county_pop_data, left_on='fips', right_on=county_pop_data.index)
counties_data['cases_per_million'] = counties_data.cases / (counties_data.population / 1e6)
counties_data['deaths_per_million'] = counties_data.deaths / (counties_data.population / 1e6)


# In[9]:


nytimes_states_url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv'
states_raw_data = pandas.read_csv(nytimes_states_url, parse_dates=['date'])
states_data = states_raw_data.astype({'fips': int})

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
states_data.head()


# In[10]:


# Confirm all states in nytimes data have abbreviations
counties_states = set(counties_data.state.unique())
abbrev_states = set(state_to_abbrev)
assert len(counties_states - abbrev_states) == 0
states_states = set(states_data.state.unique())
assert len(states_states - abbrev_states) == 0


# In[11]:


# get country population data
# from https://population.un.org/wpp/Download/Standard/CSV/
un_pop_raw_data = pandas.read_csv('WPP2019_TotalPopulationBySex.csv')
un_pop_data = un_pop_raw_data[un_pop_raw_data['Time'] == 2019]
# all data <= 2019 is automatically in "medium" variant - VarID = 2
drop_columns = ['Variant', 'VarID', 'Time', 'MidPeriod', 'PopMale', 'PopFemale', 'PopDensity']
un_pop_data = un_pop_data.drop(drop_columns, axis='columns')
un_pop_data = un_pop_data.reset_index(drop=True)
un_pop_data = un_pop_data.rename(columns={'Location': 'country', 'PopTotal': 'population'})
# un_pop_data is in thousands
un_pop_data['population'] *= 1000
un_pop_data = un_pop_data.astype({'population': int})
un_pop_data


# In[12]:


# get country deaths data

JHU_global_deaths_url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
country_deaths_raw_data = pandas.read_csv(JHU_global_deaths_url)
country_deaths_data = country_deaths_raw_data.rename(columns={
    'Country/Region': 'country',
    'Province/State': 'province',
})
# filter out province / state data for now (might want to eventually support this)
country_deaths_data = country_deaths_data[country_deaths_data.province.isna()]
country_deaths_data = country_deaths_data.drop(['province', 'Lat', 'Long'], axis='columns')
country_deaths_data = country_deaths_data.melt(id_vars=['country'], var_name='date', value_name='deaths')
country_deaths_data['date'] = pandas.to_datetime(country_deaths_data.date)
country_deaths_data.head()

country_deaths_data = pandas.merge(country_deaths_data, un_pop_data[['country', 'population']], how='inner',
                           left_on='country', right_on='country')
country_deaths_data['deaths_per_million'] = country_deaths_data.deaths / (country_deaths_data.population / 1e6)
country_deaths_data[(country_deaths_data.country == 'Italy') & country_deaths_data.deaths > 0]


# In[ ]:





# In[13]:


counties_to_graph = [
    ('Los Angeles', 'California'),
    ('Orange', 'California'),
    ('Middlesex', 'Massachusetts'),
    ('New York City', 'New York'),
]

states_to_graph = [
    'California',
    'Massachusetts',
    'New York',
]

countries_to_graph = [
    'Italy',
]

to_graph_by_date = []

for county, state in counties_to_graph:
    state_abbrev = state_to_abbrev[state]
    county_data = counties_data[(counties_data.state == state) & (counties_data.county == county)]
    assert len(county_data) > 0
    label = ', '.join([county, state_abbrev])
    to_graph_by_date.append((label, county_data))

for state in states_to_graph:
    state_abbrev = state_to_abbrev[state]
    state_data = states_data[states_data.state == state]
    assert len(state_data) > 0
    to_graph_by_date.append((state_abbrev, state_data))

for country in countries_to_graph:
    country_data = country_deaths_data[country_deaths_data.country == country]
    assert len(country_data) > 0
    to_graph_by_date.append((country, country_data))

#counties_selected_data[('Los Angeles', 'CA')]
print(to_graph_by_date[0][0])
to_graph_by_date[0][1]


# In[14]:


def get_data_since(data, condition_func):
    condition = condition_func(data)
    since_data = data[condition].reset_index(drop=True)
    day0 = since_data.date.min()
    since_data['days'] = (since_data.date - day0).apply(lambda x: x.days)
    return since_data

def deaths_per_mill_greater_1(data):
    return data.deaths_per_million >= 1.0

to_graph_by_since = []

for label, data in to_graph_by_date:
    to_graph_by_since.append((label, get_data_since(data, deaths_per_mill_greater_1)))

print(to_graph_by_since[5][0])
to_graph_by_since[5][1]


# In[ ]:





# In[15]:


from collections import OrderedDict

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


# In[25]:


import os

from bokeh.models import Column, Panel #, CategoricalColorMapper, HoverTool, ColumnDataSource
from bokeh.models.widgets import CheckboxGroup, Tabs #, Slider, RangeSlider

from bokeh.layouts import row

from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application

from bokeh.plotting import figure, output_notebook, show

from collections import namedtuple

class CommaJoinedTuple(object):
    def __str__(self):
        return ', '.join(str(x) for x in self)

class Country(CommaJoinedTuple, namedtuple('CountryBase', ['name'])):
    pass

class State(CommaJoinedTuple, namedtuple('State', ['name'])):
    pass

class County(CommaJoinedTuple, namedtuple('CountyBase', ['name', 'state'])):
    pass


def modify_doc(doc):
    all_display_items = [
        County('Los Angeles', 'CA'),
        County('Orange', 'CA'),
        County('Middlesex', 'MA'),
        County('New York City', 'NY'),
        State('California'),
        State('Massachusetts'),
        State('New York'),
        Country('Italy'),
    ]

    to_color = {item: kelly_colors[i % len(kelly_colors)] for i, item in enumerate(all_display_items)}

    def make_dataset(items_to_plot):
        to_graph_by_date = []
        for item in items_to_plot:
            label = str(item)
            if isinstance(item, County):
                county, state_abbrev = item
                state = abbrev_to_state[state_abbrev]
                county_data = counties_data[(counties_data.state == state) & (counties_data.county == county)]
                assert len(county_data) > 0
                to_append = (label, county_data)

            elif isinstance(item, State):
                state = item.name
                state_data = states_data[states_data.state == state]
                assert len(state_data) > 0
                to_append = (label, state_data)

            elif isinstance(item, Country):
                country = item.name
                country_data = country_deaths_data[country_deaths_data.country == country]
                assert len(country_data) > 0
                to_append = (label, country_data)
            else:
                raise TypeError(item)
            to_append += (to_color[item],)
            to_graph_by_date.append(to_append)

        def get_data_since(data, condition_func):
            condition = condition_func(data)
            since_data = data[condition].reset_index(drop=True)
            day0 = since_data.date.min()
            since_data['days'] = (since_data.date - day0).apply(lambda x: x.days)
            return since_data

        def deaths_per_mill_greater_1(data):
            return data.deaths_per_million >= 1.0

        to_graph_by_since = []

        for label, data, color in to_graph_by_date:
            to_graph_by_since.append((label, get_data_since(data, deaths_per_mill_greater_1), color))
        return to_graph_by_since

    def make_plot(data):
        plot = figure(title="Covid 19 - deaths since 1/million",
           x_axis_label='Days since 1 death/million', y_axis_label='Deaths/million',
           y_axis_type='log')

        # Want to enable this, but it makes graphs not display at all on iphone (chrome + safari)
        #plot.sizing_mode = 'scale_height'

        for label, data, color in data:
            plot.line(x='days', y='deaths_per_million', source=data,
                   line_width=3, color=color, legend_label=label)

        plot.legend.location = "top_left"
        return plot

    def update(attr, old, new):
        display_items = [all_display_items[i] for i in selection.active]
        data = make_dataset(display_items)
        plot = make_plot(data)
        layout.children[1] = plot

    selection = CheckboxGroup(labels=[str(x) for x in all_display_items],
                              active=list(range(len(all_display_items))))
    selection.on_change('active', update)

    controls = Column(selection)

    data = make_dataset(all_display_items)
    plot = make_plot(data)

    # Create a row layout
    layout = row(controls, plot)

    doc.add_root(layout)

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
