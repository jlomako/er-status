from dash import Dash, dcc, html, Input, Output
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
    fig.update_layout(xaxis_tickmode='auto', xaxis_dtick='1D')
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
#df_current.iloc[:, 1:] = df_current.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')
df_current[df_current.columns[1:]] = df_current[df_current.columns[1:]].apply(pd.to_numeric, errors='coerce')


options = {
    "Patients waiting": {"selection": ['patients_waiting', 'patients_total'] , "sort": 'patients_waiting', "title": f"Patient counts on {df_waiting['Date'].max()}"},
    "Patients total": {"selection": ['patients_waiting', 'patients_total'], "sort": 'patients_total', "title": f"Patient counts on {df_total['Date'].max()}"},
    "Occupancy Rate": {"selection": "occupancy", "sort": "occupancy", "title": f"Occupancy Rates on {df_occupancy['Date'].max()}"},
}

#option = st.radio("Sort from highest to lowest by:", options.keys(), horizontal=True)
#option = "Occupancy Rate"




# Create app
app = Dash(__name__)

# Define layout
app.layout = html.Div([
    html.H1('Montréal Emergency Room Status'),
    html.Div('Sort from highest to lowest by:'),
    dcc.RadioItems(id='radio-buttons', options=[{'label': k, 'value': k} for k in options.keys()],
                   inline=True, value="Occupancy Rate"),
    dcc.Graph(id='graph-fig-bar')
    ])


@app.callback(
    Output('graph-fig-bar', 'figure'),
    Input('radio-buttons', 'value'))
def update_graph(option):
    fig_bar = px.bar(
        df_current[df_current['hospital_name'] != 'TOTAL MONTRÉAL'].sort_values(by=options[option]["sort"]),
        x=options[option]["selection"], y="hospital_name",
        title=options[option]["title"],
        labels={"value": "", "variable": ""},
        orientation='h',  # horizontal
        text_auto=True,  # show numbers
        height=700,
        barmode='overlay' if options[option]["sort"] != "occupancy" else None,
        color_discrete_sequence=['#023858', '#2c7fb8'] if options[option]["sort"] != "occupancy" else None,
        color=options[option]["sort"] if options[option]["sort"] == "occupancy" else None,
        color_continuous_scale="blues" if options[option]["sort"] == "occupancy" else None,
        ).update_layout(
        xaxis_title="",
        yaxis_title="",
        xaxis_fixedrange=True,  # switch off annoying zoom functions
        yaxis_fixedrange=True,
        bargap=0.1,  # gap between bars
        legend=dict(orientation="h", x=1, y=1, xanchor="right", yanchor="bottom")
    ).update_traces(
        textfont_size=12,
        textangle=0,
        textposition="auto",
        cliponaxis=False
    ).update_coloraxes(showscale=False  # remove legend for color_continuous_scale
    ).update_xaxes(showticklabels=False)

    return fig_bar


# Run app
if __name__ == '__main__':
    app.run_server(debug=True)
