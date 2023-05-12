from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids

uploadsunrayfile = dbc.Button(size='lg', class_name='mt-1 bi bi-filetype-txt', title='upload sunray file')

okbuttonsunrayimport = dbc.Button('OK', id=ids.OKBUTTONSUNRAYIMPORT, class_name='ms-auto', n_clicks=0)

saveimportedperimeter = dbc.Button(id=ids.BUTTONSAVEIMPORTEDPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-plus', n_clicks=0, title='save imported perimeter')

okbuttonoverwriteperimter= dbc.Button('OK', id=ids.OKBUTTONOVERWRITEPERIMTER, class_name='ms-auto', n_clicks=0)

okbuttonfigurefinished = dbc.Button('OK', id=ids.OKBUTTONFIGUREFINISHED, class_name='ms-auto', n_clicks=0)

selectperimeter = dbc.Button(id=ids.BUTTONSELECTPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-download', n_clicks=0)

removeperimeter = dbc.Button(id=ids.BUTTONREMOVEPERIMETER, size='lg', class_name='mt-1 bi bi-cloud-minus', n_clicks=0)

okbuttonselectedperimeter = dbc.Button('OK', id=ids.OKBUTTONSELECTEDPERIMETER, class_name='ms-auto', n_clicks=0)


