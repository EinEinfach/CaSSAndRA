from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids

from src.backend.data.cfgdata import schedulecfg
from src.backend.data.scheduledata import schedule_tasks

def get_day(name, dayid, taskid):
    return html.Div([
            html.Small(name),
            dcc.RangeSlider(id=dayid, 
                            min=0, 
                            max=24, 
                            value=[12, 12], 
                            step=0.5, 
                            marks={
                                0: '00:00', 
                                6: '06:00', 
                                9: '09:00',
                                12: '12:00',
                                15: '15:00', 
                                18: '18:00',
                                24: '24:00',
                            },
                            tooltip={'placement': 'top'},
                            className="dbc"
            ),
            dcc.Dropdown(className='m-1', 
                         multi=True,
                         id=taskid,
                )
            ], className="schedule-day")

switch = dbc.Switch(id=ids.SWITCHACTIVATESCHEDULE,
                        style={'float' : 'right'},
                    )

monday = get_day('Monday', ids.SCHEDULEMONDAY, ids.MONDAYTASK)
tuesday = get_day('Tuesday', ids.SCHEDULETUESDAY, ids.TUESDAYTASK)
wednesday = get_day('Wednesday', ids.SCHEDULEWEDNESDAY, ids.WEDNESDAYTASK)
thursday = get_day('Thursday', ids.SCHEDULETHURSDAY, ids.THURSDAYTASK)
friday = get_day('Friday', ids.SCHEDULEFRIDAY, ids.FRIDAYTASK)
saturday = get_day('Saturday', ids.SCHEDULESATURDAY, ids.SATURDAYTASK)
sunday = get_day('Sunday', ids.SCHEDULESUNDAY, ids.SUNDAYTASK)


@callback(Output(ids.SCHEDULEMONDAY, 'disabled'),
          Output(ids.MONDAYTASK, 'disabled'),
          Output(ids.SCHEDULETUESDAY, 'disabled'),
          Output(ids.TUESDAYTASK, 'disabled'),
          Output(ids.SCHEDULEWEDNESDAY, 'disabled'),
          Output(ids.WEDNESDAYTASK, 'disabled'),
          Output(ids.SCHEDULETHURSDAY, 'disabled'),
          Output(ids.THURSDAYTASK, 'disabled'),
          Output(ids.SCHEDULEFRIDAY, 'disabled'),
          Output(ids.FRIDAYTASK, 'disabled'),
          Output(ids.SCHEDULESATURDAY, 'disabled'),
          Output(ids.SATURDAYTASK, 'disabled'),
          Output(ids.SCHEDULESUNDAY, 'disabled'),
          Output(ids.SUNDAYTASK, 'disabled'),
          Output(ids.SWITCHACTIVATESCHEDULE, 'value'),
          [Input(ids.URLUPDATE, 'pathname'),
           Input(ids.SWITCHACTIVATESCHEDULE, 'value'),
           ])
def activate_schedule(calledpage: str,
                    sas_on: bool,
                      ) -> list:
    context = ctx.triggered_id
    return_value = []
    if context == ids.SWITCHACTIVATESCHEDULE and sas_on:
        schedulecfg.active = True
        schedulecfg.save_schedulecfg()
        return_value = [False] * 14
        return_value.append(True)
        return return_value
    elif context == ids.SWITCHACTIVATESCHEDULE and not sas_on:
        schedulecfg.active = False
        schedulecfg.save_schedulecfg()
        return_value = [True] * 14
        return_value.append(False)
        return return_value
    else:
        if schedulecfg.active:
            return_value = [False] * 14
            return_value.append(True)
            return return_value
        else:
            return_value = [True] * 14
            return_value.append(False)
            return return_value

@callback(Output(ids.SCHEDULEMONDAY, 'value'),
          Output(ids.SCHEDULETUESDAY, 'value'),
          Output(ids.SCHEDULEWEDNESDAY, 'value'),
          Output(ids.SCHEDULETHURSDAY, 'value'),
          Output(ids.SCHEDULEFRIDAY, 'value'),
          Output(ids.SCHEDULESATURDAY, 'value'),
          Output(ids.SCHEDULESUNDAY, 'value'),
          [Input(ids.URLUPDATE, 'pathname'),
           Input(ids.SCHEDULEMONDAY, 'value'), 
           Input(ids.SCHEDULETUESDAY, 'value'), 
           Input(ids.SCHEDULEWEDNESDAY, 'value'), 
           Input(ids.SCHEDULETHURSDAY, 'value'), 
           Input(ids.SCHEDULEFRIDAY, 'value'), 
           Input(ids.SCHEDULESATURDAY, 'value'), 
           Input(ids.SCHEDULESUNDAY, 'value'), 
           State(ids.SCHEDULEMONDAY, 'value'),
           State(ids.SCHEDULETUESDAY, 'value'),
           State(ids.SCHEDULEWEDNESDAY, 'value'),
           State(ids.SCHEDULETHURSDAY, 'value'),
           State(ids.SCHEDULEFRIDAY, 'value'),
           State(ids.SCHEDULESATURDAY, 'value'),
           State(ids.SCHEDULESUNDAY, 'value'),
           ])
def update_schedule_time(calledpage: str,
                        schmon: list,
                        schtue: list,
                        schwed: list,
                        schthu: list,
                        schfr: list,
                        schsat: list,
                        schsun: list,
                        schmon_state: list,
                        schtue_state: list,
                        schwed_state: list,
                        schthu_state: list,
                        schfr_state: list,
                        schsat_state: list,
                        schsun_state: list,
                        ) -> list:
    context = ctx.triggered_id
    if (context == ids.SCHEDULEMONDAY or context == ids.SCHEDULETUESDAY or context == ids.SCHEDULEWEDNESDAY or context == ids.SCHEDULETHURSDAY or 
        context == ids.SCHEDULEFRIDAY or context == ids.SCHEDULESATURDAY or context == ids.SCHEDULESUNDAY):
        schedulecfg.monday_time = schmon_state
        schedulecfg.tuesday_time = schtue_state
        schedulecfg.wednesday_time = schwed_state
        schedulecfg.thursday_time = schthu_state
        schedulecfg.friday_time = schfr_state
        schedulecfg.saturday_time = schsat_state
        schedulecfg.sunday_time = schsun_state
        schedulecfg.save_schedulecfg()
    return schedulecfg.monday_time, schedulecfg.tuesday_time, schedulecfg.wednesday_time, schedulecfg.thursday_time, schedulecfg.friday_time, schedulecfg.saturday_time, schedulecfg.sunday_time

@callback(Output(ids.MONDAYTASK, 'value'),
          Output(ids.TUESDAYTASK, 'value'),
          Output(ids.WEDNESDAYTASK, 'value'),
          Output(ids.THURSDAYTASK, 'value'),
          Output(ids.FRIDAYTASK, 'value'),
          Output(ids.SATURDAYTASK, 'value'),
          Output(ids.SUNDAYTASK, 'value'),
          [Input(ids.URLUPDATE, 'pathname'),
           Input(ids.DROPDOWNTASKSORDER, 'options'),
           Input(ids.MONDAYTASK, 'value'),
           Input(ids.TUESDAYTASK, 'value'),
           Input(ids.WEDNESDAYTASK, 'value'),
           Input(ids.THURSDAYTASK, 'value'),
           Input(ids.FRIDAYTASK, 'value'),
           Input(ids.SATURDAYTASK, 'value'),
           Input(ids.SUNDAYTASK, 'value'),
           State(ids.MONDAYTASK, 'value'),
           State(ids.TUESDAYTASK, 'value'),
           State(ids.WEDNESDAYTASK, 'value'),
           State(ids.THURSDAYTASK, 'value'),
           State(ids.FRIDAYTASK, 'value'),
           State(ids.SATURDAYTASK, 'value'),
           State(ids.SUNDAYTASK, 'value'),
           ])
def update_schedule_tasks(calledpage: str,
                          tasks: list,
                          monday_tasks: list,
                          tuesday_tasks: list,
                          wednesday_tasks: list,
                          thursday_tasks: list,
                          friday_tasks: list,
                          saturdas_tasks: list,
                          sunday_tasks: list,
                          monday_tasks_state: list,
                          tuesday_tasks_state: list,
                          wednesday_tasks_state: list,
                          thursday_tasks_state: list,
                          friday_tasks_state: list,
                          saturday_tasks_state: list,
                          sunday_tasks_state: list,
                          ) -> list:
    context = ctx.triggered_id
    if (context == ids.MONDAYTASK or context == ids.TUESDAYTASK or context == ids.WEDNESDAYTASK or context == ids.THURSDAYTASK 
        or context == ids.FRIDAYTASK or context == ids.SATURDAYTASK or context == ids.SUNDAYTASK):
        schedulecfg.monday_tasks = monday_tasks_state
        schedulecfg.tuesday_tasks = tuesday_tasks_state
        schedulecfg.wednesday_tasks = wednesday_tasks_state
        schedulecfg.thursday_tasks = thursday_tasks_state
        schedulecfg.friday_tasks = friday_tasks_state
        schedulecfg.saturday_tasks = saturday_tasks_state
        schedulecfg.sunday_tasks = sunday_tasks_state
        schedulecfg.save_schedulecfg()
        schedule_tasks.load_task_order(schedulecfg)
    #remove task from schedule task if this not available
    elif context == ids.DROPDOWNTASKSORDER and monday_tasks_state != None:
        missing_task = list(set(monday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                monday_tasks_state.remove(item)
            schedulecfg.monday_tasks = monday_tasks_state
        missing_task = list(set(tuesday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                tuesday_tasks_state.remove(item)
            schedulecfg.tuesday_tasks = tuesday_tasks_state
        missing_task = list(set(wednesday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                wednesday_tasks_state.remove(item)
            schedulecfg.wednesday_tasks = wednesday_tasks_state
        missing_task = list(set(thursday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                thursday_tasks_state.remove(item)
            schedulecfg.thursday_tasks = thursday_tasks_state
        missing_task = list(set(friday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                friday_tasks_state.remove(item)
            schedulecfg.friday_tasks = friday_tasks_state
        missing_task = list(set(saturday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                saturday_tasks_state.remove(item)
            schedulecfg.saturday_tasks = saturday_tasks_state
        missing_task = list(set(sunday_tasks_state).difference(set(tasks)))
        if missing_task != []:
            for item in missing_task:
                sunday_tasks_state.remove(item)
            schedulecfg.sunday_tasks = sunday_tasks_state
        schedulecfg.save_schedulecfg()
        schedule_tasks.load_task_order(schedulecfg)
    return schedulecfg.monday_tasks, schedulecfg.tuesday_tasks, schedulecfg.wednesday_tasks, schedulecfg.thursday_tasks, schedulecfg.friday_tasks, schedulecfg.saturday_tasks, schedulecfg.sunday_tasks


