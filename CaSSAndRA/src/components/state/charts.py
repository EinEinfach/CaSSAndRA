from dash import html, dcc, Input, Output, State, callback, ctx, Patch
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from .. import ids
from ... backend.data import roverdata
from ... backend.data.chartsdata import chartsdata

daterange = dcc.DatePickerRange(id=ids.CHARTSDATERANGE,
                end_date=datetime.now().date(),
                display_format='YYYY-MM-DD',
                start_date=datetime.now().date(),
                max_date_allowed=roverdata.state.iloc[-1]['timestamp'],
                min_date_allowed=roverdata.state.iloc[0]['timestamp'],
                stay_open_on_select=False,
                minimum_nights=0,
                updatemode='bothdates',
                style={"text-align":"center", "margin-bottom":"0.5rem"},
                className="dbc"
)
timerange = dcc.RangeSlider(id=ids.CHARTSTIMERANGE, marks=None, className="chart-slider dbc")

voltagecurrent = go.Figure()
voltagecurrent.update_layout(
                font=dict(size=7),
                plot_bgcolor='rgba(255, 255, 255, 0.0)',
                yaxis=dict(
                #    title='voltage',
                   gridcolor = 'rgba(200, 200, 200, 0.25)', 
                   showgrid=True,
                   zeroline=False,
                   tickfont=dict(size=7),
                ),
                yaxis2=dict(
                    # title='current',
                    side='right',
                    overlaying='y',
                    zeroline=False,
                    tickfont=dict(size=7),
                    showgrid=False,
                ),
               xaxis=dict(
                    gridcolor = 'rgba(200, 200, 200, 0.25)', 
                    showticklabels=True,
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(size=7),
               ),
               margin=dict(b=0, l=0, r=0, t=0),
               showlegend=False,
               hovermode='x unified',
               dragmode='pan',
    )

satellites = go.Figure()
satellites.update_layout(
                font=dict(size=7),
                plot_bgcolor='rgba(255, 255, 255, 0.0)',
                margin=dict(b=0, l=0, r=0, t=0),
                showlegend=False,
                dragmode='pan',
                hovermode='x unified',
                barmode='overlay',
                yaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False,
                ),
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                ),
    )

fixfloatinvalidpie = go.Figure()
fixfloatinvalidpie.update_layout(
                    font=dict(size=8),
                    plot_bgcolor='rgba(255, 255, 255, 0.0)',
                    margin=dict(b=0, l=0, r=0, t=0),
                    uniformtext_minsize=6, 
                    uniformtext_mode='hide',
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False,
                    ),
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                    ),
    )
                    
chargeidlemowpie = go.Figure()
chargeidlemowpie.update_layout(
                    font=dict(size=8),
                    plot_bgcolor='rgba(255, 255, 255, 0.0)',
                    margin=dict(b=0, l=0, r=0, t=0),
                    uniformtext_minsize=6, 
                    uniformtext_mode='hide',
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False,
                    ),
                    xaxis=dict(
                        showgrid=False,
                        zeroline=False,
                    ),
    )

lateralerror = go.Figure()
lateralerror.update_layout(
                font=dict(size=7),
                plot_bgcolor='rgba(255, 255, 255, 0.0)',
                margin=dict(b=0, l=0, r=0, t=0),
                showlegend=False,
                hovermode='x unified',
                dragmode='pan',
                xaxis=dict(
                    range=[-0.3, 0.3],
                    showgrid=False,
                    zeroline=False,
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                ),
    )

chartcontainer = [
    # Date
    dbc.Row([
        daterange,
        timerange,
    ],
    class_name="chart-row chart-item"),
    # Battery
    dbc.Row([ 
        dbc.Label("Battery", class_name="chart-label"),
        dcc.Graph(
            id=ids.CHARTVOLTAGECURRENT, 
            figure=voltagecurrent,
            config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': False},
            style={'height': '15vh'},
        ),
    ],
    class_name="chart-row chart-item"),   
    #Saterllites and lateral error
    dbc.Row([
        dbc.Col([
            dbc.Label("Satellites", class_name="chart-label"),
            dcc.Graph(
                id=ids.CHARTSATELLITES, 
                figure=satellites,
                config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': False},
                style={'height': '10vh'},
            ),
        ],
        style={"margin-right":"0.5rem"},
        class_name="chart-row chart-item"),
        dbc.Col([
            dbc.Label("Lateral Error", class_name="chart-label"),
            dcc.Graph(
                id=ids.CHARTLATERRORHIST, 
                figure=lateralerror,
                config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': False},
                style={'height': '10vh'},
            ),
        ],
        style={"margin-left":"0.5rem"},
        class_name="chart-row chart-item"),
    ],
    class_name="chart-row"),
    #Gps and state ratios
    dbc.Row([
        dbc.Col([
            dbc.Label("GPS Solution Ratio", class_name="chart-label"),
            dcc.Graph(
                    id=ids.CHARTFIXFLOATINVALIDPIE, 
                    figure=fixfloatinvalidpie,
                    config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': False},
                    style={'height': '10vh'},
            ),
        ],
        class_name="chart-item-separator"),
        dbc.Col([
            dbc.Label("State Ratio", class_name="chart-label"),
            dcc.Graph(
                    id=ids.CHARTCHARGEIDLEMOWPIE, 
                    figure=chargeidlemowpie,
                    config={'displaylogo': False, 'scrollZoom': True, 'displayModeBar': False},
                    style={'height': '10vh'},
            ),
        ]),
    ],
    class_name="chart-row chart-item"),
]


@callback(Output(ids.CHARTVOLTAGECURRENT, 'figure'),
          Output(ids.CHARTSATELLITES, 'figure'),
          Output(ids.CHARTFIXFLOATINVALIDPIE, 'figure'),
          Output(ids.CHARTCHARGEIDLEMOWPIE, 'figure'),
          Output(ids.CHARTLATERRORHIST, 'figure'),
          Output(ids.CHARTSTIMERANGE, 'value'),
          Output(ids.CHARTSTIMERANGE, 'min'),
          Output(ids.CHARTSTIMERANGE, 'max'),
          Output(ids.CHARTSDATERANGE, 'max_date_allowed'),
          Output(ids.CHARTSDATERANGE, 'min_date_allowed'),
          Output(ids.CHARTSINTERVAL, 'disabled'),
        [
            Input(ids.CHARTSINTERVAL, 'n_intervals'),
            Input(ids.URLUPDATE, 'pathname'),
            Input(ids.CHARTSDATERANGE, 'start_date'),
            Input(ids.CHARTSDATERANGE, 'end_date'),
            Input(ids.CHARTSTIMERANGE, 'value'),
            State(ids.CHARTSDATERANGE, 'start_date'),
            State(ids.CHARTSDATERANGE, 'end_date'),
            State(ids.CHARTSTIMERANGE, 'value'),
            State(ids.CHARTSINTERVAL, 'disabled'),
        ])
def update_charts(n_intervals: int,
                  calledpage: str,
                  start_date: str,
                  end_date: str,
                  timerange: list,
                  start_date_state: str,
                  end_date_state: str,
                  timerange_state: list,
                  interval_disabled: bool,
                  ) -> list:
    context = ctx.triggered_id
    max_date_allowed=roverdata.state.iloc[-1]['timestamp']
    min_date_allowed=roverdata.state.iloc[0]['timestamp']
    if start_date_state == None or end_date_state == None:
        start_date_state = str(datetime.now().date())
        end_date_state = str(datetime.now().date())
    end_date_state = end_date_state + ' 23:59:59.0'

    state_filtered = roverdata.state[(roverdata.state['timestamp'] > start_date_state)&(roverdata.state['timestamp'] <= end_date_state)]
    state_filtered = state_filtered.reset_index(drop=True)
    calced_from_stats_filtered = roverdata.calced_from_stats[(roverdata.calced_from_stats['timestamp'] > start_date_state)&(roverdata.calced_from_stats['timestamp'] <= end_date_state)]
    calced_from_stats_filtered = calced_from_stats_filtered.reset_index(drop=True)
    if timerange_state == None or context == ids.CHARTSDATERANGE:
        timerange_state = []
        timerange_state.append(state_filtered.index.min())
        timerange_state.append(state_filtered.index.max())
    if not interval_disabled and not state_filtered.empty:
        timerange_delta = timerange_state[1]-timerange_state[0]
        timerange_state[1] = state_filtered.index.max()
        timerange_state[0] = max(0, timerange_state[1]-timerange_delta)
    state_filtered = state_filtered.loc[timerange_state[0]:timerange_state[1]]
    state_filtered_mow = state_filtered[state_filtered['job'] == 1]
    #calc stats time range from state time range
    if not state_filtered.empty:
        calced_from_stats_filtered = calced_from_stats_filtered[(calced_from_stats_filtered['timestamp'] >= state_filtered.iloc[0]['timestamp'])&
                                                                (calced_from_stats_filtered['timestamp'] <= state_filtered.iloc[-1]['timestamp'])]

    traces = []
    traces2 = []
    traces3 = []
    traces4 = []
    traces5 = []
    #Battery plot
    traces.append(go.Scatter(x=state_filtered['timestamp'],
                             y=state_filtered['battery_voltage'],
                             name='voltage', 
                             mode='lines',
                             yaxis='y',
                             line=dict(color='rgba(70, 145, 219, 0.9)'),
                             line_shape='spline',
                )
    )
    traces.append(go.Scatter(x=state_filtered['timestamp'], 
                             y=state_filtered['amps'],
                             name='current', 
                             mode='lines',
                             yaxis='y2',
                             line=dict(color='rgba(217, 139, 49, 0.9)'),
                             fillcolor="rgba(217, 139, 49, 0.25)",
                             fill='tozeroy',
                             line_shape='spline',
                )
    )
    #Satellites plot
    traces2.append(go.Histogram(x=state_filtered_mow['position_visible_satellites'],
                             name='visible', 
                             opacity=0.7
                )
    )
    traces2.append(go.Histogram(x=state_filtered_mow['position_visible_satellites_dgps'],
                             name='dgps', 
                             opacity=0.7
                )
    )
    #Pie chart fix, float, invalid duration
    duration_fix = calced_from_stats_filtered['duration_mow_fix'].sum()
    duration_float = calced_from_stats_filtered['duration_mow_float'].sum()
    duration_invalid = calced_from_stats_filtered['duration_mow_invalid'].sum()
    traces3.append(go.Pie(
                    values=[duration_fix, duration_float, duration_invalid], 
                    labels=['Fix', 'Float', 'Invalid'], 
                    marker=dict(colors=['rgba(90, 185, 26, 0.75)', 'rgba(254, 166, 7, 0.75)', 'rgba(225, 46, 46, 0.75)'], line=dict(color='rgba(255, 255, 255, 1.0)', width=1)),
                    showlegend=False,
                    textposition='inside',
                    textinfo='percent+label',
                    hoverinfo='label+percent',
                    hole=0.4,
                    # textfont_size=9,
                )
            )
    #Pie chart charge, idle, mow ratio
    duration_charge = calced_from_stats_filtered['duration_charge'].sum()
    duration_idle = calced_from_stats_filtered['duration_idle'].sum()
    duration_mow = calced_from_stats_filtered['duration_mow'].sum()
    traces4.append(go.Pie(
                    values=[duration_mow, duration_idle, duration_charge], 
                    labels=['Mow', 'Idle', 'Charge'], 
                    marker=dict(colors=['rgba(15, 135, 15, 0.75)', 'rgba(255, 165, 0, 0.75)', 'rgba(118, 153, 241, 0.75)'], line=dict(color='rgba(255, 255, 255, 1.0)', width=1)),
                    showlegend=False,
                    textposition='inside',
                    textinfo='percent+label',
                    hoverinfo='label+percent',
                    hole=0.4,
                )
            )
    #Histogramm lateral error
    traces5.append(go.Histogram(
                    x=state_filtered_mow[state_filtered_mow['position_solution']==2]['lateral_error'],
                    xbins=dict(
                        start=-0.5,
                        end=0.5,
                        size=0.01
                    ),
                    opacity=0.7
                )
            )
    #activate interval update if zoomed in
    if len(state_filtered) <= 1000:
        interval_disabled = False
    else:
        interval_disabled = True   
    fig = Patch()
    fig2 = Patch()
    fig3 = Patch()
    fig4 = Patch()
    fig5 = Patch()
    fig.data = traces
    fig2.data = traces2
    fig3.data = traces3
    fig4.data = traces4
    fig5.data = traces5
    return fig, fig2, fig3, fig4, fig5, timerange_state, state_filtered.index.min(), state_filtered.index.max(), max_date_allowed, min_date_allowed, interval_disabled

@callback(Output(ids.CHARTSDATERANGE, 'start_date'),
           Output(ids.CHARTSDATERANGE, 'end_date'),
           [Input(ids.URLUPDATE, 'pathname'),
            ])
def update_date(calledpage: str) -> list:
    return datetime.now().date(), datetime.now().date()