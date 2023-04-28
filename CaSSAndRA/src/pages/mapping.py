# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

#local imports
from src.components import ids
from src.components.mapping import map, uploadsunray, modal, dropdown, buttons

dash.register_page(
    __name__,
    path='/mapping',
    title='Mapping'
)

def update_layout() -> html.Div:
    return ([
        dbc.Col([
            html.Div([dcc.Graph(ids.MAPPINGMAP)], className='map-graph'),
            dbc.Row([
                html.Div([
                    uploadsunray.uploadsunray,
                    dropdown.dropdownsunrayimport,
                    buttons.saveimportedperimeter
                    ], className='text-center'
                ),
            ]),
        ], xs=12, sm=6, lg=6),
        modal.sunrayimportstatus,
        modal.overwriteperimter,
        html.Div(id=ids.MAPPINGHIDDEN, style={'display': 'none'}),
        ])

layout = update_layout()