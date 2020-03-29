# odpt-trainboard-pi-lcd

Train Departure Board for Raspberry Pi with an I2C LCD attached using ODPT API

# Function
- Connects to the Tokyo ODPT (Open Data for Public Transportation) API
- Downloads the train times for the configured station
- Formats the train times to print on LCD character display
- Prints departure times and animates overflowing text
- Refreshes every X seconds (30 by default)

# Requirements
- Raspberry Pi running Raspbian (Built on Pi Zero WH running Raspbian 10)
- I2C LCD character display connected to Raspbery Pi GPIO pins:

        Display SDA pin <------------> Pi SDA pin
        Display SCL pin <------------> Pi SCL pin
        Display 5V (VCC) pin <-------> Pi 5V pin
        Display Ground (GND) pin <---> Pi GND pin

- Python 3 or later (3.7 at time of writing)
- An internet connection
- An ODPT API key from https://developer-tokyochallenge.odpt.org/en/info

# Important
Before running this script, export your API as an environment variable with the command:

    export ODPT_API_KEY="PASTE_YOUR_KEY_HERE"

# More Info
For more info on how to set up:
https://ratticon.com/tutorial-train-departure-board-with-pi-python-and-an-lcd/
