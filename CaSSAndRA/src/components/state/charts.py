from dash import html, dcc, Input, Output, State, callback, ctx, Patch
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from .. import ids
from ... backend.data import roverdata

daterange = dcc.DatePickerRange(id=ids.CHARTSDATERANGE,
                end_date=datetime.now().date(),
                display_format='YYYY-MM-DD',
                start_date=datetime.now().date(),
                max_date_allowed=datetime.now().date(),
                min_date_allowed=roverdata.state.iloc[0]['timestamp'],
                stay_open_on_select=False,
                minimum_nights=0,
)
timerange = dcc.RangeSlider(id=ids.CHARTSTIMERANGE, marks=None)

voltagecurrent = go.Figure()
voltagecurrent.update_layout(
                title=dict(
                    text='battery',
                    x=0.5,
                    y=1,
                    xanchor='center',
                    yanchor='auto'
                ),
                font=dict(size=7),
                plot_bgcolor='white',
                yaxis=dict(
                   title='voltage',
                   gridcolor = '#eeeeee', 
                   showgrid=True,
                   zeroline=False,
                   tickfont=dict(size=7),
                ),
                yaxis2=dict(
                    title='current',
                    side='right',
                    overlaying='y',
                    tickfont=dict(size=7),
                ),
               xaxis=dict(
                    gridcolor = '#eeeeee', 
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
                title=dict(
                    text='satellites',
                    x=0.5,
                    y=1,
                    xanchor='center',
                    yanchor='auto'
                ),
                font=dict(size=7),
                plot_bgcolor='white',
                yaxis=dict(
                    title='amount',
                    gridcolor = '#eeeeee', 
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(size=7),
                ),
               xaxis=dict(
                    gridcolor = '#eeeeee', 
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

fixfloatinvalidpie = go.Figure()
fixfloatinvalidpie.update_layout(
                    title=dict(
                        text='solution ratio',
                        x=0.5,
                        y=1,
                        xanchor='center',
                        yanchor='auto'
                    ),
                    font=dict(size=7),
                    plot_bgcolor='white',
                    margin=dict(b=0, l=0, r=0, t=0),
                    uniformtext_minsize=6, 
                    uniformtext_mode='hide',
    )
                    
chargeidlemowpie = go.Figure()
chargeidlemowpie.update_layout(
                    title=dict(
                        text='state ratio',
                        x=0.5,
                        y=1,
                        xanchor='center',
                        yanchor='auto'
                    ),
                    font=dict(size=7),
                    plot_bgcolor='white',
                    margin=dict(b=0, l=0, r=0, t=0),
                    uniformtext_minsize=6, 
                    uniformtext_mode='hide',
    )

lateralerror = go.Figure()
lateralerror.update_layout(
                title=dict(
                    text='lateral error',
                    x=0.5,
                    y=1,
                    xanchor='center',
                    yanchor='auto', 
                ),
                font=dict(size=7),
                plot_bgcolor='white',
                margin=dict(b=0, l=0, r=0, t=0),
                showlegend=False,
                hovermode='x unified',
                dragmode='pan',
    )

@callback(Output(ids.CHARTVOLTAGECURRENT, 'figure'),
          Output(ids.CHARTSATELLITES, 'figure'),
          Output(ids.CHARTFIXFLOATINVALIDPIE, 'figure'),
          Output(ids.CHARTCHARGEIDLEMOWPIE, 'figure'),
          Output(ids.CHARTLATERRORHIST, 'figure'),
          Output(ids.CHARTSTIMERANGE, 'value'),
          Output(ids.CHARTSTIMERANGE, 'min'),
          Output(ids.CHARTSTIMERANGE, 'max'),
        [
            #Input(ids.STATEMAPINTERVAL, 'n_intervals'),
            Input(ids.URLUPDATE, 'pathname'),
            Input(ids.CHARTSDATERANGE, 'start_date'),
            Input(ids.CHARTSTIMERANGE, 'end_date'),
            Input(ids.CHARTSTIMERANGE, 'value'),
            State(ids.CHARTSDATERANGE, 'start_date'),
            State(ids.CHARTSDATERANGE, 'end_date'),
            State(ids.CHARTSTIMERANGE, 'value'),
        ])
def update_charts(#n_intervals: int,
                  calledpage: str,
                  start_date: str,
                  end_date: str,
                  timerange: list,
                  start_date_state: str,
                  end_date_state: str,
                  timerange_state: list,
                  ) -> Patch():
    context = ctx.triggered_id
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
    state_filtered = state_filtered.loc[timerange_state[0]:timerange_state[1]]
    state_filtered_mow = state_filtered[state_filtered['job'] == 1]
    #calc stats time range from state time range
    calced_from_stats_filtered = calced_from_stats_filtered[(calced_from_stats_filtered['timestamp'] >= state_filtered.iloc[1]['timestamp'])&
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
                             yaxis='y'
                )
    )
    traces.append(go.Scatter(x=state_filtered['timestamp'], 
                             y=state_filtered['amps'],
                             name='current', 
                             mode='lines',
                             yaxis='y2'
                )
    )
    #Satellites plot
    traces2.append(go.Scatter(x=state_filtered['timestamp'],
                             y=state_filtered['position_visible_satellites'],
                             name='visible', 
                             mode='lines',
                )
    )
    traces2.append(go.Scatter(x=state_filtered['timestamp'], 
                             y=state_filtered['position_visible_satellites_dgps'],
                             name='dgps', 
                             mode='lines',
                )
    )
    #Pie chart fix, float, invalid duration
    duration_fix = calced_from_stats_filtered['duration_mow_fix'].sum()
    duration_float = calced_from_stats_filtered['duration_mow_float'].sum()
    duration_invalid = calced_from_stats_filtered['duration_mow_invalid'].sum()
    traces3.append(go.Pie(
                    values=[duration_fix, duration_float, duration_invalid], 
                    labels=['fix', 'float', 'invalid'], 
                    marker=dict(colors=['green', 'orange', 'red']), 
                    showlegend=False,
                    textposition='inside',
                    hoverinfo='label+percent',
                )
            )
    #Pie chart charge, idle, mow ratio
    duration_charge = calced_from_stats_filtered['duration_charge'].sum()
    duration_idle = calced_from_stats_filtered['duration_idle'].sum()
    duration_mow = calced_from_stats_filtered['duration_mow'].sum()
    traces4.append(go.Pie(
                    values=[duration_mow, duration_idle, duration_charge], 
                    labels=['mow', 'idle', 'charge'], 
                    marker=dict(colors=['green', 'orange', 'red']),
                    showlegend=False,
                    textposition='inside',
                    hoverinfo='label+percent',
                )
            )
    #Histogramm lateral error
    traces5.append(go.Histogram(
                    x=state_filtered_mow[state_filtered_mow['position_solution']==2]['lateral_error'],
                    xbins=dict(
                        start=-0.5,
                        end=0.5,
                        size=0.01
                    )
                    
                )
            )
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
    return fig, fig2, fig3, fig4, fig5, timerange_state, state_filtered.index.min(), state_filtered.index.max()