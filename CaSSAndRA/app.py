#!/usr/bin/env python3

#Version:0.218.3 Bug fix: Joystick control
# package imports
import os
import sys
import click
import signal
import time
from threading import Thread

import logging
from logging.handlers import RotatingFileHandler

# local imports
from src.pathdata import paths
from src.backend.server import cassandra

# logging setup
logger = logging.getLogger(__name__)
frontend_logger = logging.getLogger("werkzeug")
pil_logger = logging.getLogger("PIL")
logging_choices = click.Choice(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"])


def config_logging(log_file, basic_level, log_file_level, web_server_level, pil_level):
    rfh = RotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes= (1024 * 1024)//2,
        backupCount=2,
        encoding=None,
        delay=0,
    )
    rfh.setLevel(log_file_level)
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout), rfh],
        level=basic_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    frontend_logger.setLevel(web_server_level)
    pil_logger.setLevel(pil_level)

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, *args):
    #backendserver.stop()
    cassandra.stop()
    self.kill_now = True

default_data_path = os.path.join(os.path.expanduser('~'), '.cassandra')


def check_startup(data_path):
    # check to see if this is a first-time startup
    if (data_path == default_data_path) and not os.path.exists(data_path):
        
        msgs = [
            f"CaSSAndRA stores your data (settings, maps, tasks, logs, etc) separate from the app directory. This allows us to update the app without losing any data.",
            "",
            f"Configured data_path: {click.style(data_path, bold=True)} (missing)",
            "",
            f"If you continue, CaSSAndRA will:",
            f" - Create {click.style(data_path, bold=True)}",
            f" - Sync missing files from {click.style('/src/data', bold=True)} to {click.style(data_path, bold=True)}",
            "",
            f"Each time you run CaSSAndRA, only missing files are copied and existing files aren't overwritten, so no data will be lost.",
            "",
            f"If this is the first time you are seeing this message, you can also:",
            f" - Review the readme at https://github.com/EinEinfach/CaSSAndRA#cassandra-start",
            f" - enter {click.style('python app.py --help', bold=True)} on the command line"
        ]
        
        # output the message about data_path
        click.echo(click.style('\nYou are starting CaSSAndRA without an existing external data directory\n', bold=True))
        click.echo('-'*80)
        for msg in msgs:
            click.echo(click.wrap_text(msg, initial_indent=' '*4, subsequent_indent=' '*4, width=90))
        click.echo('-'*80)

        # ask the user if they want to continue
        cont = click.confirm(click.style(f'\nContinue with {data_path}?', bold=True), default=True)
        if not cont:
            click.echo('Aborting startup...')
            return False
        else:
            return True
    else:
        return True
    


@click.command()
@click.option('-h', '--host', default='0.0.0.0', show_default=True)
@click.option('-p', '--port', default=8050, show_default=True)
@click.option('--proxy', default=None, help='format={{input}}::{{output}} example=http://0.0.0.0:8050::https://my.domain.com')
@click.option('--data_path', default=default_data_path, show_default=True)
@click.option('--debug', default=False, is_flag=True, help="Enables debug mode for dash application")
@click.option('--app_log_level', default="INFO", envvar='APPLOGLEVEL', type=logging_choices, show_default=True)
@click.option('--app_log_file_level', default="INFO", envvar='APPLOGFILELEVEL', type=logging_choices, show_default=True)
@click.option('--server_log_level', default="ERROR", envvar='SERVERLOGLEVEL', type=logging_choices, show_default=True)
@click.option('--pil_log_level', default="WARN", envvar='PILLOGLEVEL', type=logging_choices, show_default=True)
@click.option('--init', is_flag=True, help="Accepts defaults when initializing app for the first time")
@click.option('--mowername', help="Set mower name for UI display")
def start(host, port, proxy, data_path, debug, app_log_level, app_log_file_level, server_log_level, pil_log_level, init, mowername) -> None:
    """ Start the CaSSAndRA Server

        Only some Dash server options are handled as command-line options.
        All other options should use environment variables.
        Find supported environment variables here: https://dash.plotly.com/reference#app.run
        
    """
    # Mowername
    display_name = "CaSSAndRA"
    if mowername:  # if mowername is given
        display_name += f" -- {mowername}"
    os.environ["MOWERNAME"] = display_name

    if init or check_startup(data_path):
        # server and app imports
        import dash
        from src.layout import serve_layout
        from src.backend.data.utils import init_data
        import dash_bootstrap_components as dbc
        
        # initialize data files
        file_paths = init_data(data_path)
        paths.set(file_paths)
        
        # logging config
        config_logging(file_paths.log, app_log_level, app_log_file_level, server_log_level, pil_log_level)

        # start backend server
        cassandra.setup(file_paths)
        cassandra.run()
        #backendserver.start(file_paths)


        assets_path = os.path.abspath(os.path.dirname(__file__)) +'/src/assets'
        app = dash.Dash(
            __name__,
            use_pages=True,    # turn on Dash pages
            pages_folder='src/pages',
            external_stylesheets=[
                # dbc.themes.MINTY,
            #     dbc.icons.BOOTSTRAP
            ],  # fetch the proper css items we want
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
            update_title = None, #'CASSANDRA updating...',
            assets_folder=assets_path, 
        )
        app.layout = serve_layout   # set the layout to the serve_layout function

        app.run_server(host=host, port=port, proxy=proxy, debug=debug)


if __name__ == "__main__":
    #create an instance for server killer
    killer = GracefulKiller()

    #create a thread for dash application
    dash_thread = Thread(target=start, args=())
    dash_thread.setDaemon(True)
    dash_thread.start()
    
    while not killer.kill_now:
        time.sleep(1)
    logger.info('Server was killed gracefully')
    
