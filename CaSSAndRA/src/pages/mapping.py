# package imports
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

#local imports
from src.components import ids
from src.components.mapping import map, uploadsunray, modal, buttons, buttongroupcontrol, chooseperimeter

dash.register_page(
    __name__,
    path='/mapping',
    title='Mapping'
)

def update_layout() -> html.Div:
    return dbc.Container([
            dbc.Row([dcc.Graph(ids.MAPPINGMAP)], className='map-graph flex-fill'),
            dbc.Row([
                dbc.Col([
                        buttongroupcontrol.buttonperimeteradd,
                        buttongroupcontrol.buttonperimeterdiff,
                        buttongroupcontrol.buttonhomeadd,
                        buttongroupcontrol.buttonaddnewpoint,
                        buttongroupcontrol.buttondeletelastpoint,
                        buttongroupcontrol.buttonfinishfigure,
                        ], className='text-center d-flex justify-content-between', xs=12, md=6, lg=6),
            ]),
            dbc.Row([
                chooseperimeter.chooseperimeter,
                uploadsunray.uploadsunray,
            ], ),
            modal.sunrayimportstatus,
            modal.overwriteperimter,
            modal.figurefinished,
            modal.selectperimeter,
            html.Div(id=ids.MAPPINGHIDDEN, style={'display': 'none'}),
            ],fluid=True,className="mb-2 d-flex h-100 flex-column")

layout = update_layout()
