from __future__ import print_function

import sys
import datetime
import pickle
import os.path
import re
import json

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# entrants = "roryrai | rainbowpoogle | Grim | Terra | Kydra"

# Yes I know globals are awful but I'm lazy. These values are set using config.json.
SIGNUP_SHEET_ID = None
SIGNUP_SHEET_RANGE = None
RESULTS_SHEET_ID = None
RESULTS_SHEET_RANGE = None
SCOPES = None
SRL_COLUMN_INDEX = None
PREFERRED_COLUMN_INDEX = None
TWITCH_COLUMN_INDEX = None
RACE_DATES_COLUMN_INDEX = None
RACE_TIMES_COLUMN_INDEX = None
VIEWING_URL = None

# Passed by the user, this is the 3PM, 10PM, etc
RACE_TIME_SLOT = None

# Maps SRL names to the runner's preferred name and twitch name.
# Returns a dictionary with SRL names as keys, each mapping to
# another dictionary with "twitch" and "preferred" as keys.
# This second dictionary maps to the runner's names and the
# index of the qualifier race they're on ("raceNumber").
# The "raceNumber" key will be -1 if the runner has done the
# maximum number of qualifiers already, so we can skip their results.
def runnerInfo(signupSheet, resultsSheet, entrants):
    try:
        map = {}
        for row in signupSheet:
            info = {}
            info["preferred"] = row[PREFERRED_COLUMN_INDEX]
            info["twitch"] = row[TWITCH_COLUMN_INDEX]
            info["raceNumber"] = -1
            # Figure out how many races this person has done
            # -1 means they've done all their possible races
            for resultsSheetRow in resultsSheet:
                if resultsSheetRow[0] == row[PREFERRED_COLUMN_INDEX]:
                    for i in range(RACE_DATES_COLUMN_INDEX, len(resultsSheetRow), 2):
                        if resultsSheetRow[i] == "":
                            info["raceNumber"] = int((i - RACE_DATES_COLUMN_INDEX) / 2)
                            if row[SRL_COLUMN_INDEX] in entrants:
                                resultsSheetRow[i] = raceDate()
                            break
            map[row[SRL_COLUMN_INDEX]] = info
        return map
    except IndexError:
        return None



# Returns a string with date formatted as (M)M/(D)D/YY
def raceDate():
    today = datetime.date.today()
    dateString = str(today.month) + "/" + str(today.day) + "/" + str(today.year)[2:]
    return dateString


# Sets the race date of whoever is racing today
def raceDates(entrants, resultsSheet, everyone):
    for name in entrants:
        for row in resultsSheet:
            if name == row[0]:
                # Enter today's date for that race number if possible
                if everyone[name]["raceNumber"] != -1:
                    today = datetime.date.today()
                    dateString = str(today.month) + "/" + str(today.day) + "/" + str(today.year)[2:]
                    dateSlot = everyone[name]["raceNumber"] * 2 + RACE_DATES_COLUMN_INDEX
                    row[dateSlot] = dateString
    return resultsSheet


# Creates a kadgar link to view the qualifier.
# Map is the mapping of SRL names to twitch/preferred names and race numbers
# Entrants is an array of SRL names
def kadgar(map, entrants):
    url = VIEWING_URL
    for name in entrants:
        twitchName = map[name]["twitch"]
        url += "/" + twitchName
    print("\nViewing link: %s\n" % url)


# Enter time (as a string)
# Everyone is the mapping of SRL names to twitch/preferred names
# Entrants is an array of SRL names
# Results is the results sheet
def enterTimes(everyone, entrants, results):
    if len(entrants) == 0:
        print("This race has no entrants. No results will be updated. Exiting.")
        sys.exit(0)
    
    print("\nEnter final times for %d %s:" % (len(entrants), "runner" if len(entrants) is 1 else "runners"))
    verified = False

    # Number of racers who have finished
    finished = 0
    while not verified:
        name = input("\nRunner name: ")

        # Don't enter times for people not running
        if name not in entrants:
            print("That's not someone in this race.")
            continue
        if name not in everyone:
            print("I don't know who that is but they're not registered for the qualifiers")
            continue

        # Make sure the user actually enters a time in the correct format
        time = None
        while not time:
            time = matchPattern(input("Final time for %s: " % name))
            if not time:
                print("Invalid time format")

        finished += addResult(everyone, name, time, results)
        print("Finished: %d/%d" % (finished, len(entrants)))
        if finished == len(entrants):
            verified = confirmTimes(results, everyone, entrants)
    return results


# Confirms what's been entered matchs H:MM:SS format.
# In case hours were omitted, adds a leading "0:".
def matchPattern(time):
    if time == "FF":
        return time
    match = re.search("^[0-9]:[0-5][0-9]:[0-5][0-9]$", time)
    if not match:
        match = re.search("^[0-5][0-9]:[0-5][0-9]$", time)
        if not match:
            return None
        time = "0:" + match.group(0)
    return time


# Adds a result to the results sheet.
# Takes runner name, time (as a string),
# the number of that runner's current qualifier,
# and the results sheet itself.
# Returns 1 if the runner has just finished
# and 0 if their time was updated.
def addResult(everyone, runner, time, results):
    finished = 0
    for row in results:
        if everyone[runner]["preferred"] == row[0]:
            raceIndex = everyone[runner]["raceNumber"] + RACE_TIMES_COLUMN_INDEX
            if row[raceIndex] is "":
                finished = 1
            row[raceIndex] = time if time != "FF" else ""
            break
    return finished


# Prints out the results sheet
def printSheet(sheet, colWidth=12):
    rowIndex = 0
    for row in sheet:
        if rowIndex <= 1:
            print(len(row)*colWidth*"-")

        for cell in row:
            if cell:
                write(cell + " "*(colWidth-len(cell)))
            else:
                write("None" + " "*(colWidth-4))
        rowIndex += 1
        write("\n")
    print(len(sheet[0])*colWidth*"-")


# Wrapper on sys.stdout.write()
def write(string):
    sys.stdout.write(string)


# In case we need to ask something. Returns True for 'y' or 'yes' and False for 'n' or 'no'.
def askUser(question):
    accepted = ["y", "yes", "n", "no"]
    answer = ""
    while answer not in accepted:
        answer = input("%s (y/n) " % question).lower()
    return answer == "y" or answer == "yes"


# Asks the user to confirm the current results
def confirmTimes(sheet, everyone, entrants):
    print("Results:\n")
    pad = 15
    for name in entrants:
        for row in sheet:
            if everyone[name]["preferred"] == row[0]:
                # print(name + ":" + " "*(pad-len(name)) + row[everyone[name]["raceNumber"] + RACE_TIMES_COLUMN_INDEX])
                print("%s:%s%s" % (name, " "*(pad-len(name)), row[everyone[name]["raceNumber"] + RACE_TIMES_COLUMN_INDEX]))
    # printSheet(sheet)
    return askUser("\nIs this correct?")


# In case entrants are Ready, remove Ready from their names
def unready(entrants):
    for i in range(0, len(entrants)):
        if "(Ready)" in entrants[i]:
            entrants[i] = entrants[i][:-8]
    return entrants


# Exclude all entrants in the race who are already maxed out
def excludeMaxedOut(everyone, entrants):
    excluded = list()
    for runner in entrants:
        if everyone[runner]["raceNumber"] == -1:
            excluded.append(runner)
    if len(excluded) > 0:
        print("The following runners have reached the maximum number of allowable races and will be excluded from results entry:")
        print(excluded)
        print()
        for runner in excluded:
            entrants.remove(runner)     
    return entrants


# Run the program once data has been retrieved
def run(signupSheet, resultsSheet):
    if signupSheet == None or resultsSheet == None:
        print("Unable to load Google Sheets")
        sys.exit(1)

    # This should be copy/pasted from the .entrants command
    # in SRL. The | and (Ready) can be left in.
    entrants = input("List of entrants (copy from SRL): ")

    # Create an array of entrants' SRL names
    # Some entrants may not be participating
    # due to being maxed out or being the organizer,
    # so remove those entrants.
    entrants = entrants.split(" | ")
    entrants = unready(entrants)
    
    organizerRemoved = False
    while organizerRemoved is False:
        try:
            exclude = input("Race organizer (will be excluded): ")
            entrants.remove(exclude)
            organizerRemoved = True
        except ValueError:
            print("Can't remove someone not in the race")

    everyone = runnerInfo(signupSheet, resultsSheet, entrants)
    
    # Print out a viewing link
    kadgar(everyone, entrants)

    entrants = excludeMaxedOut(everyone, entrants)
    if everyone == None:
        print("Could not load runner information")
        sys.exit(1)



    results = enterTimes(everyone, entrants, resultsSheet)
    updateResults(results)
    # print("Final Results:")
    # printSheet(results, 15)

    
def auth():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

# Copied from Google's quickstart sheets project
def getSheet(id, range):
    creds = auth()

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=id, range=range).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        # for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            # print('%s, %s' % (row[0], row[4]))
        return values


# Sends an update request to the google sheets API to load the race results
# into our google sheets.
def updateResults(data):
    creds = auth()
    service = build('sheets', 'v4', credentials=creds)
    body = {
        "values": data
    }
    
    result = service.spreadsheets().values().update(spreadsheetId=RESULTS_SHEET_ID, range=RESULTS_SHEET_RANGE, valueInputOption="RAW", body=body).execute()
    print("{0} cells updated.".format(result.get("updatedCells")))

    
# Loads the settings in the file config.json
def loadConfig():
    global SIGNUP_SHEET_ID
    global SIGNUP_SHEET_RANGE
    global RESULTS_SHEET_ID
    global RESULTS_SHEET_RANGE
    global SCOPES
    global SRL_COLUMN_INDEX
    global PREFERRED_COLUMN_INDEX
    global TWITCH_COLUMN_INDEX
    global RACE_DATES_COLUMN_INDEX
    global RACE_TIMES_COLUMN_INDEX
    global VIEWING_URL
    
    configFile = open("config.json", "r")
    config = json.loads(configFile.read())
    SIGNUP_SHEET_ID = config["signup_id"]
    SIGNUP_SHEET_RANGE = config["signup_range"]
    RESULTS_SHEET_ID = config["results_id"]
    RESULTS_SHEET_RANGE = config["results_range"]
    SCOPES = config["scopes"]
    SRL_COLUMN_INDEX = config["srl_column_index"]
    PREFERRED_COLUMN_INDEX = config["preferred_column_index"]
    TWITCH_COLUMN_INDEX = config["twitch_column_index"]
    RACE_DATES_COLUMN_INDEX = config["race_dates_column_index"]
    RACE_TIMES_COLUMN_INDEX = config["race_times_column_index"]
    VIEWING_URL = config["view_url"]

# Prints the signup and results sheets to the console to configuration
def checkSheets(signup, results):
    print("SIGNUP SHEET")
    print("-"*80)
    printSheet(signup, 15)
    print("RESULTS SHEET")
    print("-"*80)
    printSheet(results, 15)

def main():
    # Load the configuration and fetch the sheets
    loadConfig()
    signupSheet = getSheet(SIGNUP_SHEET_ID, SIGNUP_SHEET_RANGE)
    resultsSheet = getSheet(RESULTS_SHEET_ID, RESULTS_SHEET_RANGE)
    
    # Handle command line args
    if len(sys.argv) == 1 and sys.argv[1] == "--check":
        checkSheets(signupSheet, resultsSheet)
        sys.exit(0)
    elif len(sys.argv) != 0:
        print("Invalid arguments")
        sys.exit(1)
    
    # Run the actual program
    run(signupSheet, resultsSheet)


if __name__ == "__main__":
    main()










