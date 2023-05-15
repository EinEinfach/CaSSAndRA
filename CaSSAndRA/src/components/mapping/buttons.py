from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids

#upload sunray file area
uploadsunrayfile = dbc.Button(size='lg', class_name='mt-1 bi bi-filetype-txt', title='upload sunray file')
okbuttonsunrayimport = dbc.Button('OK', id=ids.OKBUTTONSUNRAYIMPORT, class_name='ms-auto', n_clicks=0)
saveimportedperimeter = dbc.Button(id=ids.BUTTONSAVEIMPORTEDPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-plus', n_clicks=0, title='save imported perimeter')
okbuttonoverwriteperimter= dbc.Button('OK', id=ids.OKBUTTONOVERWRITEPERIMTER, class_name='ms-auto', n_clicks=0)

#saved perimeters area
selectperimeter = dbc.Button(id=ids.BUTTONSELECTPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-download', n_clicks=0, title='use selected perimeter')
removeperimeter = dbc.Button(id=ids.BUTTONREMOVEPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-minus', n_clicks=0, title='remove selected perimeter')
addnewperimeter = dbc.Button(id=ids.BUTTONADDNEWPERIMETER, size='lg', class_name='mt-1 bi-file-earmark-plus', n_clicks=0, title='add new perimeter')
copyperimeter = dbc.Button(id=ids.BUTTONCOPYPERIMETER, size='lg', class_name='mt-1 bi bi-clouds', n_clicks=0, title='copy perimeter')
okbuttonselectedperimeter = dbc.Button('OK', id=ids.OKBUTTONSELECTEDPERIMETER, class_name='ms-auto', n_clicks=0)

okbuttonnewperimeter = dbc.Button('OK', id=ids.OKBUTTONNEWPERIMETER, class_name='ms-auto', n_clicks=0)
okbuttoncopyperimeter = dbc.Button('OK', id=ids.OKBUTTONCOPYPERIMETER, class_name='ms-auto', n_clicks=0)
okbuttonremoveperimeter = dbc.Button('OK', id=ids.OKBUTTONREMOVEPERIMETER, class_name='ms-auto', n_clicks=0)

@callback(Output(ids.BUTTONSELECTPERIMETER, 'disabled'),
          Output(ids.BUTTONREMOVEPERIMETER, 'disabled'),
          Output(ids.BUTTONCOPYPERIMETER, 'disabled'),
          [Input(ids.DROPDOWNCHOOSEPERIMETER, 'value')])
def update_perimeter_select_buttons_disabled(dropdown: str()) -> list():
    if dropdown == None:
        return True, True, True
    else:
        return False, False, False


