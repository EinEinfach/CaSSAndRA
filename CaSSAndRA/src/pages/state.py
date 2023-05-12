# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

#local imports
from src.components import ids, modalmowsettings
from src.components.state import map, dropdownmaplinetype, buttongroupcontrol, state

dash.register_page(
    __name__,
    path='/',
    redirect_from=['/state'],
    title='State'
)

def update_layout() -> html.Div:
    return dbc.Container([
                dbc.Row(id=ids.STATESTRING),
                dbc.Row([dcc.Graph(id=ids.STATEMAP)], className='map-graph flex-fill'),
                dbc.Row([
                            dbc.Col([
                                buttongroupcontrol.buttonhome,
                                buttongroupcontrol.buttonmowall,
                                buttongroupcontrol.buttonzoneselect,
                                buttongroupcontrol.buttongoto,
                                buttongroupcontrol.buttonmowsettings,
                                buttongroupcontrol.buttoncancel
                            ],className="col-md-6 col-12 text-center d-flex justify-content-between"),
                ],className="mb-2"),
                dbc.Row([
                    dbc.Col([buttongroupcontrol.buttongo], class_name='d-grid col-md4'),
                    dbc.Col([buttongroupcontrol.buttonstop], class_name='d-grid col-md4'),
                ]),
                modalmowsettings.mowsettings,
                # dbc.Row([
                #     html.Div(['Show'], className='margin-5px'),
                #     dbc.Col([html.Div([dropdownmaplinetype.dropdown], className='dropdown-container')])
                # ]),
                #html.Div(id=ids.STATEHIDDEN, style={'display': 'none'}),
                #html.Div(id=ids.STATEHIDDEN2), #style={'display': 'none'}),
                #html.Div(id=ids.STATEHIDDEN3, style={'display': 'none'}),
    ],fluid=True, className='mb-2 d-flex h-100 flex-column')

layout = update_layout()
