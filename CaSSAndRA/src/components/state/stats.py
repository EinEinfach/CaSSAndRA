from dash import html, dcc, Input, Output, State, callback, ctx, Patch
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from .. import ids
from ... backend.data import roverdata
from . charts import daterange

from icecream import ic

statscontainer = [
                    dbc.Row([daterange]),
                    dbc.Row(id=ids.STATSDATA) 
                ]

@callback(Output(ids.STATSDATA, 'children'),
          [
            #Input(ids.CHARTSINTERVAL, 'n_intervals'),
            Input(ids.URLUPDATE, 'pathname'),
            Input(ids.CHARTSDATERANGE, 'start_date'),
            Input(ids.CHARTSTIMERANGE, 'end_date'),
            State(ids.CHARTSDATERANGE, 'start_date'),
            State(ids.CHARTSDATERANGE, 'end_date'),
        ])
def update_stats(#n_intervals: int,
                  calledpage: str,
                  start_date: str,
                  end_date: str,
                  start_date_stats: str,
                  end_date_stats: str,
                  ) -> dbc.Container:
    context = ctx.triggered_id
    ic(context)
    if start_date_stats == None or end_date_stats == None:
        start_date_stats = str(datetime.now().date())
        end_date_stats = str(datetime.now().date())
    end_date_stats = end_date_stats + ' 23:59:59.0'

    stats = roverdata.stats
    stats_filtered = stats[(stats['timestamp'] > start_date_stats)&(stats['timestamp'] <= end_date_stats)]
    stats_filtered = stats_filtered.reset_index(drop=True)
    calced_stats = roverdata.calced_from_stats
    calced_stats_filtered = calced_stats[(calced_stats['timestamp'] > start_date_stats)&(calced_stats['timestamp'] <= end_date_stats)]
    calced_stats_filtered = calced_stats_filtered.reset_index(drop=True)
    
    counter_float_recoveries_range = int(calced_stats_filtered['counter_float_recoveries'].sum())
    mow_traveled_range = round(calced_stats_filtered['distance_mow_traveled'].sum()/1000, 2)
    time_max_dgps_age_range = round(stats_filtered['time_max_dpgs_age'].max(), 2)
    counter_imu_triggered_range = int(calced_stats_filtered['counter_imu_triggered'].sum())
    counter_gps_chk_sum_errors_range = int(calced_stats_filtered['counter_gps_chk_sum_errors'].sum())
    counter_dgps_chk_sum_errors_range = int(calced_stats_filtered['counter_dgps_chk_sum_errors'].sum())
    time_max_cycle_range = round(stats_filtered['time_max_cycle'].max(), 2)
    counter_invalid_recoveries_range = int(calced_stats_filtered['counter_invalid_recoveries'].sum())
    counter_obstacles_range = int(calced_stats_filtered['counter_obstacles'].sum())
    counter_gps_jumps_range = int(calced_stats_filtered['counter_gps_jumps'].sum())                
    counter_sonar_triggered_range = int(calced_stats_filtered['counter_sonar_triggered'].sum())                   
    counter_bumper_triggered_range = int(calced_stats_filtered['counter_bumper_triggered'].sum())                        
    counter_gps_motion_timeout_range = int(calced_stats_filtered['counter_gps_motion_timeout'].sum())                      
    
    stats = html.Div(
            [
                html.P('Common'),
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('distance'),
                                html.Small(f'{mow_traveled_range}km')
                            ])
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('obstacles'),
                                html.Small(counter_obstacles_range)
                            ])
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('cycle max time'),
                                html.Small(time_max_cycle_range)
                            ])
                        ]),
                    ],
                    horizontal=True,
                    className="mb-2",
                ),
                html.P('Obstacles'),
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem([
                                html.Div([
                                    html.P('bumper'),
                                    html.Small(counter_bumper_triggered_range)
                                ])
                            ]),
                            dbc.ListGroupItem([
                                html.Div([
                                    html.P('imu'),
                                    html.Small(counter_imu_triggered_range)
                                ])
                            ]),
                            dbc.ListGroupItem([
                                html.Div([
                                    html.P('gps'),
                                    html.Small(counter_gps_motion_timeout_range)
                                ])
                            ]),
                            dbc.ListGroupItem([
                                html.Div([
                                    html.P('sonar'),
                                    html.Small(counter_sonar_triggered_range)
                                ])
                            ]),
                        ],
                        horizontal=True,
                        className="mb-2",
                    ),
                html.P('Recoveries'),
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('invalid'),
                                html.Small(counter_invalid_recoveries_range)
                            ])
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('float'),
                                html.Small(counter_float_recoveries_range)
                            ])
                        ]),
                    ],
                    horizontal=True,
                    className="mb-2",
                ),
                html.P('GPS'),
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('jumps'),
                                html.Small(counter_gps_jumps_range)
                            ])
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('crc errors'),
                                html.Small(f'{counter_gps_chk_sum_errors_range} gps/ {counter_dgps_chk_sum_errors_range} dgps')
                            ])
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.P('max age'),
                                html.Small(f'{time_max_dgps_age_range}s')
                            ])
                        ]),
                    ],
                    horizontal=True,
                    className="mb-2",
                ),
            ]
        )
    
    return stats

