# RaceManager
Python tool to help manage Ori and the Blind Forest tournament qualifier races by interfacing with Google Sheets.

# Setup
Download the files race.py and config.json into the same directory. For testing, please use the google sheets in the following locations:

Ori Tournaments/2019 All Skills Tournament/Organizers/TEST

Feel free to create new sheets to test more stuff. If you do, you'll need to update their respective "id" fields within config.json. The sheet ID can be obtained from the spreadsheet URL:

https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0

Modifying config fields may cause undefined behavior. I've sorted the signup sheet by participants. A different sort may cause undefined behavior.

You will need a file called credentials.json placed in the same directory as race.py. I got mine from the Google sheets quickstart app but I'm not totally sure if it contains sensitive information in it anywhere so it's not in the repository. I suspect there's a better way to go about this part but I don't really understand what's actually going on.

You will also need the Google API libraries for Python. I followed the instructions here: https://developers.google.com/sheets/api/quickstart/python, you can follow this up through step 2 and you should be good. Following this will also give you a credentials.json file.

# Usage
Currently there is only basic command line functionality. Launch via CLI and follow the prompts.

All names are expected to be SRL names, and names are case sensitive. The initial list of names should
be directly copied and pasted from the ".entrants" command on SRL. This will be a string that looks
something like:

"name1 | name2 | name3 | name4"

It doesn't matter if any of the runners have readied up or not, the "(Ready)" will be removed from their names.
This list will include the race organizer, who is not participating in the race. The first thing the program
will do is ask you who the organizer is so that it excludes them from the list of entrants. Runners who have
already completed the maximum number of qualifier runs will be automatically excluded, and the program will not
ask you to record their results.

When entering times for runners, SRL names should again be used. Times must be entered in one of the following formats:

- H:MM:SS
- MM:SS

Entering "FF" will mark a forfeit for that runner.

If hours are omitted they are assumed to be zero, so "35:12" would become "0:35:12" before being entered.
Once all runners have a time entered, the program will display the list of runners and their times and ask you
to confirm that it is correct. Once confirmed, data will be updated.

If at any point during this process you need to reenter a time, you can do that by simply specifying the runner's
name a second time. The program will update with the new time.

In order for this to work on the actual tournament spreadsheets we need to update the sheet IDs in the code. For now it will be
set to testing sheets based on the All Skills sheets and if this all goes well it will be updated for ACNR.


# Assumptions
- "Preferred Name" on the signup sheet exactly matches the runner's name listed on the qualifier results sheet.
- The signup sheet and qualifier sheet follows the same format as the current All Skills sheet, including column indices and ordering.
- The list of entrants contains exactly one "organizer" who is not participating as a racer.
- All runners will finish their runs in less than 10 hours.

# Known issues
- List of entrants in the SRL race isn't validated against SRL names of people registered for the tournament so unregistered entrants will not work.
- If someone's name on the qualifier results sheet does not _exactly_ match their preferred name in the signup sheet, the program will not find them.
- Forfeits are not currently marked as red cells.
