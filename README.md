Working on a dash app to track Montreal's ER status that includes 
recently released data on current patient counts etc

notes to myself on how to deploy this app on render:
* update pip with: <code>pip install --upgrade pip setuptools wheel && pip install -r requirements.txt</code>
as suggested [here](https://community.plotly.com/t/migrating-from-heroku-how-to-use-render-to-deploy-a-python-dash-app-solution/68048)
* <code>gunicorn app:server</code>
* in script under <code>app = Dash(__name__)</code> add line <code>server = app.server</code> as suggested in [video](https://www.youtube.com/watch?v=H16dZMYmvqo) 
* on render set environment variable: PYTHON_VERSION = 3.10.5