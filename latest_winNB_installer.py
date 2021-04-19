"""
Script that installs the latest NB for windows through the use
of the silent installers/uninstallers that come with the schrodinger
bundle. Script assumes you are connected to the PDX VPN

if you intend have the script automatically fetch the current release and do not
have a credentials.json please refer to
https://developers.google.com/workspace/guides/create-credentials

usage: python \\path\\to\\latest_winNB_installer.py
"""

import argparse
import datetime as DT
import os
import pickle
import re
import subprocess

from argparse import RawDescriptionHelpFormatter

def parse_args():
    """
    Parse the command line arguments.

    :return args:  All script arguments
    :rtype args:  class:`argparse.Namespace`
    """

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description=__doc__)

    parser.add_argument(
        "-release",
        metavar="release",
        help="Release version in YY-Q format (eg. 21-1)")

    args = parser.parse_args()

    # Verify release argument is in correct format
    if args.release:
        if not re.search('^[2][0-9]-[1-4]$', args.release):
            parser.error('Incorrect release given')

    return args

def format_buildID(build_id):
    # modify latest_build so that "build-###" becomes "Build ###"
    format1 = build_id.capitalize().replace("-", " ")

    # modify latest_build so that "build-0##" becomes "Build ##"
    latest_build_final = ""
    if int(format1[6]) == 0:
        for i in range(len(build_id)):
            if i != 6:
                latest_build_final = latest_build_final + format1[i]

    if latest_build_final == "":
        latest_build_final = format1

    return latest_build_final


def get_current_release():
    """
    Gets the current release version by looking 15 weeks ahead into the build and release calendar
    and examining the next release target.
    """
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    QA_calendar_id = "schrodinger.com_cl2hf12t7dim7s894gda2l9pa0@group.calendar.google.com"
    creds = None

    # Token
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
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Start google calendar
    service = build('calendar', 'v3', credentials=creds)

    # Times for events().list()
    now = DT.datetime.now().isoformat() + 'Z' # 'Z' indicates UTC time
    fifteen_weeks_ahead = (DT.datetime.now() + DT.timedelta(weeks=15)).isoformat() + 'Z'

    # List of all events in the past week that have "Release Target" in its name
    events_result = service.events().list(calendarId=QA_calendar_id, timeMin=now,
                                         timeMax=fifteen_weeks_ahead, singleEvents=True, q="* Release Target").execute()

    current_release = events_result["items"][0]["summary"][:4]

    if len(events_result["items"]) == 0:
        print("No release targets detected")
        return False

    return current_release


def get_local_build_version(local_suite_path):
    """
    Gets the content from version.txt found in the local suite directory

    :param local_suite_path: Path to local installation
    :param type: str

    :return build_version: contents of version.txt
    :return type: str
    """

    version_file = local_suite_path + "\\version.txt"
    with open(version_file, 'r') as fh:
        build_version = fh.read()

    return build_version


def main(*, release):
    if not release:
        release = get_current_release()

    local_installation_path = f"C:\\Program Files\\Schrodinger20{release}"
    installers_path = f"M:\\installers\\NB\\20{release}"
    all_NBs = os.listdir(installers_path)

    # Get the latest available NB and its setup.exe path
    for NB in all_NBs[::-1]:
        setup_script = f"{installers_path}\\{NB}\\Windows-x64\\setup-silent.exe"
        if os.path.isfile(setup_script):
            latest_NB = format_buildID(NB)
            break

    # Check for a local up-to-date installation
    if os.path.isdir(local_installation_path):
        local_version = get_local_build_version(local_installation_path)

        if latest_NB in local_version:
            return

        else:
            uninstaller = f"{local_installation_path}\\installer\\uninstall-silent.exe"
            subprocess.run([uninstaller, "/interactive_mode:off"])

    subprocess.run([
        setup_script, "/interactive_mode:off", "/install", "/knimeshortcut:no"
    ])


if __name__ == "__main__":
    cmd_args = parse_args()
    main(release=cmd_args.release)
