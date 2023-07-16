# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

#local imports
from src.components import ids, modaltaskmowsettings
from src.components.tasks import map, buttongroupcontrol, modal, choosetask

dash.register_page(
    __name__,
    path='/taskplanner',
    title='Taskplanner'
)

def update_layout() -> html.Div:
       return dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.Div(className='loader-wrapper', 
                                children=[
                                    dbc.Spinner(delay_show=1000, 
                                                children=html.Div([
                                                            dcc.Graph(id=ids.TASKMAP, config={'displaylogo': False, 'scrollZoom': True})
                                                            ], className='map-graph'
                                                        )
                                    )
                                ]
                        ),
                        html.Div([
                            buttongroupcontrol.buttonplanmowall,
                            buttongroupcontrol.buttonmowsettings,
                            buttongroupcontrol.buttonconfirmselection,
                            buttongroupcontrol.buttoncancel,
                            ], className='text-center'),
                    ], xs=12, sm=6, lg=6),
                    dbc.Col([   
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    choosetask.choosetask,
                                ], className='text-center'),
                            ]),
                        ], justify='evenly'),
                    ], xs=12, sm=6, lg=6),
                ]),
                modaltaskmowsettings.mowsettings,     
                modal.savecurrenttask,  
                modal.removecurrenttask,       
            ], fluid=True)
            

layout = update_layout()