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
        ]
    )

def main() -> None:
    logger.info('Backend: Starting Backend server')
    backendserver.start()
    
    app = dash.Dash(
        __name__,
        use_pages=True,    # turn on Dash pages
        pages_folder='src/pages',
        external_stylesheets=[
            dbc.themes.MINTY,
            dbc.icons.BOOTSTRAP
        ],  # fetch the proper css items we want
        meta_tags=[
            {   # check if device is a mobile device. This is a must if you do any mobile styling
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.5, minimum-scale=0.5' 
            }
        ],
        suppress_callback_exceptions=True,
        title='CASSANDRA'
    )
    app.layout = serve_layout   # set the layout to the serve_layout function

    #app.run_server(host='127.0.0.1', port=8050, debug=True, dev_tools_props_check=True)
    app.run_server('0.0.0.0', debug=False)

if __name__ == "__main__":
    main()

    


