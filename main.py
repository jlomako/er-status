import dash
from dash import html

# Create the Dash app
app = dash.Dash()

# Define the layout of the app
app.layout = html.Div([
    html.H1('Hello, Dash!'),
    html.Div('Dash: A web application framework for Python.')
])

if __name__ == '__main__':
    # Run the app
    app.run_server(debug=True)
