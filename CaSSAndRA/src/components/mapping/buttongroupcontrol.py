from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids


buttonperimeteradd = dbc.Button(id=ids.BUTTONPERIMETERADD, size='lg', class_name='me-1 mt-1 mb-1 bi bi-plus-circle', disabled=False)

buttonperimeterdiff = dbc.Button(id=ids.BUTTONPERIMETERDIFF, size='lg', class_name='me-1 mt-1 mb-1 bi bi-dash-circle', disabled=False)

buttonhomeadd = dbc.Button(id=ids.BUTTONHOMEADD, size='lg',class_name='me-1 mt-1 mb-1 bi bi-house-add', disabled=False)
                
buttonaddnewpoint = dbc.Button(id=ids.BUTTONADDNEWPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-plus', disabled=False)

buttondeletelastpoint = dbc.Button(id=ids.BUTTONDELETELASTPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-minus', disabled=False)

buttonfinishfigure = dbc.Button(id=ids.BUTTONFINISHFIGURE, size='lg', class_name='me-1 mt-1 mb-1 bi bi-check-square-fill', disabled=False)

