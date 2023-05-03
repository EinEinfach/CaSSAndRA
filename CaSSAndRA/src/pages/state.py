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
    return ([
            dbc.Row([
                dbc.Col([
                    dbc.Row(id=ids.STATESTRING),
                    html.Div([dcc.Graph(id=ids.STATEMAP)], className='map-graph'),
                    #dbc.Row([inputsmowsettings.accordion]),
                    dbc.Row([
                        html.Div([
                                buttongroupcontrol.buttonhome,
                                buttongroupcontrol.buttonmowall,
                                buttongroupcontrol.buttonzoneselect,
                                buttongroupcontrol.buttongoto,
                                buttongroupcontrol.buttonmowsettings,
                                buttongroupcontrol.buttoncancel,
                                ], className='text-center'),    
                    ]),
                    dbc.Row([
                        dbc.Col([buttongroupcontrol.buttongo], class_name='d-grid col-md4'),
                        dbc.Col([buttongroupcontrol.buttonstop], class_name='d-grid col-md4'),
                    ]),
                    modalmowsettings.mowsettings,
                    # dbc.Row([
                    #     html.Div(['Show'], className='margin-5px'),
                    #     dbc.Col([html.Div([dropdownmaplinetype.dropdown], className='dropdown-container')])
                    # ]),
                ], xs=12, sm=6, lg=6),
                dbc.Col([
                html.Div([
                    html.Div(id=ids.STATEHIDDEN, style={'display': 'none'}),
                    html.Div(id=ids.STATEHIDDEN2), #style={'display': 'none'}),
                    html.Div(id=ids.STATEHIDDEN3, style={'display': 'none'}),
                    #dbc.Row(html.Div(id=ids.MAPDATABLOCK, style={'marginTop':20}))    
                    ])
                ], xs=12, sm=6, lg=6)
            ]),

    ])

layout = update_layout()