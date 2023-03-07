from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import timedelta

nr_of_days = 7


def get_data(file):
    df = pd.read_csv("https://github.com/jlomako/hospital-occupancy-tracker/raw/main/tables/"+file,
        parse_dates=['Date']).drop_duplicates('Date').rename(
        columns={"HÔPITAL DE SOINS PSYCHIATRIQUES DE L'EST-DE-MONTRÉAL": "HÔPITAL DE SOINS PSYCHIATRIQUES",
                 "L'HÔPITAL DE MONTRÉAL POUR ENFANTS": "HÔPITAL DE MONTRÉAL POUR ENFANTS",
                 "CENTRE HOSPITALIER DE L'UNIVERSITÉ DE MONTRÉAL": "CHUM"})
    df['Date'] = pd.DatetimeIndex(df['Date']).floor('H') + pd.Timedelta(minutes=46) # set all to 46min
    df = df[(df["Date"] >= (df['Date'].max() - timedelta(days=nr_of_days))) & (df["Date"] <= df['Date'].max())]
    return df


def get_selected(df, selected, variable):
    df = df.filter(items=['Date', selected]).rename(columns={selected: variable})
    # create df_range with timestamps for every hour then merge
    date_range = pd.date_range(start=df['Date'].min(), end=df['Date'].max(), freq='H')
    df_range = pd.DataFrame({'Date': date_range})
    df = pd.merge(df_range, df, on='Date', how='outer')
    return df


def plot_data(df, x_col, y_col, label, title=None):
    fig = px.line(df, x=x_col, y=y_col, labels={"value": label, "variable": ""}, title=title)
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    fig.update_layout(legend=dict(orientation="h", x=1, y=1, xanchor="right", yanchor="bottom"))
    fig.update_layout(xaxis_tickmode='auto', xaxis_dtick='1D', template="plotly_white")
    return fig


# load data
df_occupancy = get_data("occupancy.csv")
df_waiting = get_data("patients_waiting.csv")
df_total = get_data("patients_total.csv")

# DISPLAY CURRENT DATA

# create df with latest data
df_current = pd.merge(df_occupancy.iloc[-1, 1:].reset_index().set_axis(['hospital_name', 'occupancy'], axis=1),
               df_waiting.iloc[-1, 1:].reset_index().set_axis(['hospital_name', 'patients_waiting'], axis=1),
               on='hospital_name', how='outer')
df_current = pd.merge(df_current,
               df_total.iloc[-1, 1:].reset_index().set_axis(['hospital_name', 'patients_total'], axis=1),
               on='hospital_name', how='outer')

# transform cols to numeric
df_current[df_current.columns[1:]] = df_current[df_current.columns[1:]].apply(pd.to_numeric, errors='coerce')


options = {
    "Patients waiting": {"selection": ['patients_waiting', 'patients_total'], "sort": 'patients_waiting', "title": f"Patient counts on {df_waiting['Date'].max()}"},
    "Patients total": {"selection": ['patients_waiting', 'patients_total'], "sort": 'patients_total', "title": f"Patient counts on {df_total['Date'].max()}"},
    "Occupancy Rate": {"selection": "occupancy", "sort": "occupancy", "title": f"Occupancy Rates on {df_occupancy['Date'].max()}"},
}

# SELECT HOSPITAL
hospitals = list(df_occupancy.columns[1::])


# Create interactive dash app with bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

# idea: show data table and then charts (in tabs/ cards?)

# layout
app.layout = dbc.Container([
    html.Br(),
    html.H1('Montréal Emergency Room Status'),
    html.P('Sort from highest to lowest by:'),
    dbc.Tabs(id="upper-tabs", active_tab='patients_waiting',
             children=[
                 dbc.Tab(label='Patients waiting', tab_id='patients_waiting'),
                 dbc.Tab(label='Patients Total', tab_id='patients_total'),
                 dbc.Tab(label='Occupancy Rate', tab_id='occupancy')
             ]),
    dcc.Graph(id='graph-fig-bar'),
    html.H6('Patients Waiting: The number of patients in the emergency room who are waiting to be seen by a physician.'),
    html.H6('Patients Total: The total number of patients in the emergency room, '
            'including those who are currently waiting to be seen by a physician.'),
    html.H6('Occupancy Rate: The occupancy rate refers to the percentage of stretchers that are occupied '
            'by patients. An occupancy rate of over 100% indicates that the emergency room is over capacity, '
            'typically meaning that there are more patients than there are stretchers.'),
    html.Br(),
    html.Br(),
    html.H2('Select a hospital for more information: '),
    dcc.Dropdown(hospitals, id='select-hospital', value='CHUM'),
    html.Br(),
    dbc.Tabs(id="tabs", active_tab='tab1',
             children=[
                 dbc.Tab(label='Patient Counts', tab_id='tab1'),
                 dbc.Tab(label='Occupancy Rate', tab_id='tab2'),
                 dbc.Tab(label='Wait times', tab_id='tab3')
             ]),
    html.Div(id='graph-container') # contains figures for selected hospital
    ])


@app.callback(
    Output('graph-fig-bar', 'figure'),
    # Input('radio-buttons', 'value'),
    Input('upper-tabs', 'active_tab'))
def update_graph(tab):
    fig_bar = px.bar(
       df_current[df_current['hospital_name'] != 'TOTAL MONTRÉAL'].sort_values(by=tab),
       x=tab, y="hospital_name",
       title=tab,
       orientation='h',  # horizontal
       text_auto=True,  # show numbers
       height=700,
       color=tab,
       color_continuous_scale="blues"
    ).update_layout(
        xaxis_title="",
        yaxis_title="",
        xaxis_fixedrange=True,  # switch of zoom functions etc
        yaxis_fixedrange=True,
        template="plotly_white",
        bargap=0.1
    ).update_traces(
        textfont_size=12,
        textangle=0,
        textposition="auto",
        cliponaxis=False
    ).update_coloraxes(showscale=False  # remove legend
    ).update_xaxes(showticklabels=False)  # remove y axis label

    # Barplot with patient counts (patients waiting and patients total in one plot):
    # fig_bar = px.bar(
    #     df_current[df_current['hospital_name'] != 'TOTAL MONTRÉAL'].sort_values(by=options[option]["sort"]),
    #     x=options[option]["selection"], y="hospital_name",
    #     title=options[option]["title"],
    #     labels={"value": "", "variable": ""},
    #     orientation='h',  # horizontal
    #     text_auto=True,  # show numbers
    #     height=700,
    #     barmode='overlay' if options[option]["sort"] != "occupancy" else None,
    #     color_discrete_sequence=['#023858', '#2c7fb8'] if options[option]["sort"] != "occupancy" else None,
    #     color=options[option]["sort"] if options[option]["sort"] == "occupancy" else None,
    #     color_continuous_scale="blues" if options[option]["sort"] == "occupancy" else None,
    #     ).update_layout(
    #     xaxis_title="",
    #     yaxis_title="",
    #     xaxis_fixedrange=True,  # switch off annoying zoom functions
    #     yaxis_fixedrange=True,
    #     template="plotly_white",
    #     bargap=0.1,  # gap between bars
    #     legend=dict(orientation="h", x=1, y=1, xanchor="right", yanchor="bottom")
    # ).update_traces(
    #     textfont_size=12,
    #     textangle=0,
    #     textposition="auto",
    #     cliponaxis=False
    # ).update_coloraxes(showscale=False  # remove legend for color_continuous_scale
    # ).update_xaxes(showticklabels=False)
    return fig_bar


# select hospital and return figures in tabs:
@app.callback(
    Output('graph-container', 'children'),
    Input('select-hospital', 'value'),
    Input('tabs', 'active_tab'))
def update_fig(selected, tab):
    df = pd.merge(get_selected(df_occupancy, selected, "occupancy"),
                  get_selected(df_waiting, selected, "patients_waiting"), on='Date', how='outer')
    df = pd.merge(df, get_selected(df_total, selected, "patients_total"), on='Date', how='outer')
    fig1 = plot_data(df, "Date", ["patients_waiting", "patients_total"], "Number of Patients")
    fig2 = plot_data(df, "Date", ["occupancy"], "Occupancy Rate")
    if tab == 'tab1':
        return dcc.Graph(figure=fig1)
    elif tab == 'tab2':
        return dcc.Graph(figure=fig2)
    elif tab == 'tab3':
        return html.P('coming soon')


# Run app
if __name__ == '__main__':
    app.run_server(debug=True)


# select hospital and return 2 figures in layout:
    # html.Div(id='fig1-container'),
    # html.Div(id='fig2-container')
# @app.callback(
#     [Output('fig1-container', 'children'),
#      Output('fig2-container', 'children')],
#     Input('select-hospital', 'value'))
# def update_fig(selected):
#     df = pd.merge(get_selected(df_occupancy, selected, "occupancy"),
#                   get_selected(df_waiting, selected, "patients_waiting"), on='Date', how='outer')
#     df = pd.merge(df, get_selected(df_total, selected, "patients_total"), on='Date', how='outer')
#     fig1 = plot_data(df, "Date", ["patients_waiting", "patients_total"], "Number of Patients")
#     fig2 = plot_data(df, "Date", "occupancy", "Occupancy Rate")
#     return dcc.Graph(figure=fig1), dcc.Graph(figure=fig2)


    ### radioItems that create bar plot with separate plots for each option:
    ## Layout:
    # dbc.RadioItems(id='radio-buttons', options=[{'label': k, 'value': k} for k in options.keys()],
    #                inline=True,
    #                value="Patients waiting"
    #                ),
    ## Callback:
    # @app.callback(
    #     Output('graph-fig-bar', 'figure'),
    #     Input('radio-buttons', 'value'),
    #def update_graph(option):
    # fig_bar = px.bar(df_current[df_current['hospital_name'] != 'TOTAL MONTRÉAL'].sort_values(by=options[option]["sort"]),
    #    x=options[option]["sort"], y="hospital_name",
    #    title=options[option]["title"],
    #    orientation='h',  # horizontal
    #    text_auto=True,  # show numbers
    #    height=700)



