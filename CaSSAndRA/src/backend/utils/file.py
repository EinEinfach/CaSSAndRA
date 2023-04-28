import logging
logger = logging.getLogger(__name__)
import pandas as pd
import base64
import io

from src.backend.data import mapdata

def parse_sunray_file(content) -> int:
    #logger.debug(content)
    content_type, content = content.split(',')
    decoded = base64.b64decode(content)
    try:
        df = pd.read_json(io.StringIO(decoded.decode('utf-8')))
    except Exception as e:
        logger.warning('Backend: Import of sunray file failed')
        logger.debug(str(e))
        return -1
    mapdata.imported, status = import_sunray(df)
    return status
    

def import_sunray(df: pd.DataFrame()) -> list():
    coords_all = pd.DataFrame()
    try:
        for map_number in range(len(df)): 
            if not df[df.index == map_number].isnull().values.any():
                coords = pd.DataFrame(df['perimeter'][map_number])
                coords['type'] = 'perimeter'    
                try:
                    coords_exclusions = df['exclusions'][map_number]
                    for i, exclusion in enumerate(coords_exclusions):
                        exclusion_df = pd.DataFrame(exclusion)
                        exclusion_df['type'] = 'exclusion_'+str(i)
                        coords = pd.concat([coords, exclusion_df], ignore_index=True)
                except:
                    logger.info('Backend: No exclusions found in sunray file')
                try: 
                    dockpoints_df = pd.DataFrame(df['dockpoints'][map_number])
                    dockpoints_df['type'] = 'dockpoints'
                    coords = pd.concat([coords, dockpoints_df], ignore_index=True)
                except:
                    logger.info('Backend: No dockpoints found in sunray file')
                coords = coords.drop(['delta', 'timestamp', 'sol'], axis=1)
                coords['map_nr'] = map_number
                coords_all = pd.concat([coords_all, coords], ignore_index=True)

        return coords_all, 0
    
    except Exception as e:
        logger.warning('Backend: Sunray file import failed')
        logger.debug(str(e))
        return mapdata.imported, -1

# if __name__ == '__main__':
#     import_sunray('test.txt', 0)