"""
Script designed to automate the process of download testing when
given an installer type and release version. This script has the
following requirements:

1. Must run on linux and have /nfs/installers mounted
2. Must have chrome browser and chromedriver somehwere in your $PATH
(To install chromedriver, run script and see link in error message)

Usage: python3 download_testing_v2.py academic 21-1
"""
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

import argparse
import hashlib
import os
import sys
import time


def md5(fname):
    """
    Calculate the md5checksum of file given.

    :return: Md5checksum
    :rtype: class`hashlib.md5`
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def parse_args():
    """
    Parse the command line arguments.

    :return:  All script arguments
    :rtype:  class:`argparse.Namespace`
    """

    parser = argparse.ArgumentParser(
        description='perform download testing')

    parser.add_argument(
        "installer",
        help="Type of installer (academic, commercial, non-commercial, or advanced)")

    parser.add_argument(
        "release",
        help="Release version (eg. 21-1)")

    args = parser.parse_args()

    return args

def main(installer, release):
    URL = "https://www.schrodinger.com/downloads/releases"

    accounts = {"Non-commercial":{"user":"academic@schrodinger.com", "pass":"password"},
                "Commercial":{"user":"commercial@schrodinger.com", "pass":"password"},
                "Restricted":{"user":"advanced@sch-gsuite.services", "pass":"Te5t1ng!"}}

    chromeOptions = webdriver.ChromeOptions()
    prefs = {'safebrowsing.enabled': 'false'}
    chromeOptions.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chromeOptions)
    driver.get(URL)

    username = driver.find_element_by_id("edit-name")
    password = driver.find_element_by_id("edit-pass")

    if installer == "academic":

        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        download_files = [f"Maestro_20{release}_Linux-x86_64_Academic.tar",
                          f"Maestro_20{release}_Windows-x64_Academic.zip",
                          f"Maestro_20{release}_MacOSX_Academic.dmg"]

        # Remove any previous installers (of the same release) in user's download folder
        for file_to_delete in download_files:
            file_path = os.path.join(download_dir, file_to_delete)
            if os.path.isfile(file_to_delete):
                os.remove(file_to_delete)

        # Login
        username.send_keys(accounts["Non-commercial"]["user"])
        password.send_keys(accounts["Non-commercial"]["pass"])
        driver.find_element_by_id("edit-submit").click()

        # Select release
        release_dropdown = Select(driver.find_element_by_id(f"edit-release"))
        release_dropdown.select_by_visible_text(f"Release 20{release}")

        # Go to free maestro tab
        driver.find_element_by_link_text('Free Maestro').click()

        # Download Linux
        driver.refresh()
        driver.find_element_by_id("edit-linux").click()
        driver.find_element_by_id("edit-freemaestro-acknowledge").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        time.sleep(3)
        driver.back()

        # Download Windows
        driver.refresh()
        driver.find_element_by_id("edit-windows-64-bit").click()
        driver.find_element_by_id("edit-freemaestro-acknowledge").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        time.sleep(3)
        driver.back()

        # Download Mac
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        driver.find_element_by_id("edit-freemaestro-acknowledge").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        time.sleep(3)
        driver.back()

        for fname in download_files:
            while not os.path.exists(os.path.join(download_dir, fname)):
                time.sleep(60)

        driver.quit()

        # Calculate and compare checksums
        print(installer.capitalize() + " md5checksums")
        for fname in download_files:
            installer_path = os.path.join(download_dir, fname)
            ref_path = ref_path = os.path.join("/nfs/installers/releases", f"suite20{release}", "bundles", fname)
            installer_checksum = md5(installer_path)
            ref_checksum = md5(ref_path)

            if installer_checksum == ref_checksum:
                print("congrats, both checksums match!")
            else:
                print("checksums DO NOT match")
            print(f"REFERENCE {ref_checksum} {ref_path}\n{installer} {installer_checksum} {installer_path}")

    elif installer == "non-commercial":

        download_files = ["Schrodinger_Suites_2021-1_Linux-x86_64.tar",
                          "Schrodinger_Suites_2021-1_Windows-x64.zip",
                          "Schrodinger_Suites_2021-1_MacOSX.dmg",
                          "Schrodinger_Suites_2021-1_KNIME_MacOSX.dmg"]

        for file_to_delete in download_files:
            if os.path.isfile(file_to_delete):
                os.remove(file_to_delete)

        # Login
        username.send_keys(accounts["Non-commercial"]["user"])
        password.send_keys(accounts["Non-commercial"]["pass"])
        driver.find_element_by_id("edit-submit").click()

        # Select release
        release_dropdown = Select(driver.find_element_by_id(f"edit-release"))
        release_dropdown.select_by_visible_text(f"Release 20{release}")

        # Download Linux
        driver.refresh()
        driver.find_element_by_id("edit-linux").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Windows
        driver.refresh()
        driver.find_element_by_id("edit-windows-64-bit").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/o KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("without KNIME")
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/ KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("with KNIME")
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()

        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        for fname in download_files:
            while not os.path.exists(os.path.join(download_dir, fname)):
                time.sleep(60)

        driver.quit()

        # Calculate and compare checksums
        print(installer.capitalize() + " md5checksums")
        for fname in download_files:
            installer_path = os.path.join(download_dir, fname)
            ref_path = ref_path = os.path.join("/nfs/installers/releases", f"suite20{release}", "bundles", fname)
            installer_checksum = md5(installer_path)
            ref_checksum = md5(ref_path)

            if installer_checksum == ref_checksum:
                print("Congrats, both checksums match!")
            else:
                print("checksums DO NOT match")
            print(f"REFERENCE {ref_checksum} {ref_path}\n{installer} {installer_checksum} {installer_path}")

    elif installer == "commercial":

        download_files = ["Schrodinger_Suites_2021-1_Linux-x86_64.tar",
                          "Schrodinger_Suites_2021-1_Windows-x64.zip",
                          "Schrodinger_Suites_2021-1_MacOSX.dmg",
                          "Schrodinger_Suites_2021-1_KNIME_MacOSX.dmg"]

        for file_to_delete in download_files:
            if os.path.isfile(file_to_delete):
                os.remove(file_to_delete)

        # Login
        username.send_keys(accounts["Commercial"]["user"])
        password.send_keys(accounts["Commercial"]["pass"])
        driver.find_element_by_id("edit-submit").click()

        # Select release
        release_dropdown = Select(driver.find_element_by_id(f"edit-release"))
        release_dropdown.select_by_visible_text(f"Release 20{release}")

        # Download Linux
        driver.refresh()
        driver.find_element_by_id("edit-linux").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Windows
        driver.refresh()
        driver.find_element_by_id("edit-windows-64-bit").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/o KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("without KNIME")
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/ KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("with KNIME")
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()

        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        for fname in download_files:
            while not os.path.exists(os.path.join(download_dir, fname)):
                time.sleep(60)

        driver.quit()

        # Calculate and compare checksums
        print(installer.capitalize() + " md5checksums")
        for fname in download_files:
            installer_path = os.path.join(download_dir, fname)
            ref_path = ref_path = os.path.join("/nfs/installers/releases", f"suite20{release}", "bundles", fname)
            installer_checksum = md5(installer_path)
            ref_checksum = md5(ref_path)

            if installer_checksum == ref_checksum:
                print("congrats, both checksums match!")
            else:
                print("checksums DO NOT match")
            print(f"REFERENCE {ref_checksum} {ref_path}\n{installer} {installer_checksum} {installer_path}")

    elif installer == "advanced":
        download_files = ["Schrodinger_Suites_2021-1_Advanced_Linux-x86_64.tar",
                          "Schrodinger_Suites_2021-1_Advanced_Windows-x64.zip",
                          "Schrodinger_Suites_2021-1_Advanced_MacOSX.dmg",
                          "Schrodinger_Suites_2021-1_Advanced_KNIME_MacOSX.dmg"]

        for file_to_delete in download_files:
            if os.path.isfile(file_to_delete):
                os.remove(file_to_delete)

        # Login
        username.send_keys(accounts["Restricted"]["user"])
        password.send_keys(accounts["Restricted"]["pass"])
        driver.find_element_by_id("edit-submit").click()

        # Select release
        release_dropdown = Select(driver.find_element_by_id(f"edit-release"))
        release_dropdown.select_by_visible_text(f"Release 20{release}")

        # Download Linux
        driver.refresh()
        driver.find_element_by_id("edit-linux").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Windows
        driver.refresh()
        driver.find_element_by_id("edit-windows-64-bit").click()
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/o KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("without KNIME")
        driver.find_element_by_id("edit-submit").click()
        driver.back()

        # Download Mac w/ KNIME
        driver.refresh()
        driver.find_element_by_id("edit-mac").click()
        mac_dropdown = Select(driver.find_element_by_id("edit-mac-downloads"))
        mac_dropdown.select_by_visible_text("with KNIME")
        driver.find_element_by_id("edit-eula").click()
        driver.find_element_by_id("edit-submit").click()

        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        for fname in download_files:
            while not os.path.exists(os.path.join(download_dir, fname)):
                time.sleep(60)

        driver.quit()

        # Calculate and compare checksums
        print(installer.capitalize() + " md5checksums")
        for fname in download_files:
            installer_path = os.path.join(download_dir, fname)
            ref_path = ref_path = os.path.join("/nfs/installers/releases", f"suite20{release}", "bundles", fname)
            installer_checksum = md5(installer_path)
            ref_checksum = md5(ref_path)

            if installer_checksum == ref_checksum:
                print("congrats, both checksums match!")
            else:
                print("checksums DO NOT match")
            print(f"REFERENCE {ref_checksum} {ref_path}\n{installer} {installer_checksum} {installer_path}")


if __name__ == '__main__':
    cmd_args = parse_args()
    main(cmd_args.installer, cmd_args.release)