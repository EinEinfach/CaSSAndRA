from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids
from . import buttons

connection = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle('Warning')),
                dbc.ModalBody('Are you sure? This will overwrite your settings and restart backend server'),
                dbc.ModalFooter([
                    buttons.okbutton,  
                ] ),
            ],
            id=ids.MODALCONNECTION,
            is_open=False,
        )

mapandposition = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle('Warning')),
                dbc.ModalBody('Are you sure? This will overwrite your map settings for coverage path planner'),
                dbc.ModalFooter([
                    buttons.okbuttonmapsettings,  
                ] ),
            ],
            id=ids.MODALMAPSETTINGS,
            is_open=False,
        )

app = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle('Warning')),
                dbc.ModalBody('Are you sure? This will overwrite your app settings'),
                dbc.ModalFooter([
                    buttons.okbuttonappsettings,  
                ] ),
            ],
            id=ids.MODALAPPSETTINGS,
            is_open=False,
        )

robot = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle('Warning')),
                dbc.ModalBody('Are you sure? This will overwrite your robot settings'),
                dbc.ModalFooter([
                    buttons.okbuttonrobotsettings
                ])
            ],
            id=ids.MODALROBOTSETTINGS,
            is_open=False,
        )

