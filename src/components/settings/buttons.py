from dash import html, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc

from .. import ids


savebutton = dbc.Button('Save and reboot', color='primary', className='m-1', id=ids.BUTTONSAVEANDREBOOT)
savebuttonmapsettings = dbc.Button('Save and reboot', color='primary', className='m-1', id=ids.BUTTONSAVEANDREBOOTMAPSETTINGS)
savebuttonappsettings = dbc.Button('Save and reboot', color='primary', className='m-1', id=ids.BUTTONSAVEANDREBOOTAPPSETTINGS)
okbutton = dbc.Button('OK', id=ids.BUTTONOK, className='ms-auto', n_clicks=0)
okbuttonmapsettings = dbc.Button('OK', id=ids.BUTTONOKMAPSETTINGS, className='ms-auto', n_clicks=0)
okbuttonappsettings = dbc.Button('OK', id=ids.BUTTONOKAPPSETTINGS, className='ms-auto', n_clicks=0)


