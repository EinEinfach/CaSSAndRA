from dash import html, dcc, Input, Output, State, callback, ctx, Patch
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from .. import ids
from ... backend.data import roverdata
from . charts import daterange, timerange

from icecream import ic

statscontainer = [
    dbc.Row([
        daterange,
        timerange,
    ],
    class_name="chart-row chart-item"),
]

stats = [
    dbc.Row([
        dbc.Label('Common', style={"margin-top":"0.5rem", "padding":"0", "margin-left":"1.5rem", "margin-bottom":"0.25rem"}),
        dbc.ListGroup(
            [
                dbc.ListGroupItem([
                        html.P('distance', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="mow_traveled_range")
                ]),
                dbc.ListGroupItem([
                        html.P('obstacles', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_obstacles_range")
                ]),
                dbc.ListGroupItem([
                        html.P('cycle time', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="time_max_cycle_range")
                ]),
            ],
            horizontal=True,
            className="mb-2",
            style={"justify-content":"", "margin-left":"1rem", "margin-right":"1rem", "flex-shrink":"1"},
        ),
        dbc.Label('Obstacles', style={"margin-top":"0.5rem", "padding":"0", "margin-left":"1.5rem", "margin-bottom":"0.25rem"}),
        dbc.ListGroup(
            [
                dbc.ListGroupItem([
                        html.P('bumper', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_bumper_triggered_range")
                ]),
                dbc.ListGroupItem([
                        html.P('imu', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_imu_triggered_range")
                ]),
                dbc.ListGroupItem([
                        html.P('gps', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_gps_motion_timeout_range")
                ]),
                dbc.ListGroupItem([
                        html.P('sonar', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_sonar_triggered_range")
                ]),
            ],
            horizontal=True,
            className="mb-2",
            style={"justify-content":"", "margin-left":"1rem", "margin-right":"1rem", "flex-shrink":"1"},
        ),
        dbc.Label('Recoveries', style={"margin-top":"0.5rem", "padding":"0", "margin-left":"1.5rem", "margin-bottom":"0.25rem"}),
        dbc.ListGroup(
            [
                dbc.ListGroupItem([
                        html.P('invalid', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_invalid_recoveries_range")
                ]),
                dbc.ListGroupItem([
                        html.P('float', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_float_recoveries_range")
                ]),
            ],
            horizontal=True,
            className="mb-2",
            style={"justify-content":"", "margin-left":"1rem", "margin-right":"1rem", "flex-shrink":"1"},
        ),
        dbc.Label('GPS', style={"margin-top":"0.5rem", "padding":"0", "margin-left":"1.5rem", "margin-bottom":"0.25rem"}),
        dbc.ListGroup(
            [
                dbc.ListGroupItem([
                        html.P('jumps', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_gps_jumps_range")
                ]),
                dbc.ListGroupItem([
                        html.P('crc errors', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="counter_gps_chk")
                ]),
                dbc.ListGroupItem([
                        html.P('max age', style={"margin-bottom":"0.25rem"}),
                        html.Small(id="time_max_dgps_age_range")
                ]),
            ],
            horizontal=True,
            className="mb-2",
            style={"justify-content":"", "margin-left":"1rem", "margin-right":"1rem", "flex-shrink":"1"},
        ),
    ],
    id=ids.STATSDATA,
    class_name="chart-row chart-item chart-stats"
    )
]

@callback(
    [
        # Output(ids.STATSDATA, 'children')
        Output("mow_traveled_range", 'children'),
        Output("counter_obstacles_range", 'children'),
        Output("time_max_cycle_range", 'children'),
        Output("counter_bumper_triggered_range", 'children'),
        Output("counter_imu_triggered_range", 'children'),
        Output("counter_gps_motion_timeout_range", 'children'),
        Output("counter_sonar_triggered_range", 'children'),
        Output("counter_invalid_recoveries_range", 'children'),
        Output("counter_float_recoveries_range", 'children'),
        Output("counter_gps_jumps_range", 'children'),
        Output("counter_gps_chk", 'children'),
        Output("time_max_dgps_age_range", 'children'),
    ],
    [
        #Input(ids.INTERVAL, 'n_intervals'),
        Input(ids.URLUPDATE, 'pathname'),
        Input(ids.CHARTSDATERANGE, 'start_date'),
        Input(ids.CHARTSTIMERANGE, 'end_date'),
        Input(ids.CHARTSTIMERANGE, 'value'),
        State(ids.CHARTSDATERANGE, 'start_date'),
        State(ids.CHARTSDATERANGE, 'end_date'),
        State(ids.CHARTSTIMERANGE, 'value'),
    ])
def update_stats(#n_intervals: int,
                  calledpage: str,
                  start_date: str,
                  end_date: str,
                  timerange: list,
                  start_date_stats: str,
                  end_date_stats: str,
                  timerange_state: list,
                  ) -> dbc.Container:
    context = ctx.triggered_id
    if start_date_stats == None or end_date_stats == None:
        start_date_stats = str(datetime.now().date())
        end_date_stats = str(datetime.now().date())
    end_date_stats = end_date_stats + ' 23:59:59.0'

    stats = roverdata.stats
    calced_stats = roverdata.calced_from_stats
    state_filtered = roverdata.state[(roverdata.state['timestamp'] > start_date_stats)&(roverdata.state['timestamp'] <= end_date_stats)]
    state_filtered = state_filtered.reset_index(drop=True)
    if timerange_state == None or context == ids.CHARTSDATERANGE:
        timerange_state = []
        timerange_state.append(state_filtered.index.min())
        timerange_state.append(state_filtered.index.max())
    state_filtered = state_filtered.loc[timerange_state[0]:timerange_state[1]]
    stats_filtered = stats[(stats['timestamp'] > start_date_stats)&(stats['timestamp'] <= end_date_stats)]
    stats_filtered = stats_filtered.reset_index(drop=True)
    calced_stats_filtered = calced_stats[(calced_stats['timestamp'] > start_date_stats)&(calced_stats['timestamp'] <= end_date_stats)]
    calced_stats_filtered = calced_stats_filtered.reset_index(drop=True)

    #calc stats time range from state time range
    if not state_filtered.empty:
        calced_stats_filtered = calced_stats_filtered[(calced_stats_filtered['timestamp'] >= state_filtered.iloc[0]['timestamp'])&
                                                                (calced_stats_filtered['timestamp'] <= state_filtered.iloc[-1]['timestamp'])]
        stats_filtered = stats_filtered[(stats_filtered['timestamp'] >= state_filtered.iloc[0]['timestamp'])&
                                                                (stats_filtered['timestamp'] <= state_filtered.iloc[-1]['timestamp'])]
    
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
    
    return f'{mow_traveled_range} km', counter_obstacles_range, f'{time_max_cycle_range} s', counter_bumper_triggered_range, counter_imu_triggered_range, counter_gps_motion_timeout_range, counter_sonar_triggered_range, \
        counter_invalid_recoveries_range, counter_float_recoveries_range, counter_gps_jumps_range, f'{counter_gps_chk_sum_errors_range} gps / {counter_dgps_chk_sum_errors_range} dgps',f'{time_max_dgps_age_range} s'
