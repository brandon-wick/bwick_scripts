"""
Script to automate the download and installation of the latest Mac NB
(advanced w/KNIME) from build-download.schrodinger.com. A license file will need to be
manually installed. Designed to be an alternative to latest_schro.py.
Script implements functions from dmg.py and install_schrodinger.py
found in the buildbot-config repos. Modules from buildbot-config were not imported so
that the user does not need to clone any additional repos.

This script requires the following:

1. connected to the PDX VPN
2. a token.pick or credentials.json in the CWD that provides info for a google user that has
access to the Builds and Release calendar. See https://cloud.google.com/docs/authentication/getting-started
for obtaining credentials.json

Usage: python3 latest_mac_schro.py

TODO: automate adding license

"""

import argparse
import datetime as DT
import os
import pickle
import re
import requests
import shutil
import subprocess
import sys

from argparse import RawDescriptionHelpFormatter
from bs4 import BeautifulSoup
from contextlib import contextmanager
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


def parse_args():
    """
    Parse the command line arguments.

    :return args:  All script arguments
    :rtype args:  class:`argparse.Namespace`
    """

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description=__doc__)


    parser.add_argument(
        "platform",
        choices=["darwin", "linux", "windows"],
        metavar="platform",
        help="Release version in YY-Q format (eg. 21-1)")

    parser.add_argument(
        "bundle_type",
        choices=["academic", "general", "advanced"],
        metavar="bundle_type",
        help="type of bundle")

    parser.add_argument(
        "build_type",
        choices=["NB", "OB"],
        metavar="build_type",
        help="Type of build: Official build or Nightly Build")

    parser.add_argument(
        "-build",
        dest="build_id",
        metavar="build",
        help="build id in ### format (eg. 012, 105)")

    parser.add_argument(
        "-release",
        metavar="release",
        help="Release version in YY-Q format (eg. 21-1)")

    args = parser.parse_args()

    # Verify release argument is in correct format
    if args.release:
        if not re.search('^[2][0-9]-[1-4]$', args.release):
            parser.error('Incorrect release given')

    # Verify build_id argument is in correct format
    if args.build_id:
        if not re.search('^[0-9][0-9][0-9]$', args.build_id):
            parser.error('Incorrect build id given')

    return args

def create_clean_dirs(*directories):
    """
    Creates new directories. Also removes any pre-existing
    directory with the same name

    param tuple(str) directories: name of directories
    """
    dirs = list(directories)
    for dir in dirs:
        if os.path.exists(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)


def darwin_install(release, dmg_file_path, target_dir):
    """
    Sets up the directories needed and runs Darwin installer in the given
    target directory.

    Extracts "Payload" from each pkg file in installer_tmpdir and pipes it to
    cpio.

    :param str release: Latest release.
    :param str dmg_location: Path to schrodinger dmg file.
    :param str target_dir: Path to installation target directory.
    """
    installer_tmpdir = os.path.expanduser("~") + "/installer_tmpdir"
    app_dir = f"/Applications/SchrodingerSuites{release}"
    create_clean_dirs(installer_tmpdir, target_dir, app_dir)
    extract_bundle(dmg_file_path, installer_tmpdir)

    for file_path in os.listdir(installer_tmpdir):
        if os.path.splitext(file_path)[1] != '.pkg':
            continue
        payload = os.path.join(file_path, 'Payload')

        # Equivalent of "gunzip -c $payload | cpio -i"
        gunzip_cmd = ['gunzip', '-c', payload]
        gunzip = subprocess.Popen(
            gunzip_cmd, cwd=installer_tmpdir, stdout=subprocess.PIPE)
        subprocess.check_call(
            ['cpio', '-i'], cwd=target_dir, stdin=gunzip.stdout)
        gunzip.wait()
        if gunzip.returncode != 0:
            raise subprocess.CalledProcessError(
                gunzip.returncode, gunzip_cmd, output=gunzip.stdout)

    # move .app files to /Applications/
    for file in os.listdir(target_dir):
        if os.path.splitext(file)[1] != ".app":
            continue
        shutil.move((target_dir + file), app_dir)

    shutil.rmtree(installer_tmpdir)


def download_file(url, target):
    """
    Use the stream interface of requests to download a file in chunks (without
    having to read the entire file into memory).

    :param str url: URL to download file from
    :param str target: Path to the target file being downloaded.
    """
    #remove previous .dmg file if one already exists
    if os.path.exists(target):
        print("Previous .dmg found, removing...")
        os.remove(target)

    # Download file using the stream interface from requests
    # (avoids reading the entire file into memory)
    print(f'Beginning download to {target}')
    resp = requests.get(url, stream=True)
    resp.raise_for_status()

    with open(target, mode='wb') as file_handle:
        for chunk in resp.iter_content(chunk_size=1024):
            if not chunk:
                # Filter out keep-alive chunks
                continue
            file_handle.write(chunk)
    print('Download complete')


def get_current_release():
    """
    Gets the current release version by looking 15 weeks ahead into the build and release calendar
    and examining the next release target.
    """
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

    current_release = "20" + events_result["items"][0]["summary"][:4]

    if len(events_result["items"]) == 0:
        print("No release targets detected")
        return False

    return current_release


def extract_bundle(bundle_path, destination):
    with mount_dmg(bundle_path) as mount_point:
        bundle_name = os.path.basename(bundle_path)
        pkg_path = os.path.join(mount_point,
                                os.path.splitext(bundle_name)[0] + '.pkg')
        subprocess.check_call(['xar', '-C', destination, '-xvf', pkg_path])


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



def get_build_info(base_url, build_type):
    """
    Retrieves the current release and the latest build-id that contains
    a Schrodinger w/KNIME installation.

    :param str base_url: base url of schrodinger build site
    :param str base_type: NB or OB
    :return str current_release: The current release passed on from
        get_current_release()
    :return str dmg_file: dmg file extension
    :return str latest_build: The latest build ID
    """
    current_release = get_current_release()

    # update URL and navigate to builds page
    URL = '/'.join([base_url, build_type, current_release])
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    # obtain all available builds and arrange in a list where latest build is first
    all_uls = soup.find_all('ul')
    builds_list = all_uls[1].text.split('\n')
    builds_list = [id.strip() for id in builds_list if 'build' in id]

    if int(builds_list[-1][6:9]) > int(builds_list[0][6:9]):
        builds_list = builds_list[::-1]

    # go through each build-id page (starting with the latest) and find the latest build id
    # with a schrodinger w/KNIME installation. Stop once one is found
    for page in builds_list:
        dmg_file = get_dmg_file(URL, page)
        latest_build = page
        if dmg_file:
            break

    return current_release, latest_build, dmg_file


def get_dmg_file(*url_bits):
    """
    Fetches the dmg file name by scraping for the
    advanced installers header and specifically filtering
    results so that the Mac installation w/ KNIME's
    href is left. It is then edited to obtain the file name.

    :param tuple(str) url_bits: url bits to contstruct the URL
        for the installers page
    :return str dmg_file: dmg file name
    """
    URL = '/'.join(list(url_bits))
    page = requests.get(URL)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, 'html.parser')

    # find the 'Advanced Installers' header and go to the ul under it.
    try:
        advanced_installer_header = soup.find('h3', text='Advanced Installers')
        advanced_installers = advanced_installer_header.find_next_sibling()
    except:
        print(f"No advanced installer found for {URL}, moving to next build")
        return None

    # search for mac w/KNIME installer and get the href
    Knime_installer = advanced_installers.find_all(
        lambda tag: (tag.name == 'a' and ("Mac" and "with" in tag.text)))

    dmg_file = ""

    if Knime_installer:
        dmg_file = Knime_installer[0]['href']
        dmg_file = dmg_file.split('/')[-1]

    return dmg_file


def get_local_build_version(local_suite_path):
    """
    Gets the content from version.txt found in the local suite directory

    :param str local_install_path: Path to local installation
    :return str build_version: contents of version.txt
    """
    version_file = local_suite_path + "version.txt"
    with open(version_file, 'r') as fh:
        build_version = fh.read()

    return build_version


def install_schrodinger_hosts(build_type, release, build_id, installation_dir):
    """
    Download latest schrodinger.hosts file and move it into the local installation
    """
    url = "http://build-download.schrodinger.com/generatehosts/generate_hosts_file"
    form_data = {"build_type": build_type, "release": release, "build_id": build_id}
    resp = requests.post(url, data=form_data, stream=True)
    resp.raise_for_status()

    with open("schrodinger.hosts", mode='w') as file_handle:
        file_handle.write(resp.text)

    print("installing schrodinger.hosts...")
    shutil.move("schrodinger.hosts", installation_dir)
    print("schroding.hosts successfully installed")


@contextmanager
def mount_dmg(dmg_path):
    if not sys.platform.startswith('darwin'):
        raise RuntimeError('Mounting .dmg files is only supported on MacOS')

    # Mount dmg and parse mount point from output
    cmd = [
        'hdiutil', 'attach', '-mountrandom', '/Volumes', '-nobrowse', dmg_path
    ]
    output = subprocess.check_output(cmd, universal_newlines=True)

    print(output)

    match = re.search(r'/Volumes/dmg\.[\d\w]+', output)
    if not match:
        raise RuntimeError(
            'Could not parse mount point\n\nCommand: {}\n\nOutput:\n\n{}'.
            format(subprocess.list2cmdline(cmd), output))
    mount_point = match.group(0)

    # Yield the mount point so we can do:
    #   "with mount_dmg(dmg_path) as mount_point"
    try:
        yield mount_point
    finally:
        # Unmount the dmg when the context is exited.
        subprocess.check_call(['hdiutil', 'detach', '-force', mount_point])


def uninstall(release):
    old_suite = f"/opt/schrodinger/suites{release}/"
    apps_dir = f"/Applications/SchrodingerSuites{release}"
    print(f"Removing {old_suite}...\nRemoving{apps_dir}")
    shutil.rmtree(old_suite)
    shutil.rmtree(apps_dir)


def main(*, platform, bundle_type, build_type, release, build_id):
    base_url = 'http://build-download.schrodinger.com'
    build_type = bundle_type
    current_release, latest_build, schro_dmg_file = get_build_info(
        base_url, build_type)
    local_install_dir = f'/opt/schrodinger/suites{current_release}/'
    download_url = '/'.join(
        [base_url, build_type, current_release, latest_build, schro_dmg_file])
    user_download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

    # If running as root, set download location to /tmp, otherwise set to user's directory
    if os.geteuid == 0:
        target = os.path.join('/tmp', schro_dmg_file)
    target = os.path.join(user_download_dir, schro_dmg_file)

    print(
        f"The current release is {current_release} and the latest build is {latest_build}. \nChecking for a local {current_release} installation..."
    )

    if os.path.isdir(local_install_dir):
        local_version = get_local_build_version(local_install_dir)
        print(f"Local installation found, version.txt shows: {local_version}")

        latest_build_final = format_buildID(latest_build)

        if current_release and latest_build_final in local_version:
            print(
                "You currently have the latest build available for the current release, no update necessary"
            )
            return
        else:
            print(
                "Local installation is out of date. Downloading latest NB...")
    else:
        print("No local installation found, downloading latest NB...")

    download_file(download_url, target)
    darwin_install(current_release, target, local_install_dir)
    install_schrodinger_hosts(build_type, current_release, latest_build,
                                local_install_dir)


if __name__ == "__main__":
    cmd_args = parse_args()

    build_type = cmd_args.build_type
    bundle_type = cmd_args.bundle_type
    build_id = cmd_args.build_id
    release = cmd_args.release
    platform = cmd_args.platform

    main(platform = platform,
        bundle_type = bundle_type,
        build_type = build_type,
        release = release,
        build_id = build_id)
