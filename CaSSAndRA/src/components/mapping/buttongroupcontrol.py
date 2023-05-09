from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids


buttonperimeteradd = dbc.Button(id=ids.BUTTONPERIMETERADD, size='lg', class_name='me-1 mt-1 mb-1 bi bi-plus-circle', disabled=False)

buttonperimeterdiff = dbc.Button(id=ids.BUTTONPERIMETERDIFF, size='lg', class_name='me-1 mt-1 mb-1 bi bi-dash-circle', disabled=False)

buttonhomeadd = dbc.Button(id=ids.BUTTONHOMEADD, size='lg',class_name='me-1 mt-1 mb-1 bi bi-house-add', disabled=False)
                
buttonaddnewpoint = dbc.Button(id=ids.BUTTONADDNEWPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-plus', disabled=False)

buttondeletelastpoint = dbc.Button(id=ids.BUTTONDELETELASTPOINT, size='lg', class_name='me-1 mt-1 mb-1 bi bi-node-minus', disabled=False)

buttonfinishfigure = dbc.Button(id=ids.BUTTONFINISHFIGURE, size='lg', class_name='me-1 mt-1 mb-1 bi bi-check-square-fill', disabled=False)

@callback(Output(ids.MODALFIGUREFINISHED, 'is_open'),
          [Input(ids.BUTTONPERIMETERADD, 'n_clicks'),
           Input(ids.OKBUTTONFIGUREFINISHED, 'n_clicks'),
           State(ids.MODALFIGUREFINISHED, 'is_open')])
def update_mapping(baddp_n_clicks: int, bok_n_clicks, is_open: bool) -> bool:
    if baddp_n_clicks or bok_n_clicks:
        return not is_open
    return is_open
