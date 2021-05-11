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
import tarfile
import zipfile

from argparse import RawDescriptionHelpFormatter
from bs4 import BeautifulSoup
from contextlib import contextmanager

BASE_URL = 'http://build-download.schrodinger.com'


def parse_args():
    """
    Parse the command line arguments.

    :return args:  All script arguments
    :rtype args:  class:`argparse.Namespace`
    """

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description=__doc__)

    parser.add_argument(
        "bundle_type",
        choices=["academic", "general", "advanced", "desres"],
        metavar="bundle_type",
        help="type of bundle")

    parser.add_argument(
        "build_type",
        choices=["NB", "OB"],
        metavar="build_type",
        help="Type of build: Official build or Nightly Build")

    parser.add_argument(
        "-c",
        dest="download_destination",
        metavar="dest",
        help="Download bundle to the specified directory. If not given the bundle is downloaded to the user's download")

    parser.add_argument(
        "-d, --download",
        dest="download_only",
        action="store_true",
        help="Download bundle only, no installation of bundle or schrodinger.hosts is performed.")

    parser.add_argument(
        "-release",
        metavar="release",
        help="Release version in YY-Q format (eg. 21-1). If release is not specified, it is automatically fetched from the builds and release calendar")

    parser.add_argument(
        "-knime",
        action="store_true",
        help="include KNIME in schrodinger installation")

    args = parser.parse_args()

    # Verify path download destination exists if given
    if not os.path.exists(args.download_destination):
        parser.error("The download destination given doesn't seem to exist. Please give a pre-existing path")

    # Verify release argument is in correct format
    if args.release:
        if not re.search('^[2][0-9]-[1-4]$', args.release):
            parser.error('Incorrect release given')
        args.release = "20" + args.release

    # Verify -knime is only given under appropriate conditions
    if args.knime and args.bundle_type in ["desres", "academic"]:
        parser.error('-knime can only be passed when bundle_type is general or advanced')
    if args.knime and not sys.platform.startswith("darwin"):
        parser.error('Incompatible platform, please remove the -knime option')

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


def download_file(url, target):
    """
    Use the stream interface of requests to download a file in chunks (without
    having to read the entire file into memory).

    :param str url: URL to download file from
    :param str target: Path to the target file being downloaded.
    """
    # remove previous schrodinger installer if one already exists
    if os.path.exists(target):
        print("Previous installer found, removing...")
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
    Gets the current release version by looking 15 weeks ahead into the build & release calendar
    and examining the next release target.

    :return dmg_file: current release in XXXX-X format
    :return type: str
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

    current_release = "20" + events_result["items"][0]["summary"][:4]

    if len(events_result["items"]) == 0:
        print("No release targets detected")
        return False

    return current_release


def extract_bundle(bundle_path, destination):
    """
    Extract bundle from tar or zip or dmg into the specified directory.

    :param str platform: Platform name, must be in buildinfo.Platforms
    :param str bundle_path: Path to bundle being extracted.
    :param str destination: Target directory for extracting files.
    """
    print(f"Extracting {bundle_path} to {destination}")

    if sys.platform.startswith('win32'):
        with zipfile.ZipFile(bundle_path, 'r') as zip_archive:
            zip_archive.extractall(path=destination)
    elif sys.platform.startswith('linux'):
        with tarfile.open(name=bundle_path, mode='r') as tar:
            tar.extractall(path=destination)
    elif sys.platform.startswith('darwin'):
        with mount_dmg(bundle_path) as mount_point:
            bundle_name = os.path.basename(bundle_path)
            pkg_path = os.path.join(mount_point,
                                    os.path.splitext(bundle_name)[0] + '.pkg')
            subprocess.check_call(['xar', '-C', destination, '-xvf', pkg_path])
        return
    else:
        raise RuntimeError(f'Unsupported platform: {sys.platform}')

    # For tar and zip, extracted files go in a subdir and need to be moved to
    # the destination directory
    dirname = os.path.join(destination,
                           os.path.splitext(os.path.basename(bundle_path))[0])
    try:
        for name in os.listdir(dirname):
            dest = os.path.join(destination, name)
            if os.path.exists(dest):
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            src = os.path.join(dirname, name)
            print(f"Moving {os.path.abspath(src)} to {os.path.abspath(dest)}")
            os.rename(src, dest)
    finally:
        shutil.rmtree(dirname)


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


def get_build_info(release, build_type, bundle_type, knime):
    """
    Retrieves the latest build-id that contains
    a Schrodinger w/KNIME installation.

    :param str base_url: base url of schrodinger build site
    :param str base_type: NB or OB
    :return str current_release: The current release passed on from
        get_current_release()
    :return str dmg_file: dmg file extension
    :return str latest_build: The latest build ID
    """

    # Get platform
    if sys.platform.startswith("linux"):
        platform = "Linux"
    elif sys.platform.startswith("darwin"):
        platform = "MacOSX"
    else:
        platform = "Windows"

    # update URL and navigate to builds page
    URL = '/'.join([BASE_URL, build_type, release])
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    # obtain all available builds and arrange in a list where latest build is first
    all_uls = soup.find_all('ul')
    builds_list = all_uls[1].text.split('\n')
    builds_list = [id.strip() for id in builds_list if 'build' in id]

    if int(builds_list[-1][6:9]) > int(builds_list[0][6:9]):
        builds_list = builds_list[::-1]

    # go through each build-id page (starting with the latest) and find the latest build id
    # Stop once and available bundle is found
    for build_page in builds_list:
        bundle_name = get_bundle_name(URL, build_page, bundle_type, platform, knime)
        latest_build = build_page
        if bundle_name:
            break

    return latest_build, bundle_name


def get_bundle_name(URL, build, bundle_type, platform, knime):
    """
    Fetches the dmg file name by scraping for the
    advanced installers header and specifically filtering
    results so that the Mac installation w/ KNIME's
    href is left. It is then edited to obtain the file name.

    :param tuple(str) url_bits: url bits to contstruct the URL
        for the installers page
    :return str dmg_file: dmg file name
    """
    URL = '/'.join([URL, build])
    page = requests.get(URL)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, 'html.parser')

    # find the appropriate bundle type header and go to the ul under it.

    header = bundle_type.capitalize()
    if bundle_type.lower() == "desres":
        header = "Academic"
    try:
        bundle_type_header = soup.find('h3', text=f'{header} Installers')
        installers = bundle_type_header.find_next_sibling()
    except:
        print(f"No {bundle_type} installer found for {URL}, moving to next build")
        return None

    # filter out other platform installers
    filter_ = platform
    if bundle_type.lower() == "desres":
        filter_ = "DESRES"
    installers = installers.find_all(
        lambda tag: (tag.name == 'a' and filter_ in tag.text))

    installer = installers[0]
    # Select KNIME installation if -knime was passed
    if platform == "MacOSX" and not knime:
        installer = installers[1]

    installer_file = ""

    if installer:
        installer_file = installer['href']
        installer_file = installer_file.split('/')[-1]

    return installer_file


def get_local_build_version(local_suite_path):
    """
    Gets the content from version.txt found in the local suite directory

    :param str local_install_path: Path to local installation
    :return str build_version: contents of version.txt
    """
    version_file = local_suite_path + "/version.txt"
    with open(version_file, 'r') as fh:
        build_version = fh.read()

    return build_version


def move_to_final(source, dest):
    for file_ in os.listdir(source):
        shutil.move(os.path.join(source, file_), dest)


def install_schrodinger_bundle(release, bundle_installer, local_install_dir):
    install_tempdir = local_install_dir + "/installer_tmpdir"
    create_clean_dirs(install_tempdir)
    extract_bundle(bundle_installer, install_tempdir)

    if sys.platform.startswith('win32'):
        cmd = _get_windows_install_cmd(install_tempdir, install_tempdir)
        _run_install_cmd(cmd, install_tempdir)
        move_to_final(install_tempdir, local_install_dir)
    elif sys.platform.startswith('linux'):
        cmd = _get_linux_install_cmd(install_tempdir, install_tempdir)
        _run_install_cmd(cmd, install_tempdir)
        move_to_final(install_tempdir, local_install_dir)
    elif sys.platform.startswith('darwin'):
        _darwin_install(release, install_tempdir, local_install_dir)
    else:
        raise RuntimeError('unsupported platform: {}'.format(sys.platform()))

    shutil.rmtree(install_tempdir)


def _run_install_cmd(cmd, cwd):
    """
    Runs the specified command in the given working directory with the env
    variable SCHRODINGER_INSTALL_UNSUPPORTED_PLATFORMS set to "1".

    :param list cmd: Command to execute.
    :param str cwd: Working directory for the command.
    """
    print(f'Running {subprocess.list2cmdline(cmd)}')
    env = os.environ.copy()
    env['SCHRODINGER_INSTALL_UNSUPPORTED_PLATFORMS'] = '1'
    subprocess.check_call(cmd, cwd=cwd, stderr=subprocess.STDOUT, env=env)


def _get_windows_install_cmd(installer_dir, target_dir):
    setup_silent = os.path.join(installer_dir, 'setup-silent.exe')
    cmd = [
        setup_silent, '/interactive_mode:off', '/install',
        "/installdir:'{}'".format(target_dir), '/force'
    ]
    return cmd


def _get_linux_install_cmd(installer_dir, target_dir):
    cmd = [
        "./INSTALL", "-b", "-d", installer_dir, "-t",
        os.path.join(target_dir, "thirdparty"), "-s", target_dir, "-k", "/scr",
        "--allow_deprecated"
    ]
    cmd.extend([d for d in os.listdir(installer_dir) if d.endswith(".tar.gz")])
    return cmd


def _darwin_install(release, installer_dir, target_dir):
    """
    Runs Darwin installer in the given target directory.

    Extracts "Payload" from each pkg file in installer_dir and pipes it to
    cpio.

    :param str installer_dir: Path to directory containing pkg files.
    :param str target_dir: Path to installation target directory.
    """

    app_dir = f"/Applications/SchrodingerSuites{release}"
    create_clean_dirs(app_dir)
    target_dir = target_dir + "/"

    for file_path in os.listdir(installer_dir):
        if os.path.splitext(file_path)[1] != '.pkg':
            continue
        payload = os.path.join(file_path, 'Payload')
        print(f'Extracting payload from {payload}')
        # Equivalent of "gunzip -c $payload | cpio -i"
        gunzip_cmd = ['gunzip', '-c', payload]
        gunzip = subprocess.Popen(
            gunzip_cmd, cwd=installer_dir, stdout=subprocess.PIPE)
        subprocess.check_call(
            ['cpio', '-i'], cwd=target_dir, stdin=gunzip.stdout)
        gunzip.wait()
        if gunzip.returncode != 0:
            raise subprocess.CalledProcessError(
                gunzip.returncode, gunzip_cmd, output=gunzip.stdout)

    # move .app files to /Applications/
    for file_ in os.listdir(target_dir):
        if os.path.splitext(file_)[1] != ".app":
            continue
        shutil.move((target_dir + file_), app_dir)


def setup_dirs(release):
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    if sys.platform.startswith('win32'):
        download_dir = os.path.join(os.getenv('USERPROFILE'), 'Downloads')
        local_install_dir = f'C:\\Program Files\\Schrodinger{release}'
    elif sys.platform.startswith('darwin'):
        local_install_dir = f"/opt/schrodinger/suites{release}"
    else:
        local_install_dir = f"/scr/schrodinger{release}"


    return download_dir, local_install_dir


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

    hosts_path = os.path.join(installation_dir, "schrodinger.hosts")

    # remove stock schrodinger.hosts file if one exists
    if os.path.isfile(hosts_path):
        os.remove(hosts_path)

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


def uninstall(release, installation_dir):

    if sys.platform.startswith('win32'):
        uninstaller = f"{installation_dir}\\installer\\uninstall-silent.exe"
        subprocess.run([uninstaller, "/interactive_mode:off"])

    print(f"Removing {installation_dir}...")
    shutil.rmtree(installation_dir)
    if sys.platform.startswith('darwin'):
        apps_dir = f"/Applications/SchrodingerSuites{release}"
        print(f"Removing {apps_dir}")
        shutil.rmtree(apps_dir)


def main(*, bundle_type, build_type, release, knime, download_only=False, download_dest=None):

    # obtain all relevant build info for constructing the download url
    if not release:
        release = get_current_release()

    latest_build, bundle_name = get_build_info(release, build_type, bundle_type, knime)
    download_url = '/'.join(
        [BASE_URL, build_type, release, latest_build, bundle_name])

    # get path for download and local installation directory
    download_dir, local_install_dir = setup_dirs(release)
    bundle_path = os.path.join(download_dir, bundle_name)
    if download_dest:
        bundle_path = os.path.join(download_dest, bundle_name)

    print(
        f"The latest build for {release} is {latest_build}. \nChecking for a local {release} installation..."
    )

    if os.path.isdir(local_install_dir):
        local_version = get_local_build_version(local_install_dir)
        print(f"Local installation found, version.txt shows: {local_version}")

        if release and format_buildID(latest_build) in local_version:
            print(
                "You currently have the latest build available for the given release, no update necessary"
            )
            return
        else:
            print("Local installation is out of date")
            uninstall(release, local_install_dir)
    else:
        print("No local installation found, downloading latest NB...")

    download_file(download_url, bundle_path)
    if download_only:
        return

    install_schrodinger_bundle(release, bundle_path, local_install_dir)
    install_schrodinger_hosts(build_type, release, latest_build, local_install_dir)


if __name__ == "__main__":
    cmd_args = parse_args()
    download_dest = cmd_args.download_destination
    build_type = cmd_args.build_type
    bundle_type = cmd_args.bundle_type
    knime = cmd_args.knime
    release = cmd_args.release
    download_only= cmd_args.download_only

    main(bundle_type=bundle_type, build_type=build_type, download_dest=download_dest, release=release, knime=knime, download_only=download_only)