# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

#local imports
from src.components import ids
from src.components.mapping import map, uploadsunray, modal, buttons, buttongroupcontrol, chooseperimeter

dash.register_page(
    __name__,
    path='/mapping',
    title='Mapping'
)

def update_layout() -> html.Div:
    return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div(className='loader-wrapper', 
                             children=[
                                 dbc.Spinner(delay_show=1000, 
                                             children=html.Div([
                                                        dcc.Graph(id=ids.MAPPINGMAP, figure=map.mappingmap, config= {'displaylogo': False, 
                                                                                                                     'scrollZoom': True, 
                                                                                                                     #'modeBarButtonsToAdd':['eraseshape']
                                                                                                                     })
                                                        ], className='map-graph'
                                                    )
                                )
                            ]
                    ),
                    dbc.Row([
                        html.Div([
                            buttongroupcontrol.buttonhomeadd,
                            buttongroupcontrol.buttonaddnewpoint,
                            buttongroupcontrol.buttondeletelastpoint,
                            buttongroupcontrol.buttonmovepoints,
                            buttongroupcontrol.buttoncancelmapaction,
                            ], className='text-center'),   
                     
                    ]),
                    dbc.Row([
                        dbc.Col([buttongroupcontrol.buttonperimeteradd], class_name='d-grid col-md4'),
                        dbc.Col([buttongroupcontrol.buttonperimeterdiff], class_name='d-grid col-md4'),
                    ]),
                ], xs=12, sm=6, lg=6),
                dbc.Col([
                    html.Div([
                        chooseperimeter.chooseperimeter,
                        ], className='text-center'
                    ),
                    html.Div([
                        uploadsunray.uploadsunray,
                        ], className='text-center'),
                ], xs=12, sm=6, lg=6),
                modal.sunrayimportstatus,
                modal.overwriteperimter,
                modal.newperimeter,
                modal.selectperimeter,
                modal.copyperimeter,
                modal.removeperimeter,
                modal.finishmapping,
                modal.nofixsolution,
                html.Div(id=ids.MAPPINGHIDDEN, style={'display': 'none'}),
                ])
            ], fluid=True)

layout = update_layout()
