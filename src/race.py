from __future__ import print_function

import sys
import datetime
import pickle
import os.path
import re


from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# entrants = "roryrai | rainbowpoogle | Grim | Terra | Kydra"

# Spreadsheet IDs and ranges
SIGNUP_SHEET_ID = "15tP_j0SnXZu3GbCdRmnDqTCJZlhOEVqx_jBCAS03qQg"
SIGNUP_SHEET_RANGE = "Form Responses 1!C2:O54"
RESULTS_SHEET_ID = "1uRJvUgsTRP3LM3CK4vclrYrqVGj_RqSOrDaHZ8RpyDY"
RESULTS_SHEET_RANGE = "Times!A2:X"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Index of SRL name in the signup sheet
SRL_COLUMN_INDEX = 12

# Index of preferred name in the signup sheet
PREFERRED_COLUMN_INDEX = 0

# Index of Twitch name in the signup sheet
TWITCH_COLUMN_INDEX = 11

# Index of the first Race Date column in the results sheet
RACE_DATES_COLUMN_INDEX = 9

# Index of the first Qualifier Time column in the results sheet
RACE_TIMES_COLUMN_INDEX = 2

# Start of the url for the kadgar link for viewing
VIEWING_URL = "http://kadgar.net"


# Fake signup spreadsheet rows
# [Preferred, Discord, SRL, Twitch]
signupHeader = ["Preferred", "Discord", "SRL", "Twitch"]
roryrai = ['Roryrai', 'Roryrai#4160', 'roryrai', 'Roryrai']
meldon = ['Meldon', 'Meldon#1234', 'Meldon', 'MeldonTaragon']
terra = ['Terra', 'Terra#1234', 'Terra', 'Terra21']
vulajin = ['Vulajin', 'Vulajin#1234', 'Vulajin', 'Vulajin']

# Fake results spreadsheet rows
#                Name,       Avg,       Race 1,     Race 2,     Race 3,     Date 1,     Vod 1,      Date 2,     Vod 2,      Date 3,     Vod 3
resultsHeader = ['Name',     'Avg',     'Race 1',  'Race 2',   'Race 3',   'Date 1',   'Vod 1',    'Date 2',   'Vod 2',    'Date 3',   'Vod 3']
resultsR =      ['Roryrai',  None,      None,       None,       None,       None,       None,       None,       None,       None,       None]
resultsM =      ['Meldon',   None,      None,       None,       None,       None,       None,       None,       None,       None,       None]
resultsT =      ['Terra',    None,      '30:21',    None,       None,       '3/20/19',  'vod-1',    '3/30/19',  None,       None,       None]
resultsV =      ['Vulajin',  None,      '30:38',    '31:12',    '31:30',    '3/22/19',  'vod-1',    '3/28/19',  'vod-2',    '3/30/19',  None]

# "Spreadsheets"
signupSheet = [signupHeader, roryrai, meldon, terra, vulajin]
resultsSheet = [resultsHeader, resultsR, resultsM, resultsT, resultsV]


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
        print(map)
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
    print("\nViewing link: %s" % url)


# Enter time (as a string)
# Everyone is the mapping of SRL names to twitch/preferred names
# Entrants is an array of SRL names
# Results is the results sheet
def enterTimes(everyone, entrants, results):
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
    for runner in entrants:
        if everyone[runner]["raceNumber"] == -1:
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
    entrants = excludeMaxedOut(everyone, entrants)
    if everyone == None:
        print("Could not load runner information")
        sys.exit(1)

    # Print out a viewing link
    kadgar(everyone, entrants)

    results = enterTimes(everyone, entrants, resultsSheet)
    print("Final Results:")
    printSheet(results, 15)


# Copied from Google's quickstart sheets project
def getSheet(id, range, scope):
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
                'credentials.json', scope)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=id,
                                range=range).execute()
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
def updateSheet(sheet, data):
    requests = []
    updateReq = {
        "rows": [
        {
          object(data)
        }
        ],
        "fields": string,

        # Union field area can be only one of the following:
        "start": {
        object(GridCoordinate)
        },
        "range": {
        object(GridRange)
        }
        # End of list of possible types for union field area.
}


def main():
    signupSheet = getSheet(SIGNUP_SHEET_ID, SIGNUP_SHEET_RANGE, SCOPES)
    resultsSheet = getSheet(RESULTS_SHEET_ID, RESULTS_SHEET_RANGE, SCOPES)
    
    # printSheet(signupSheet)
    # printSheet(resultsSheet)
    
    # for row in signupSheet:
        # print(row[PREFERRED_COLUMN_INDEX])
        # try:
            # print(row[TWITCH_COLUMN_INDEX])
            # print(row[SRL_COLUMN_INDEX])
        # except IndexError:
            # print("IndexError")
    # for row in resultsSheet:
        # print(row[0], len(row))
        # try:
            # if row[RACE_TIMES_COLUMN_INDEX] == None:
                # print("None")
            # if row[RACE_TIMES_COLUMN_INDEX] == "":
                # print("Empty String")
            # print(row[RACE_TIMES_COLUMN_INDEX])
            # print(row[RACE_DATES_COLUMN_INDEX])
        # except IndexError:
            # print("IndexError")
    
    run(signupSheet, resultsSheet)


if __name__ == "__main__":
    main()










