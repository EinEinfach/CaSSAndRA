from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids

uploadsunrayfile = dbc.Button(size='lg', class_name='mt-1 bi bi-upload')
okbuttonsunrayimport = dbc.Button('OK', id=ids.OKBUTTONSUNRAYIMPORT, class_name='ms-auto', n_clicks=0)
saveimportedperimeter = dbc.Button(id=ids.BUTTONSAVEIMPORTEDPERIMETER, size='lg', class_name='mt-1 bi bi-save', n_clicks=0)
okbuttonoverwriteperimter= dbc.Button('OK', id=ids.OKBUTTONOVERWRITEPERIMTER, class_name='ms-auto', n_clicks=0)

