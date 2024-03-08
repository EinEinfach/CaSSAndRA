from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from src.backend.data.mapdata import mapping_maps
from .. import ids

#import map area
uploadsunrayfile = dbc.Button(class_name='mt-1 me-1 bi bi-filetype-txt', title='upload sunray file')
saveimportedperimeter = dbc.Button(id=ids.BUTTONSAVEIMPORTEDPERIMETER, class_name='mt-1 me-1 bi bi-cloud-plus', n_clicks=0, title='save imported perimeter')
okbuttonoverwriteperimter= dbc.Button('OK', id=ids.OKBUTTONOVERWRITEPERIMTER, class_name='ms-auto', n_clicks=0)

#select map area
selectperimeter = dbc.Button(id=ids.BUTTONSELECTPERIMETER, class_name='mt-1 me-1 bi bi-cloud-download btn-info', n_clicks=0, title='use selected perimeter')
removeperimeter = dbc.Button(id=ids.BUTTONREMOVEPERIMETER, class_name='mt-1 me-1 bi bi-trash', n_clicks=0, title='remove selected perimeter')
addnewperimeter = dbc.Button(id=ids.BUTTONADDNEWPERIMETER, class_name='mt-1 me-1 bi-file-earmark-plus', n_clicks=0, title='add new perimeter')
copyperimeter = dbc.Button(id=ids.BUTTONCOPYPERIMETER, class_name='mt-1 me-1 bi bi-copy', n_clicks=0, title='copy perimeter')
finishfigure = dbc.Button(id=ids.BUTTONFINISHFIGURE, class_name='mt-1 me-1 bi bi-floppy btn-success', disabled=False, title='finish and save')
renameperimeter = dbc.Button(id=ids.BUTTONRENAMEPERIMETER, class_name='mt-1 me-1 bi bi-pencil-square', disabled=False, title='rename perimeter')
okbuttonselectedperimeter = dbc.Button('OK', id=ids.OKBUTTONSELECTEDPERIMETER, class_name='ms-auto', n_clicks=0)

okbuttonnewperimeter = dbc.Button('OK', id=ids.OKBUTTONNEWPERIMETER, class_name='ms-auto', n_clicks=0)
okbuttoncopyperimeter = dbc.Button('OK', id=ids.OKBUTTONCOPYPERIMETER, class_name='ms-auto', n_clicks=0)
okbuttonremoveperimeter = dbc.Button('OK', id=ids.OKBUTTONREMOVEPERIMETER, class_name='ms-auto', n_clicks=0)
okbuttonfinishmapping = dbc.Button('OK', id=ids.OKBUTTONFINISHMAPPING, class_name='ms-auto', n_clicks=0)
okbuttonnofixsolution = dbc.Button('OK', id=ids.OKBUTTONNOFIXSOLUTION, class_name='ms-auto', n_clicks=0)
okbuttonrenameperimeter = dbc.Button('OK', id=ids.OKBUTTONRENAMEPERIMETER, class_name='ms-auto', n_clicks=0)


@callback(Output(ids.BUTTONSELECTPERIMETER, 'disabled'),
          Output(ids.BUTTONREMOVEPERIMETER, 'disabled'),
          Output(ids.BUTTONCOPYPERIMETER, 'disabled'),
          Output(ids.BUTTONRENAMEPERIMETER, 'disabled'),
          [Input(ids.DROPDOWNCHOOSEPERIMETER, 'value')])
def update_perimeter_select_buttons_disabled(dropdown: str()) -> list():
    if dropdown == None:
        return True, True, True, True
    else:
        return False, False, False, False
