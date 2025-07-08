import aiofiles
import json
from pathlib import Path

def file_exists(file_path: str) -> bool:
    """
    :param file_path: The path to the file
    :return: True is the file exists, False otherwise
    """
    return Path(file_path).exists()

async def read_file(file_path: str) -> str:
    """
    Function to read the data from a file
    :param file_path: The path to the file
    :return: A string representation of the data in the file
    """
    input_file = Path(file_path)

    # Test whether the file is a Directory
    if input_file.is_dir():
        raise IsADirectoryError(f'{file_path} is a directory')

    try:
        async with aiofiles.open(input_file, 'r') as f:
            file_data = await f.read()
            return file_data

    except FileNotFoundError:
        raise FileNotFoundError(f'{file_path} does not exist.')
    except Exception as e:
        raise IOError(f'Error while reading data from {file_path}.')

async def read_file_json(file_path: str) -> {}:
    """
    Function to read the data from a file
    :param file_path: The path to the file
    :return: A JSON representation of the data in the file
    """
    input_file = Path(file_path)

    # Test whether the file is a Directory
    if input_file.is_dir():
        raise IsADirectoryError(f'{file_path} is a directory')

    # Test whether the file has the extension .json
    if input_file.suffix != '.json':
        raise TypeError(f'{file_path} is not a JSON file')

    try:
        async with aiofiles.open(input_file, 'r') as f:
            file_data = await f.read()
            file_data_json = json.loads(file_data)
            return file_data_json

    except FileNotFoundError:
        raise FileNotFoundError(f'{file_path} does not exist.')
    except Exception as e:
        raise IOError(f'Error while reading data from {file_path}.')

async def write_file(file_path: str, file_data: str):
    """
    Function to write data to a file
    :param file_path: The path to the file
    :param file_data: The data to be added to the file
    """
    output_file = Path(file_path)

    # Test whether the file is a Directory
    if output_file.is_dir():
        raise IsADirectoryError(f'{file_path} is a directory')

    try:
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(file_data)

    except Exception as e:
        raise IOError(f'Error writing data to {file_path}: {e}')


async def write_file_json(file_path: str, file_data: str):
    """
    Function to write JSON data to a file
    :param file_path: The path to the file
    :param file_data: The data to be added to the file
    """
    output_file = Path(file_path)

    # Test whether the file is a Directory
    if output_file.is_dir():
        raise IsADirectoryError(f'{file_path} is a directory')

    # Overwrite the suffix if not ".json"
    if output_file.suffix != '.json':
        output_file.with_suffix('.json')

    try:
        async with aiofiles.open(output_file, 'w') as f:
            json.dump(file_data, f, indent=2)

    except Exception as e:
        raise IOError(f'Error writing data to {file_path}: {e}')