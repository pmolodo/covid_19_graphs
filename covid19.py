# coding: utf-8

# helpful links:
# - https://towardsdatascience.com/data-visualization-with-bokeh-in-python-part-ii-interactions-a4cf994e2512
# - https://realpython.com/lessons/using-groupfilter-and-cdsview/

import pandas

import math
import os

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.layouts import row, column
from bokeh.models import Button, Div, Panel, Paragraph, Select, Spacer
from bokeh.models.widgets import CheckboxGroup, Tabs
from bokeh.plotting import figure, output_notebook, show

from collections import OrderedDict, namedtuple


# Constant mappings

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

################################################################################
# Get county population data

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

county_pop_data = county_pop_data[['fips', 'POPESTIMATE2019']]
county_pop_data = county_pop_data.rename(columns={
    'POPESTIMATE2019': 'population',
})
county_pop_data = county_pop_data.set_index('fips')

################################################################################
# Get state population data

state_pop_data = all_pop_data[all_pop_data.SUMLEV == 40][
    ['STATE', 'STNAME', 'POPESTIMATE2019']
]
state_pop_data = state_pop_data.rename(columns={
    'POPESTIMATE2019': 'population',
    'STATE': 'fips',
    'STNAME': 'state',
})
state_pop_data = state_pop_data.set_index('fips')

################################################################################
# Get county Covid-19 data

nytimes_counties_url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'
counties_raw_data = pandas.read_csv(nytimes_counties_url, parse_dates=['date'])
# fips codes are left out for, ie, New York City, and "Unknown" groupings for states

# Fixup New York City

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

# Process county covid data

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


################################################################################
# Get state Covid-19 data

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

# Confirm all states in nytimes data have abbreviations
counties_states = set(counties_data.state.unique())
abbrev_states = set(state_to_abbrev)
assert len(counties_states - abbrev_states) == 0
states_states = set(states_data.state.unique())
assert len(states_states - abbrev_states) == 0


################################################################################
# Get country population data

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


################################################################################
# Get country deaths data

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
# Country / State / County data types


class CommaJoinedTuple(object):
    def __str__(self):
        return ', '.join(str(x) for x in self)

class Country(CommaJoinedTuple, namedtuple('CountryBase', ['name'])):
    pass

class State(CommaJoinedTuple, namedtuple('State', ['name'])):
    def __new__(cls, *args, **kwargs):
        # force non-abbreviated name
        self = super().__new__(cls, *args, **kwargs)
        if self.name in abbrev_to_state:
            self = State(abbrev_to_state[self.name])
        return self

class County(CommaJoinedTuple, namedtuple('CountyBase', ['name', 'state'])):
    def __new__(cls, *args, **kwargs):
        # force abbreviated state name
        self = super().__new__(cls, *args, **kwargs)
        if self.state in state_to_abbrev:
            self = County(self.name, state_to_abbrev[self.state])
        return self


################################################################################
# Bokeh application logic

def modify_doc(doc):
    doc.title = "Covid-19 Graphs"

    # initial items to graph
    display_countries = set([
        Country('Italy'),
    ])
    display_states = set([
        State('California'),
        State('Massachusetts'),
        State('New York'),
    ])
    display_counties = set([
        County('Los Angeles', 'CA'),
        County('Orange', 'CA'),
        County('Middlesex', 'MA'),
        County('New York City', 'NY'),
        County('Allegheny', 'PA'),
    ])
    display_all = []

    to_color = {}

    def update_colors():
        to_color.clear()
        to_color.update({
            item: kelly_colors[i % len(kelly_colors)] for i, item in
            enumerate(display_all)
        })

    def update_all_display_items():
        display_all[:] = sorted(display_countries) + sorted(display_states) \
            + sorted(display_counties)
        update_colors()

    def add_display_item(item):
        if isinstance(item, Country):
            display_countries.add(item)
        elif isinstance(item, State):
            display_states.add(item)
        elif isinstance(item, County):
            display_counties.add(item)
        else:
            raise TypeError("must be a Country, State, or County - got: {!r}"
                            .format(item))
        update_all_display_items()

    # update to show initial items
    update_all_display_items()

    def make_dataset(items_to_plot):
        to_graph_by_date = []
        for item in items_to_plot:
            label = str(item)
            if isinstance(item, County):
                county, state_abbrev = item
                state = abbrev_to_state[state_abbrev]
                county_data = counties_data[(counties_data.state == state) & (counties_data.county == county)]
                assert len(county_data) > 0, f"no county data for {county}, {state}"
                to_append = (label, county_data)

            elif isinstance(item, State):
                state = item.name
                state_data = states_data[states_data.state == state]
                assert len(state_data) > 0, f"no state data for {state}"
                to_append = (label, state_data)

            elif isinstance(item, Country):
                country = item.name
                country_data = country_deaths_data[country_deaths_data.country == country]
                assert len(country_data) > 0, f"no country data for {country}"
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

    def update_vis(attr, old_vis, new_vis):
        del old_vis
        assert attr == 'active'
        display_items = [display_all[i] for i in new_vis]
        data = make_dataset(display_items)
        plot = make_plot(data)
        main_layout.children[1] = plot

    visibility_selection = CheckboxGroup(labels=[str(x) for x in display_all],
                                         active=list(range(len(display_all))))
    visibility_selection.on_change('active', update_vis)

    spacer = Spacer(height=10)

    def add_item_and_update(item):
        if item in display_all:
            return
        add_display_item(item)
        visible = set(visibility_selection.labels[i]
                      for i in visibility_selection.active)
        visible.add(str(item))
        visibility_selection.labels = [str(x) for x in display_all]
        visibility_selection.active = [
            i for i, label in enumerate(visibility_selection.labels)
            if label in visible
        ]
        update_vis('active', None, visibility_selection.active)

    all_countries = sorted(
        country_deaths_data[country_deaths_data.deaths_per_million >= 1.0]
            .country.unique())
    pick_country_dropdown = Select(title="Country:", value="Spain",
                                   options=all_countries)
    add_country_button = Button(label="Add Country")
    def click_add_country():
        add_item_and_update(Country(pick_country_dropdown.value))
    add_country_button.on_click(click_add_country)

    all_states = sorted(
        states_data[states_data.deaths_per_million >= 1.0].state.unique())
    pick_state_dropdown = Select(title="US State:", value="California",
                                 options=all_states)
    add_state_button = Button(label="Add State")

    def click_add_state():
        add_item_and_update(State(pick_state_dropdown.value))

    add_state_button.on_click(click_add_state)

    pick_county_dropdown = Select(title="US County:")
    add_county_button = Button(label="Add County")

    # update county values when state changes
    def pick_state_changed(attr, old_state, new_state):
        assert attr == 'value'
        del old_state
        all_counties = sorted(
            counties_data[
                (counties_data.state == new_state)
                & (counties_data.deaths_per_million >= 1.0)
            ].county.unique()
        )
        pick_county_dropdown.options = all_counties
        pick_county_dropdown.value = all_counties[0]

    pick_state_dropdown.on_change('value', pick_state_changed)
    pick_state_changed('value', None, pick_state_dropdown.value)

    def click_add_county():
        add_item_and_update(County(pick_county_dropdown.value,
                                   pick_state_dropdown.value))

    add_county_button.on_click(click_add_county)

    note1 = Paragraph(text="Note: graphable entities are filtered to"
                           " only those that meet the minimum criteria")
    note2 = Paragraph(text="Note: Some countries (ie Australia, US), for which"
                           " my datasource doesn't provide nicely summarized"
                           " data, currently missing")

    # TODO: get US, Australia working
    #   Get county picking working

    add_item_panel = column(pick_country_dropdown, add_country_button,
                            spacer,
                            pick_state_dropdown, add_state_button,
                            spacer,
                            pick_county_dropdown, add_county_button,
                            spacer,
                            note1, note2)

    controls = column(visibility_selection,
                      Div(text="<hr width=100>"),
                      add_item_panel)

    data = make_dataset(display_all)
    plot = make_plot(data)

    # Create a row layout
    main_layout = row(controls, plot)

    doc.add_root(main_layout)


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
