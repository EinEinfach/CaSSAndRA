#!/usr/bin/env python3

#Version:0.70.3 Issue no log file

# package imports
import os
import sys
import click

import logging
from logging.handlers import RotatingFileHandler

# logging setup
logger = logging.getLogger(__name__)
frontend_logger = logging.getLogger("werkzeug")
pil_logger = logging.getLogger("PIL")
logging_choices = click.Choice(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"])


def config_logging(basic_level, log_file_level, web_server_level, pil_level):
    rfh = RotatingFileHandler(
        filename=os.path.dirname(__file__) + "/src/data/log/cassandra.log",
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding=None,
        delay=0,
    )
    rfh.setLevel(log_file_level)
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout), rfh],
        level=basic_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S;",
    )
    frontend_logger.setLevel(web_server_level)
    pil_logger.setLevel(pil_level)


default_data_path = os.path.join(os.path.expanduser('~'), '.cassandra')


@click.group()
def cli():
    """CaSSAndRA App Commands"""

@cli.command()
@click.option('-h', '--host', default='0.0.0.0', show_default=True)
@click.option('-p', '--port', default=8050, show_default=True)
@click.option('--data_path', default=default_data_path, show_default=True)
@click.option('--proxy', default=None, help='format={{input}}::{{output}} example=http://0.0.0.0:8050::https://my.domain.com')
@click.option('--debug', default=False, is_flag=True, help="Enables debug mode for dash application")
@click.option('--app_log_level', default="DEBUG", envvar='APPLOGLEVEL', type=logging_choices, show_default=True)
@click.option('--app_log_file_level', default="DEBUG", envvar='APPLOGFILELEVEL', type=logging_choices, show_default=True)
@click.option('--server_log_level', default="ERROR", envvar='SERVERLOGLEVEL', type=logging_choices, show_default=True)
@click.option('--pil_log_level', default="WARN", envvar='PILLOGLEVEL', type=logging_choices, show_default=True)
def start(host, port, proxy, debug, app_log_level, app_log_file_level, server_log_level, pil_log_level) -> None:
    """ Start the CaSSAndRA Server

        Only some Dash server options are handled as command-line options.
        All other options should use environment variables.
        Find supported environment variables here: https://dash.plotly.com/reference#app.run
        
    """
    # logging config
    config_logging(app_log_level, app_log_file_level, server_log_level, pil_log_level)

    # server and app imports
    import dash
    from src.layout import serve_layout
    from src.backend import backendserver
    
    backendserver.start()
    assets_path = os.path.abspath(os.path.dirname(__file__)) +'/src/assets'

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
                'content': 'width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, viewport-fit=cover' 
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

    app.run_server(host=host, port=port, proxy=proxy, debug=debug)


if __name__ == "__main__":
    cli()
