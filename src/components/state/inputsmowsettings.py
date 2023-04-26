# from dash import html, Input, Output, State, callback, ctx
# import dash_bootstrap_components as dbc

# from components import ids
# from backend.data import mapdata


# accordion = dbc.Accordion([
#                 dbc.AccordionItem([
#                     dbc.Row([
#                         dbc.Col([
#                             html.P(['pattern'], className='mb-0'),
#                             dbc.Select(
#                                 id=ids.INPUTPATTERNSTATE, 
#                                 options=[
#                                     {'label': 'lines', 'value': 'lines'},
#                                     {'label': 'squares', 'value': 'squares'},
#                                     {'label': 'rings', 'value': 'rings'},
#                                 ],
#                                 value=mapdata.pattern
#                             )
#                         ]),
#                         dbc.Col([
#                             html.P(['width'], className='mb-0'),
#                             dbc.Input(id=ids.INPUTMOWOFFSETSTATE, placeholder=str(mapdata.mowoffset), type='number', min=0, max=1, step=0.01, size='sm'),
#                         ]),
#                         dbc.Col([
#                             html.P(['angle'], className='mb-0'),
#                             dbc.Input(id=ids.INPUTMOWOANGLESTATE, placeholder=str(mapdata.mowangle), type='number', min=0, max=359, step=1, size='sm')
#                         ]),
#                         dbc.Col([
#                             dbc.Button(id=ids.BUTTONOKINPUTMAPSETTINGS, size='md', class_name='me-1 mt-3 bi bi-check-square-fill')
#                         ])
#                     ])
#                 ], title='mow settings', class_name='justify-content-sm-center')
#             ], start_collapsed=True
#             )

# @callback(Output(ids.STATEHIDDEN, 'children'),
#           [Input(ids.BUTTONOKINPUTMAPSETTINGS, 'n_clicks'),
#            State(ids.INPUTPATTERNSTATE, 'value'),
#            State(ids.INPUTMOWOFFSETSTATE, 'value'),
#            State(ids.INPUTMOWOANGLESTATE, 'value')])
# def update_mow_settings(bok: int, pattern: str(), mowoffset: str(), mowangle: str()) -> str():
#     context = ctx.triggered_id
#     if context == ids.BUTTONOKINPUTMAPSETTINGS:
#         if pattern != 'lines' and pattern != 'squares' and pattern != 'rings':
#             mapdata.patternstatepage = 'lines'
#         else:
#             mapdata.patternstatepage = pattern

#         try:
#             if 0.1 <= float(mowoffset) <= 1:
#                 mapdata.mowoffsetstatepage = float(mowoffset)
#             else:
#                 mapdata.mowanglestatepage = 0.18
#         except:
#             mapdata.mowanglestatepage = 0.18   
        
#         try:
#             if 0 <= int(mowangle) < 360:
#                 mapdata.mowanglestatepage = int(mowangle)
#             else:
#                 mapdata.mowanglestatepage = 0
#         except:
#             mapdata.mowanglestatepage = 0
    
#     # if 0 <= int(mowangle) < 360:
#     #     mapdata.mowanglestatepage = mowangle
#     # else:
#     #     mapdata.mowanglestatepage = 0

#     return str(mapdata.patternstatepage)
    
