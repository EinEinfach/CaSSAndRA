from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import dash_daq as daq

def get_mow_settings_template(idInputPattern, cfgPattern,
                              idInputMowOffset, cfgWidth,
                              idMowAngle, cfgAngle,
                              idDistanceBorder, cfgDistanceBorder,
                              idMowBorder, cfgMowBorder,
                              idMowArea, cfgMowArea,
                              idMowExclusion, cfgMowExclusion,
                              idMowBorderCCW, cfgMowBorderCCW):
    return dbc.ListGroup([
            dbc.ListGroupItem(
                # Line Settings
                dbc.Row([
                    dbc.Col([  
                        html.P(['Pattern'], className='mb-0'),
                        dbc.Select(
                            id=idInputPattern, 
                            options=[
                                {'label': 'lines', 'value': 'lines'},
                                {'label': 'squares', 'value': 'squares'},
                                {'label': 'rings', 'value': 'rings'},
                            ],
                            value=cfgPattern, style={"padding-top" : "0.17rem", "padding-bottom" : "0.17rem"}
                        ),
                    ]),
                    dbc.Col([  
                        html.P(['Width'], className='mb-0'),
                        dbc.Input(id=idInputMowOffset, 
                                value=cfgWidth,
                                type='number', 
                                min=0, 
                                max=1, 
                                step=0.01, 
                                size='sm'
                        ), 
                    ]),
                    dbc.Col([  
                        html.P(['Angle'], className='mb-0'),
                        dbc.Input(id=idMowAngle, 
                                value=cfgAngle, 
                                type='number', 
                                min=0, 
                                max=359, 
                                step=1, 
                                size='sm'
                        ),
                    ]),
                ], style={"padding-bottom" : "0.75rem"}),
            style={"padding-left" : "0.75rem", "padding-right" : "0.75erem", "padding-bottom" : "0.5rem", "padding-top" : "1.0rem"}),
            
            dbc.ListGroupItem(
                # Perimeter Settings
                dbc.Row([
                    dbc.Col([  
                        html.P(['Distance to border'], className='mb-0'),
                        dbc.Input(id=idDistanceBorder, 
                                value=cfgDistanceBorder, 
                                type='number', 
                                min=0, 
                                max=5, 
                                step=1, 
                                size='sm'
                        ),
                    ]),
                    dbc.Col([  
                        html.P(['Border rounds'], className='mb-0'),
                        dbc.Input(id=idMowBorder, 
                                value=cfgMowBorder, 
                                type='number', 
                                min=0, 
                                max=6, 
                                step=1, 
                                size='sm'
                        ),
                    ]),
                ], style={"padding-bottom" : "0.75rem"}),
            style={"padding-left" : "0.75rem", "padding-right" : "0.75erem", "padding-bottom" : "0.5rem", "padding-top" : "1.0rem"} ),
            
            dbc.ListGroupItem([
                # 
                dbc.Row([
                    dbc.Col([ 
                        html.P(['Mow area'], className='mb-0'),
                    ], style={"flex-grow" : "2"}),
                    dbc.Col([ 
                        daq.BooleanSwitch(
                            id=idMowArea,
                            on= cfgMowArea,
                            style={"float" : "right"},
                            color="#afe0d2",
                        ),
                    ], style={"flex-shrink" : "2"}),
                ], style={"padding-bottom" : "0.75rem"}),
                
                dbc.Row([
                    dbc.Col([ 
                        html.P(['Mow exclusion border'], className='mb-0'),
                    ], style={"flex-grow" : "2"}),
                    dbc.Col([ 
                        daq.BooleanSwitch(
                            id=idMowExclusion,
                            on= cfgMowExclusion,
                            style={"float" : "right"},
                            color="#afe0d2",
                        ),
                    ], style={"flex-shrink" : "2"}),
                ], style={"padding-bottom" : "0.75rem"}),

                dbc.Row([
                    dbc.Col([ 
                        html.P(['Mow border CCW'], className='mb-0'),
                    ], style={"flex-grow" : "2"}),
                    dbc.Col([ 			
                        daq.BooleanSwitch(
                            id=idMowBorderCCW,
                            on= cfgMowBorderCCW,
                            style={"float" : "right"},
                            color="#afe0d2",
                        ),															 
                    ], style={"flex-shrink" : "2"}),
                ], style={"padding-bottom" : "0.75rem"}),
            
            ],
            style={"padding-left" : "0.75rem", "padding-right" : "0.75erem", "padding-bottom" : "0.5rem", "padding-top" : "1.0rem"} ),
        ],
        flush=True,
    )