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
    fig = px.line(df, x=x_col, y=y_col,
                  color_discrete_sequence=['#1f77b4', '#ff7f0e'],
                  labels={"value": label, "variable": ""}, title=title, height=300)
    fig.update_layout(legend=dict(orientation="h", x=1, y=1, xanchor="right", yanchor="bottom"))
    fig.update_layout(xaxis_tickmode='auto', xaxis_dtick='1D', template="plotly_white",
                      yaxis=dict(range=[0, 160]) if label == "Number of Patients" else dict(range=[0, 260]),
                      margin=dict(l=0, r=0, t=10, b=10))
    return fig


# load data
df_occupancy = get_data("occupancy.csv")
df_waiting = get_data("patients_waiting.csv")
df_total = get_data("patients_total.csv")

# DISPLAY CURRENT DATA
# to do: correct 0 and NA in barplot

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
hospitals = list(df_occupancy.columns[1:22]) # without TOTAL MONTREAL
# list(df_occupancy.columns[1::]) # with TOTAL MONTREAL


# Create interactive dash app with bootstrap theme
app = Dash(__name__,
           title='Current Montreal ER Status',
           external_stylesheets=[dbc.themes.COSMO],
           meta_tags=[
               {"name": "viewport", "content": "width=device-width, initial-scale=1"},
                     ],
)
# app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

# for render deployment
server = app.server

# layout
app.layout = dbc.Container([
    html.Br(),
    html.H1('Montréal Emergency Room Status'),
    html.Br(),
    html.H5(f"last updated: {df_occupancy['Date'].max().date()} at {df_occupancy['Date'].max().hour}:{df_occupancy['Date'].max().minute} "),
    html.Br(),
    dbc.Tabs(id="upper-tabs", active_tab='patients_waiting',
             children=[
                 dbc.Tab(label='Patients Waiting', tab_id='patients_waiting'),
                 dbc.Tab(label='Patients Total', tab_id='patients_total'),
                 dbc.Tab(label='Occupancy Rate', tab_id='occupancy')
             ]),
    dcc.Graph(id='graph-fig-bar', config={'displayModeBar': False}),
    dbc.Alert([
        html.H6(dcc.Markdown('''
        **Patients Waiting**: The number of patients in the emergency room who are waiting to be seen by a physician.  
        **Patients Total**: The total number of patients in the emergency room, including those who are currently waiting to be seen by a physician.  
        **Occupancy Rate**: The occupancy rate refers to the percentage of stretchers that are occupied by patients. An occupancy rate of over 100% 
        indicates that the emergency room is over capacity, typically meaning that there are more patients than there are stretchers.
        '''))
    ], color="primary"),
    html.Br(),
    html.Br(),
    html.H2('Select a hospital for more information: '),
    dcc.Dropdown(hospitals, id='select-hospital', value='CHUM'),
    html.Br(),
    html.H6(id='current-hospital'), # recent data comes in here
    dbc.Tabs(id="tabs", active_tab='tab1',
             children=[
                 dbc.Tab(label='Patient Counts', tab_id='tab1'),
                 dbc.Tab(label='Occupancy Rate', tab_id='tab2'),
                 # dbc.Tab(label='Wait Times', tab_id='tab3')
             ]),
    html.Div(id='graph-container'), # contains figures for selected hospital
    html.Br(),
    html.H6("Data source: Ministère de la Santé et des Services sociaux du Québec",
                style={"paddingLeft": "10px", 'text-align': 'center'}),
    html.H6(children=['© Copyright 2023, ', html.A('jlomako', href="https://github.com/jlomako/"), '.'],
            style={"paddingLeft": "10px", 'text-align': 'center'}),
], fluid=False)


@app.callback(
    Output('graph-fig-bar', 'figure'),
    Input('upper-tabs', 'active_tab'))
def update_graph(tab): # tab = patients_waiting, patients_total or occupancy
    fig_bar = px.bar(
       df_current[df_current['hospital_name'] != 'TOTAL MONTRÉAL'].sort_values(by=tab),
       x=tab, y="hospital_name",
       #title=tab,
       orientation='h',  # horizontal
       text_auto=True,  # show numbers
       height=600,
       color=tab,
       color_continuous_scale="blues"
    ).update_layout(
        xaxis_title="",
        yaxis_title="",
        template="plotly_white",
        bargap=0.1,
        margin=dict(l=0, r=0, t=10, b=10),
    ).update_traces(
        textfont_size=12,
        textangle=0,
        textposition="auto",
        cliponaxis=False
    ).update_coloraxes(showscale=False  # remove legend
    ).update_xaxes(showticklabels=False, # remove y axis label
                   showgrid=False)  # remove grid lines
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
    fig1 = plot_data(df, "Date", ["patients_total", "patients_waiting"], "Number of Patients")
    fig2 = plot_data(df, "Date", ["occupancy"], "Occupancy Rate (%)")
    # get mean patient counts over 24h and plot as fig_mean
    df_mean_by_hour = df.groupby(df['Date'].dt.hour).mean(numeric_only=True).reset_index()
    fig_mean = px.bar(df_mean_by_hour, x="Date", y=["patients_total", "patients_waiting"],
                      labels={"value": "mean", "variable": ""},
                      #title="Average Patient counts over 24h",# selected,
                      height=300,
                      barmode='overlay',
                      color_discrete_sequence=['#1f77b4', '#ff7f0e'])
    fig_mean.update_layout(legend=dict(orientation="h", x=1, y=1, xanchor="right", yanchor="bottom"))
    fig_mean.update_layout(xaxis_tickmode='array', xaxis_tickvals=df_mean_by_hour['Date'],
                           xaxis_ticktext=[str(i) + ":00" for i in df_mean_by_hour['Date']],
                           yaxis=dict(range=[0, 150]),
                           template="plotly_white", bargap=0.1,
                           margin=dict(l=0, r=0, b=5))


    if tab == 'tab1':
        return dcc.Graph(figure=fig1, config={'displayModeBar': False}), html.Br(), html.H6(f"{selected}: Average Patient Counts over 24 hours"), dcc.Graph(figure=fig_mean, config={'displayModeBar': False})
    elif tab == 'tab2':
        return dcc.Graph(figure=fig2, config={'displayModeBar': False})
    # elif tab == 'tab3':
    #     return html.H6("Coming soon...")

# returns current values for selected hospital:
@app.callback(
    Output('current-hospital', 'children'),
    Input('select-hospital', 'value'))
def update_hospital(selected):
    current_values = df_current[df_current['hospital_name'] == selected]
    return dcc.Markdown((f'''
    **{current_values.iloc[0,0]}
    on {df_occupancy['Date'].max().date()} at {df_occupancy['Date'].max().hour}:{df_occupancy['Date'].max().minute}**:  
    Out of a total of **{int(current_values.iloc[0,3])}
    ** patients in the emergency room, **{int(current_values.iloc[0,2])}
    ** are waiting to be seen by a physician. 
    The current occupancy rate is at **{int(current_values.iloc[0,1])}**%.  
    '''))


# Run app
if __name__ == '__main__':
    app.run_server(debug=True)
