'''
odpt_train_board_pi_lcd.py by Benjamin Cooper 2020 (https://ratticon.com)
----------------------------------------------------------------
Train Departure Board for Raspberry Pi with an I2C LCD attached.

Function:
- Connects to the Tokyo ODPT (Open Data for Public Transportation) API
- Downloads the train times for the configured station
- Formats the train times to print on LCD character display
- Prints departure times and animates overflowing text
- Refreshes every X seconds (30 by default)

Requirements:
- Raspberry Pi running Raspbian (Built on Pi Zero WH running Raspbian 10)
- I2C LCD character display connected to Raspbery Pi GPIO pins:
    Display SDA pin <------------> Pi SDA pin
    Display SCL pin <------------> Pi SCL pin
    Display 5V (VCC) pin <-------> Pi 5V pin
    Display Ground (GND) pin <---> Pi GND pin
- Python 3 or later (3.7 at time of writing)
- An internet connection
- An ODPT API key from https://developer-tokyochallenge.odpt.org/en/info
  Before running this script, export your API as an environment variable with the command:
  export ODPT_API_KEY="PASTE_YOUR_KEY_HERE"

For more info on how to set up:
https://ratticon.com/tutorial-train-departure-board-with-pi-python-and-an-lcd/
'''


# Imports ---------------------------------------------------------------------

import os
import requests
import pprint
from datetime import datetime
import time
import math
import I2C_LCD_driver


# Functions -------------------------------------------------------------------

def get_stationTimetable(response_json):
    '''
    Checks response_json and returns the contents of the
    stationTimetableObject if found
    '''
    results = []
    for list_item in response_json:
        if 'odpt:stationTimetableObject' in list_item:
            results = list_item['odpt:stationTimetableObject']
            break
    print(f'Got {len(results)} train times')
    return results


def get_all_departures(stationTimetable):
    '''
    Checks stationTimetable and returns a list of departing trains, including
    their time, train type and destination properties.
    '''
    results = []
    for train in stationTimetable:
        # Get departure time
        departureTime = train["odpt:departureTime"]
        # Get Local or Express
        if 'Local' in train["odpt:trainType"]:
            trainType = "Local"
        elif 'Express' in train["odpt:trainType"]:
            trainType = "Express"
        else:
            trainType = train["odpt:trainType"]
        # Get destination
        destinationStation = train["odpt:destinationStation"][-1].split('.')[-1]
        # Add item to all_departures array
        results.append({"departureTime": departureTime, "trainType": trainType, "destinationStation": destinationStation})
    return results


def get_future_departures(departure_list):
    '''
    Takes departure_list and returns a list of departures beginning from
    the current time.
    '''
    results = []
    now = datetime.now()
    # Calculate next 24 hours
    future_hours = []
    for hour in range(now.hour, now.hour+24):
        if hour >= 24:
            hour -= 24
        future_hours.append(hour)
    # Build list of departures in order from current time
    for hour in future_hours:
        for departure in departure_list:
            hours_mins = departure["departureTime"].split(':')
            if int(hours_mins[0]) == hour:
                if hour == now.hour and int(hours_mins[1]) < now.minute:
                    continue
                results.append(departure)
    return results


def get_departures(apikey=".", station="Tokyu.Oimachi.Jiyugaoka", direction="Outbound"):
    '''
    Queries ODPT API for timetable for station, direction.
    Returns a list of departures starting from the current time.
    '''
    # Get data from ODPT
    print(f'Querying ODPT API for "{direction}" trains for "{station}"...')
    request_url = (
        'https://api-tokyochallenge.odpt.org/api/v4/odpt:StationTimetable?'
        + f'acl:consumerKey={apikey}'
        + f'&odpt:station=odpt.Station:{station}'
        + f'&odpt:railDirection=odpt.RailDirection:{direction}'
    )
    try:
        response = requests.get(request_url)
    except requests.exceptions.HTTPError as errh:
        print("An Http Error occurred:\n" + repr(errh))
        return []
    except requests.exceptions.ConnectionError as errc:
        print("An Error Connecting to the ODPT API occurred:\n" + repr(errc))
        return []
    except requests.exceptions.Timeout as errt:
        print("A Timeout Error occurred:\n" + repr(errt))
        return []
    except requests.exceptions.RequestException as err:
        print("An Unknown Error occurred:\n" + repr(err))
        return []
    # Check API response is OK
    if response:
        print(f'[Response {response.status_code} - OK]')
    else:
        print(f'[Response {response.status_code} - ERROR / BAD TOKEN OR QUERY]')
        return []
    # Find the stationTimetableObject
    stationTimetable = get_stationTimetable(response.json())
    # Get the times
    all_departures = get_all_departures(stationTimetable)
    # Collect departures for the rest of the day
    future_departures = get_future_departures(all_departures)
    return future_departures


def trim_departures(departure_list=[], length=4):
    '''
    Takes departure_list and trims to length. Returns trimmed departure list.
    '''
    results = []
    for train in departure_list:
        results.append(train)
        if len(results) == length:
            return results
    return results


def get_printable_departures(departure_list=[]):
    '''
    Takes departure_list, formats trainType to fit on LCD and converts
    destinationStation to uppercase. Returns formatted departure list.
    '''
    results = []
    for departure in departure_list:
        train_type = departure["trainType"]
        train_time = departure["departureTime"]
        train_dest = departure["destinationStation"].upper()
        if train_type == "Express":
            train_type = "EXP"
        elif train_type == "Local":
            train_type = "Loc"
        results.append(f'{train_type} {train_time} {train_dest}')
    return results


def get_scrollable_destinations(departure_list=[]):
    '''
    Takes departure_list and returns a list of only the destinationStation
    objects.
    '''
    results = []
    for departure in departure_list:
        results.append(departure["destinationStation"].upper())
    return results


def print_departures(departure_list=[], lcd_width=20):
    '''
    Clears LCD and prints each departure in departure_list.
    Trims each row to fit on screen if needed.
    '''
    mylcd.lcd_clear()
    lcd_row = 1
    for departure in departure_list:
        print(departure)
        if len(departure) > lcd_width:
            departure = departure[0:lcd_width]
        mylcd.lcd_display_string(departure, lcd_row)
        lcd_row += 1


def scroll_area(start_pos=0, width=10, duration_sec=30, data=[]):
    '''
    Scrolls data on LCD from start_position to width for duration_sec
    '''
    # Initialize counter for cycles
    elapsed = 0
    # Precompute frames
    frames = []
    for row in data:
        # If data doesn't need scrolling, append only one frame
        if len(row) <= width:
            frames.append([row])
            continue
        # Calculate frames needed to scroll all characters in row
        overflow_chars = len(row) - width
        row_frames = []
        for index in range(0, overflow_chars+1):
            row_frames.append(row[(0+index):(width+index)])
        frames.append(row_frames)
    # DEBUG - Uncomment to print precomputed frames
    # pp.pprint(frames)
    # Initialize counter for frames on each row to enable looping
    current_positions = []
    for row_frames in frames:
        current_positions.append(0)
    # Animate scrolling area for duration_sec
    while elapsed < duration_sec:
        for row_index, row_frames in enumerate(frames, start=1):
            if current_positions[row_index-1] >= len(row_frames):
                current_positions[row_index-1] = 0
            mylcd.lcd_display_string(row_frames[current_positions[row_index-1]], row_index, start_pos)
            current_positions[row_index-1] += 1
        time.sleep(1.5)
        elapsed += 1.5


def page_area(start_pos=0, width=10, duration_sec=30, data=[]):
    '''
    Pages data on LCD from start_position to width for duration_sec
    '''
    # Initialize counter for cycles
    elapsed = 0
    # Precompute frames
    frames = []
    for row in data:
        # If data doesn't need scrolling, append only one frame
        if len(row) <= width:
            frames.append([row])
            continue
        # Calculate frames needed to scroll all characters in row
        pages_required = math.ceil(len(row) / width)
        row_frames = []
        for index in range(0, pages_required):
            frame_start = index * width
            frame_end = frame_start + width
            if frame_end > len(row):
                frame_end = len(row)
            padded_frame = str(row[frame_start:frame_end]).ljust(width)
            row_frames.append(padded_frame)
        frames.append(row_frames)
    # DEBUG - Uncomment to print precomputed frames
    # pp.pprint(frames)
    # Initialize counter for frames on each row to enable looping
    current_positions = []
    for row_frames in frames:
        current_positions.append(0)
    # Animate scrolling area for duration_sec
    while elapsed < duration_sec:
        for row_index, row_frames in enumerate(frames, start=1):
            if current_positions[row_index-1] >= len(row_frames):
                current_positions[row_index-1] = 0
            mylcd.lcd_display_string(row_frames[current_positions[row_index-1]], row_index, start_pos)
            current_positions[row_index-1] += 1
        time.sleep(1.5)
        elapsed += 1.5


def wipe_lcd(direction='up', rows=4, width=20):
    '''
    Animates wiping the LCD display in direction specified.
    Valid direction values are 'up' or 'down'
    '''
    rows += 1
    for row in range(1, rows):
        if direction == 'up':
            row = (rows - row)
        mylcd.lcd_display_string(' '*width, row)
        time.sleep(0.05)


# Config Variables ------------------------------------------------------------
station = "Tokyu.Oimachi.Jiyugaoka"   # Operator, Line, Station name
direction = "Outbound"                # Accepts "Inbound" or "Outbound"
lcd_width = 20                        # Width of LCD in characters
lcd_rows = 4                          # Number of rows on LCD display
refresh_seconds = 30                  # Seconds to wait between updates
overflow_animation = 'paging'         # Accepts 'paging' or 'scrolling'

# Startup ---------------------------------------------------------------------
ODPT_API_KEY = os.environ["ODPT_API_KEY"]
pp = pprint.PrettyPrinter(indent=4)
print(f'Initializing {lcd_width}x{lcd_rows} LCD...')
mylcd = I2C_LCD_driver.lcd()

# Main Loop -------------------------------------------------------------------
while True:
    # Get data
    future_departures = get_departures(ODPT_API_KEY, station, direction)
    print(f'\nNext {lcd_rows} trains:')
    # Check if no data
    if len(future_departures) < 1:
        print(f'< NO DATA >\nRetrying in {refresh_seconds} seconds...\n')
        mylcd.lcd_clear()
        mylcd.lcd_display_string('< NO DATA >', 1)
        time.sleep(refresh_seconds)
        wipe_lcd(direction='up', rows=lcd_rows, width=lcd_width)
        continue
    # Trim data
    trimmed_departures = trim_departures(future_departures, length=lcd_rows)
    # Format data for printing
    printable_departures = get_printable_departures(trimmed_departures)
    # Print data
    print_departures(printable_departures, lcd_width)
    # Get destinations to scroll
    destinations_to_scroll = get_scrollable_destinations(trimmed_departures)
    # Scroll frames until next data refresh
    print(f'{overflow_animation.title()} display for {refresh_seconds} seconds...\n')
    if overflow_animation == 'scrolling':
        scroll_area(start_pos=10, width=lcd_width-10, duration_sec=refresh_seconds, data=destinations_to_scroll)
    else:
        page_area(start_pos=10, width=lcd_width-10, duration_sec=refresh_seconds, data=destinations_to_scroll)
    # Animate screen wipe for refresh
    wipe_lcd(direction='up', rows=lcd_rows, width=lcd_width)
