# create logger
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

frontend_logger = logging.getLogger('werkzeug')
frontend_logger.setLevel(logging.ERROR)

# package imports
import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# local imports
from src.components import ids, navbar, offcanvas, modalremotecontrol, modalinfo
from src.backend import backendserver

def serve_layout():
    return html.Div(
        [
            dcc.Interval(id=ids.INTERVAL, interval=1*4000, n_intervals=0),
            navbar.navbar,
            offcanvas.offcanvas,
            modalremotecontrol.confirm,
            modalinfo.info,
            dash.page_container
            #footer
        ], className='d-flex flex-column h-100 w-100 fixed-top')

def main() -> None:
    backendserver.start()
    assets_path = os.getcwd() +'/src/assets'
    
    app = dash.Dash(
        __name__,
        use_pages=True,    # turn on Dash pages
        pages_folder='src/pages',
        meta_tags=[
            {   # check if device is a mobile device. This is a must if you do any mobile styling
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.5, minimum-scale=0.5' 
            },{
                'name':"apple-mobile-web-app-capable",
                'content':"yes",
            },{
                'name':'theme-color' ,
                'content':'#78c2ad'
            }
        ],
        suppress_callback_exceptions=True,
        prevent_initial_callbacks='initial_duplicate',
        title='CASSANDRA',
        update_title = 'CASSANDRA updating...',
        assets_folder=assets_path
    )
    app.layout = serve_layout   # set the layout to the serve_layout function

    #app.run_server(host='127.0.0.1', port=8050, debug=True, dev_tools_props_check=True)
    app.run_server('0.0.0.0', debug=False)

if __name__ == "__main__":
    main()

    


