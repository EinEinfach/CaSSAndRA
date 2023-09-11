#!/usr/bin/env python3

#Version:0.60.1 Fix modal beahaivor in mapping mode on mobile devices

# create logger
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

frontend_logger = logging.getLogger('werkzeug')
frontend_logger.setLevel(logging.ERROR)

pil_logger = logging.getLogger('PIL')
pil_logger.setLevel(logging.WARNING)

# package imports
import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# local imports
from src.components import ids, navbar, offcanvas, modalremotecontrol, modalinfo, modalerror
from src.backend import backendserver

def serve_layout() -> html.Div:
    return html.Div(
        [
            dcc.Interval(id=ids.INTERVAL, interval=1*3000, n_intervals=0),
            #dcc.Interval(id=ids.STATEMAPINTERVAL, interval=1*3000, n_intervals=0, disabled=True),
            #dcc.Interval(id=ids.MAPPINGINTERVAL, interval=1*3000, n_intervals=0, disabled=True),
            dcc.Location(id=ids.URLUPDATE, refresh=True),
            navbar.navbar,
            offcanvas.offcanvas,
            modalremotecontrol.confirm,
            modalinfo.info,
            modalerror.mapuploadfailed,
            dash.page_container
            #footer
        ]) 

def main() -> None:
    backendserver.start()
    assets_path = os.path.dirname(__file__) +'/src/assets'

    app = dash.Dash(
        __name__,
        use_pages=True,    # turn on Dash pages
        pages_folder='src/pages',
        # external_stylesheets=[
        #     dbc.themes.MINTY,
        #     dbc.icons.BOOTSTRAP
        # ],  # fetch the proper css items we want
        meta_tags=[
            {   # check if device is a mobile device. This is a must if you do any mobile styling
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0' 
            },
            {
                'name':"apple-mobile-web-app-capable",
                'content':"yes",
            },
            {
                'name':'theme-color' ,
                'content':'#78c2ad'
            },
        ],
        suppress_callback_exceptions=True,
        title='CASSANDRA',
        update_title = 'CASSANDRA updating...',
        assets_folder=assets_path, 
    )
    app.layout = serve_layout   # set the layout to the serve_layout function

    #app.run_server(host='127.0.0.1', port=8050, debug=True, dev_tools_props_check=True)
    app.run_server('0.0.0.0', debug=False, port=8050)

if __name__ == "__main__":
    main()


