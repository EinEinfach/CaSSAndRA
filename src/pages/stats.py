# package imports
import dash
from dash import html

dash.register_page(
    __name__,
    path='/stats',
    title='Statistic'
)

layout = html.Div([html.H1('Statistic')]
)