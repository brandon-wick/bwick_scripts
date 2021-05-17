"""
Script to automate the download and installation of the latest build
from build-download.schrodinger.com. A license file will need to be
manually installed. Designed to be an alternative to latest_schro.py.
Script implements functions from dmg.py and install_schrodinger.py
found in the buildbot-config repos. Modules from buildbot-config were
not imported so that the user does not need to clone any additional repos.

This script requires the following:

1. connected to the PDX VPN
2. a token.pickle or credentials.json in the CWD that provides info for a
google user that has access to the Builds and Release calendar. See
https://cloud.google.com/docs/authentication/getting-started
for obtaining credentials.json

Example usages:
python latest_build_installer.py academic NB -d
python latest_build_installer.py advanced OB -release 21-3 -knime
python latest_build_installer.py general OB -c /home/user/Downloads -i /scr/user
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
        metavar="/path/to/download/folder",
        default=None,
        help=
        "Download bundle to the specified directory. If not given the bundle is downloaded to the user's download"
    )

    parser.add_argument(
        "-i",
        dest="install_destination",
        metavar="/path/to/installation",
        default=None,
        help=
        "Install bundle to the specified directory. If not given the bundle is installed to the platform's default installation location"
    )

    parser.add_argument(
        "-d, --download_only",
        dest="download_only",
        action="store_true",
        help=
        "Download bundle only, no installation of bundle or schrodinger.hosts is performed."
    )

    parser.add_argument(
        "-r, --release",
        metavar="##-#",
        dest="release",
        help=
        "Release version in YY-Q format (eg. 21-1). If release is not specified, it is automatically fetched from the builds and release calendar"
    )

    parser.add_argument(
        "-knime",
        action="store_true",
        help=
        "include KNIME in schrodinger installation. Only available for General and Advanced bundles."
    )

    args = parser.parse_args()

    # Verify path to download destination exists if given
    if args.download_destination:
        if not os.path.exists(args.download_destination):
            parser.error(
                "The download destination given doesn't seem to exist. Please give a pre-existing path"
            )

    # Disable -i option for Windows
    if sys.platform.startswith("win32") and args.install_destination:
        parser.error('-i option is not available for Windows')

    # Verify release argument is in correct format
    if args.release:
        if not re.search('^[2][0-9]-[1-4]$', args.release):
            parser.error('Incorrect release given')
        args.release = "20" + args.release

    # Verify -knime is only given under appropriate conditions
    if args.knime and args.bundle_type in ["desres", "academic"]:
        parser.error(
            '-knime can only be passed when bundle_type is general or advanced'
        )
    if args.knime and not sys.platform.startswith("darwin"):
        parser.error('Incompatible platform, please remove the -knime option')

    return args


def create_clean_dirs(*directories):
    """
    Creates new directories. Also removes any pre-existing
    directory with the same name

    :param directories: Name of directories
    :type directories: tuple(str)
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

    :param url: URL to download file from
    :type url: str
    :param target: Path to the target file being downloaded.
    :type target: str
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
    Gets the current release version by looking 15 weeks ahead
    from the time of execution into the build & release calendar
    and examining the next release target.

    :return current_release: Current release in XXXX-X format
    :rtype current_release: str
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
            if not os.path.isfile(
                    os.path.join(os.getcwd(), 'credentials.json')):
                raise FileNotFoundError(
                    "credentials.json not found, please visit https://cloud.google.com/docs/authentication/getting-started"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Start google calendar
    service = build('calendar', 'v3', credentials=creds)

    # Times for events().list()
    now = DT.datetime.now().isoformat() + 'Z'  # 'Z' indicates UTC time
    fifteen_weeks_ahead = (
        DT.datetime.now() + DT.timedelta(weeks=15)).isoformat() + 'Z'

    # List of all events in the past week that contain "Release Target"
    events_result = service.events().list(
        calendarId=QA_calendar_id,
        timeMin=now,
        timeMax=fifteen_weeks_ahead,
        singleEvents=True,
        q="* Release Target").execute()

    current_release = "20" + events_result["items"][0]["summary"][:4]

    if len(events_result["items"]) == 0:
        print("No release targets detected")
        return False

    return current_release


def extract_bundle(bundle_path, destination):
    """
    Extract bundle from tar or zip or dmg into the specified directory.

    :param bundle_path: Path to bundle being extracted.
    :type bundle_path: str
    :param destination: Target directory for extracting files.
    :type destination: str
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
    formatted_buildID = ""
    if int(format1[6]) == 0:
        for i in range(len(build_id)):
            if i != 6:
                formatted_buildID = formatted_buildID + format1[i]

    if formatted_buildID == "":
        formatted_buildID = format1

    return formatted_buildID


def get_build_info(release, build_type, bundle_type, knime):
    """
    Retrieves the latest build-id for the given release
    and the bundle installer file name

    :param release: Release in XXXX-X format
    :type release: str
    :param build_type: NB or OB
    :type build_type: str
    :param bundle_type: Academic, general, advanced or desres
    :type current_release: str
    :param knime: Include knime installation if true
    :type knime: bool

    :return latest_build: The latest build ID
    :rtype latest_build: str
    :return bundle_name: Name of bundle installer passed from
        get_bundle_name()
    :rtype bundle_name: str
    """

    if sys.platform.startswith("win32"):
        platform = "Windows"
    elif sys.platform.startswith("darwin"):
        platform = "MacOSX"
    else:
        platform = "Linux"

    # update URL and navigate to builds page
    URL = '/'.join([BASE_URL, build_type, release])
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    # obtain all available builds and arrange the latest build first
    all_uls = soup.find_all('ul')
    builds_list = all_uls[1].text.split('\n')
    builds_list = [id.strip() for id in builds_list if 'build' in id]

    if int(builds_list[-1][6:9]) > int(builds_list[0][6:9]):
        builds_list = builds_list[::-1]

    # go through each build-id page (starting with the latest) and find
    # the latest build id. Stop once and available bundle is found
    print(
        f"Finding the latest available {bundle_type} build for {platform}...")
    for build_page in builds_list:
        bundle_name = get_bundle_name(release, build_type, build_page,
                                      bundle_type, platform, knime)
        latest_build = build_page
        if bundle_name:
            break
    print(f"Latest {bundle_type} build for {platform} is {latest_build}")

    return latest_build, bundle_name


def get_bundle_name(release, build_type, build_page, bundle_type, platform,
                    knime):
    """
    Fetches the bundle installer file name by scraping for the
    bundle type header and then finding the href to the requested installer.
    It is then edited to obtain the file name.

    :param build_page: The download page for each build ID in 'build-###'
        format
    :type build_page: str
    :param platform: Machine platform
    :type platform: str

    :return installer_file: Name of bundle installer
    :rtype installer_file: str
    """

    URL = '/'.join([BASE_URL, build_type, release, build_page])
    page = requests.get(URL)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, 'html.parser')

    # find the appropriate bundle type header and go to the ul under it.
    header = bundle_type.capitalize()
    if bundle_type.lower() == "desres":
        header = "Academic"

    # For the rare occasion that headers aren't updated on the build site
    try:
        bundle_type_header = soup.find('h3', text=f'{header} Installers')
        installers = bundle_type_header.find_next_sibling()
    except AttributeError:
        print(
            f"No {bundle_type} installers found for {URL}, moving to next build"
        )
        return None

    # filter out other platform installers
    filter_ = platform
    if bundle_type.lower() == "desres":
        filter_ = "DESRES"
    installers = installers.find_all(
        lambda tag: (tag.name == 'a' and filter_ in tag.text))

    # See if there is an available installer
    if len(installers) == 0:
        print(
            f"No {platform} {bundle_type} installer found for {URL}, moving to next build"
        )
        return None

    # Select the no KNIME installation if -knime is not passed
    if platform == "MacOSX" and not knime:
        installer = installers[1]
    else:
        installer = installers[0]

    installer_file = ""
    if installer:
        installer_file = installer['href']
        installer_file = installer_file.split('/')[-1]

    return installer_file


def get_local_build_version(local_installation_path):
    """
    Gets the content from version.txt found in the local schrodinger
    installation

    :param local_installation_path: Path to the local installation
    :type local_installation_path: str

    :return build_version: Contents of version.txt
    :rtype build_version: str
    """

    version_file = os.path.join(local_installation_path, "version.txt")
    with open(version_file, 'r') as fh:
        build_version = fh.read()

    return build_version


def install_schrodinger_bundle(release, bundle_installer, local_install_dir):
    install_tmpdir = os.path.join(local_install_dir, "install_tmpdir")
    create_clean_dirs(local_install_dir, install_tmpdir)
    extract_bundle(bundle_installer, install_tmpdir)

    if sys.platform.startswith('win32'):
        cmd = _get_windows_install_cmd(install_tmpdir, local_install_dir)
        _run_install_cmd(cmd, install_tmpdir)
    elif sys.platform.startswith('linux'):
        cmd = _get_linux_install_cmd(install_tmpdir, local_install_dir)
        _run_install_cmd(cmd, install_tmpdir)
    elif sys.platform.startswith('darwin'):
        _darwin_install(release, install_tmpdir, local_install_dir)
    else:
        raise RuntimeError(f'unsupported platform: {sys.platform()}')

    shutil.rmtree(install_tmpdir)


def _run_install_cmd(cmd, cwd):
    """
    Runs the specified command in the given working directory with the env
    variable SCHRODINGER_INSTALL_UNSUPPORTED_PLATFORMS set to "1".

    :param cmd: Command to execute.
    :type cmd: list
    :param cwd: Working directory for the command.
    :type cmd: str
    """

    print(f'Running {subprocess.list2cmdline(cmd)}')
    env = os.environ.copy()
    env['SCHRODINGER_INSTALL_UNSUPPORTED_PLATFORMS'] = '1'
    subprocess.check_call(cmd, cwd=cwd, stderr=subprocess.STDOUT, env=env)


def _get_windows_install_cmd(installer_dir, target_dir):
    setup_silent = os.path.join(installer_dir, 'setup-silent.exe')
    cmd = [
        setup_silent, '/interactive_mode:off', '/install',
        f"/installdir:'{target_dir}'", '/force'
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

    :param installer_dir: Path to directory containing pkg files.
    :type installer_dir: str
    :param target_dir: Path to installation target directory.
    :type target_dir: str
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


def install_schrodinger_hosts(build_type, release, build_id, installation_dir):
    """
    Download latest schrodinger.hosts file and move it into the
    local installation
    """

    url = "http://build-download.schrodinger.com/generatehosts/generate_hosts_file"
    form_data = {
        "build_type": build_type,
        "release": release,
        "build_id": build_id
    }
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
            f'Could not parse mount point\n\nCommand: {subprocess.list2cmdline(cmd)}\n\nOutput:\n\n{output}'
        )
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


def main(*,
         bundle_type,
         build_type,
         release,
         knime=False,
         download_only=False,
         download_dest=None,
         install_dest=None):

    # obtain all relevant build info for constructing the download url
    if not release:
        release = get_current_release()

    latest_build, bundle_name = get_build_info(release, build_type,
                                               bundle_type, knime)
    download_url = '/'.join(
        [BASE_URL, build_type, release, latest_build, bundle_name])

    # default paths for download and local installation directories
    user_down_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

    if sys.platform.startswith('win32'):
        user_down_dir = os.path.join(os.getenv('USERPROFILE'), 'Downloads')
        local_install_dir = f'C:\\Program Files\\Schrodinger{release}'
    elif sys.platform.startswith('darwin'):
        local_install_dir = f"/opt/schrodinger/suites{release}"
    elif sys.platform.startswith('linux'):
        local_install_dir = f"/scr/schrodinger{release}"

    bundle_path = os.path.join(user_down_dir, bundle_name)

    # Use installation path given by -i if passed
    if install_dest:
        local_install_dir = os.path.join(install_dest, f"suites{release}")

    # Use download path given by -c if passed
    if download_dest:
        bundle_path = os.path.join(download_dest, bundle_name)

    print(f"Checking for a local {release} installation...")
    if os.path.isdir(local_install_dir):
        local_version = get_local_build_version(local_install_dir)
        print(f"Local installation found, version.txt shows:\n{local_version}")

        if release and format_buildID(latest_build) in local_version:
            print("You currently have the latest build, no update necessary")
            return
        else:
            print("Local installation is out of date")
            uninstall(release, local_install_dir)
    else:
        print("No local installation found, downloading latest build...")

    download_file(download_url, bundle_path)
    if download_only:
        print("Download-only enabled, stopping execution")
        return

    install_schrodinger_bundle(release, bundle_path, local_install_dir)
    install_schrodinger_hosts(build_type, release, latest_build,
                              local_install_dir)


if __name__ == "__main__":
    cmd_args = parse_args()
    download_dest = cmd_args.download_destination
    install_dest = cmd_args.install_destination
    build_type = cmd_args.build_type
    bundle_type = cmd_args.bundle_type
    knime = cmd_args.knime
    release = cmd_args.release
    download_only = cmd_args.download_only

    main(
        bundle_type=bundle_type,
        build_type=build_type,
        download_dest=download_dest,
        install_dest=install_dest,
        release=release,
        knime=knime,
        download_only=download_only)
