from pathlib import Path
from typing import Optional, Union
import json

import gspread
import pandas as pd
from loguru import logger
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter
from gspread.exceptions import GSpreadException
import numpy as np


def flatten_dict(dct: dict, parent_key: str = "", sep: str = "_") -> dict:
    """
    Flatten nested dictionary
    :param dct: nested dictionary
    :param parent_key: parent key
    :param sep: separator
    :return: flattened dictionary
    """
    items = []
    for k, v in dct.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            if isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
    return dict(items)


def remove_empty_lists(dct: dict) -> dict:
    """
    Remove empty lists from dictionary
    :param dct: dictionary
    :return: dictionary without empty lists
    """
    return {k: v for k, v in dct.items() if v != []}


def check_duplicate_columns_in_header(sheet_instance):
     # Get the header row
    header_row = sheet_instance.row_values(1)

    # Count each column name
    header_count = Counter(header_row)

    # Find and print duplicate column names
    duplicates = [col for col, count in header_count.items() if count > 1]
    if duplicates:
        print("Duplicate column names found:", duplicates)
    else:
        print("No duplicate column names found.")
        
    return duplicates

def google_spreadsheet_append(
    title: str, creds, data: Union[pd.DataFrame, dict], scope=None, sheet_index=0
) -> pd.DataFrame:
    # define the scope

    # https://www.analyticsvidhya.com/blog/2020/07/read-and-update-google-spreadsheets-with-python/

    if type(data) == dict:
        # df_novy = pd.DataFrame(data)
        ## maybe this line is better
        first_key = list(data.keys())[0]
        if type(data[first_key]) == list:
            df_novy = pd.DataFrame(data)
        else:
            df_novy = pd.DataFrame(data, index=[0])
    else:
        df_novy = data
    if scope is None:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

    # add credentials to the account
    if type(creds) in (str, Path):
        creds = ServiceAccountCredentials.from_json_keyfile_name(Path(creds), scope)

    # authorize the clientsheet
    client = gspread.authorize(creds)

    # get the instance of the Spreadsheet
    sheet = client.open(title)

    # get the first sheet of the Spreadsheet
    sheet_instance = sheet.get_worksheet(sheet_index)

    
    duplicates = check_duplicate_columns_in_header(sheet_instance)
    if len(duplicates) > 0:
        logger.debug(f"Remove duplicates from the Google spreasheet table. Duplicates={duplicates}")
    # get all the records of the data
    # records_data = sheet_instance.get_all_records()

    # convert the json to dataframe
    # records_df = pd.DataFrame.from_dict(records_data)

    # view the top records
    # records_df.head()
    try:
        records_data = sheet_instance.get_all_records()
    except GSpreadException as e:
        
        logger.error("Duplicate columns in header. Try to remove empty columns in Google Spreasheet.")
        raise e

    # convert the json to dataframe
    records_df = pd.DataFrame.from_dict(records_data)
    
    ############# this is my code
    df_concat = pd.concat([records_df, df_novy], axis=0, ignore_index=True)
    df_empty = pd.DataFrame(columns=df_concat.keys())

    df_out = pd.concat([df_empty, df_novy], axis=0)

    # remove NaN
    df_out2 = df_out.where(pd.notnull(df_out), None)
    df_out2 = df_out2.fillna("")
    logger.debug(f"appended keys={list(df_out2.keys())}")
    logger.debug(f"appended rows={df_out2.values.tolist()}")
    sheet_instance.append_rows(df_out2.values.tolist(), table_range="A1")
    
    
    # update  header
    cell_list = sheet_instance.range(1, 1, 1, len(df_out2.keys()))
    sheet_instance.update_cells(
        cell_list,
    )

    for i, key in enumerate(df_out2.keys()):
        val = cell_list[i].value
        # val = sheet_instance.cell(1, i + 1).value
        if val != key:
            cell_list[i].value = key
            # sheet_instance.update_cell(1, i + 1, key)

    sheet_instance.update_cells(cell_list)

    return df_out2


def remove_iterables_from_dict(dct: dict) -> dict:
    """
    Remove iterables from dictionary
    :param dct: dictionary
    :return: dictionary without iterables
    """
    return {k: v for k, v in dct.items() if not hasattr(v, "__iter__")}


class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def save_json(data: dict, output_json: Union[str, Path], update: bool = True):
    logger.debug(f"Writing '{output_json}'")

    output_json = Path(output_json)
    output_json.parent.mkdir(exist_ok=True, parents=True)
    # os.makedirs(os.path.dirname(output_json), exist_ok=True)
    dct = {}
    if update and output_json.exists():
        with open(output_json, "r") as output_file:
            dct = json.load(output_file)
        logger.debug(f"old keys: {list(dct.keys())}")
    dct.update(data)
    logger.debug(f"updated keys: {list(dct.keys())}")
    with open(output_json, "w") as output_file:
        try:
            json.dump(dct, output_file, indent=4, cls=NumpyEncoder)
        except Exception as e:
            logger.error(f"Error writing json file {output_json}: {e}")
            logger.error(f"Data: {dct}")
            print_nested_dict_with_types(dct, 4)

            raise e

def print_nested_dict_with_types(d: dict, indent: int = 0):
    for k, v in d.items():
        if isinstance(v, dict):
            logger.debug(f"{' ' * indent}{k}:")
            print_nested_dict_with_types(v, indent + 2)
        else:
            logger.debug(f"{' ' * indent}{k}: {type(v)}")
