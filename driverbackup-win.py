import os
import csv
import shutil
from datetime import datetime
import hashlib

# backup mode sets how the script backs up the drivers
# full = backup entire WHQL driver list, including duplicated ones (some drivers use same .INF and files)
# strict = backs up only one copy of each driver to save space. all drivers are still backed up, but only 1 copy.
backup_mode = 'full'

current_datetime = datetime.now().strftime("%Y-%m-%d_%Hh%Mm")
whql_drivers_root = "C:\Windows\INF"
storage_drivers_root = "C:\Windows\System32\DriverStore\\FileRepository\\"

# create signed drivers list from system and dump to csv file
os.system("DRIVERQUERY /FO CSV /SI > drv_list.csv")

# open and parse csv file
csv_file = open("drv_list.csv", "r")
csv_parse = csv.DictReader(csv_file)

# create a list with md5 values of whql drivers .inf
whql_drivers_md5 = list()
for whql_driver in csv_parse:
    try:
        whql_driver_inf = open(os.path.join(
            whql_drivers_root, whql_driver["InfName"]), 'rb')
        md5 = hashlib.md5(whql_driver_inf.read()).hexdigest()
        whql_drivers_md5.append(
            [md5, whql_driver["DeviceName"]])
    except:
        print(
            f'Driver file "{whql_driver["InfName"]}" not found for "{whql_driver["DeviceName"]}".')
        continue

# trim whql_drivers_md5 if backup_mode is set to 'strict'.
if backup_mode == 'strict':
    whql_drivers_dict = dict(whql_drivers_md5)
    whql_drivers_md5.clear()
    for whql_driver in whql_drivers_dict:
        whql_drivers_md5.append([whql_driver, whql_drivers_dict[whql_driver]])

# close and delete csv file
csv_file.close()
if os.path.exists("drv_list.csv"):
    os.remove("drv_list.csv")

# walk over all directories on DriverStore repo and return .INF files
for root, dirs, files in os.walk(storage_drivers_root):
    for storage_driver_inf in files:

        # create md5 checksum from .inf found
        if storage_driver_inf.endswith(".inf"):
            try:
                storage_driver_md5 = hashlib.md5(
                    open(os.path.join(root, storage_driver_inf), 'rb').read()).hexdigest()
            except:
                print(f'Cannot checksum: {root}')
                continue

        # in case .INF md5 matches .INF from WHQL list, backup drive and remove that whql driver from list
        for storage_driver in whql_drivers_md5:
            if storage_driver[0] == storage_driver_md5:
                whql_drivers_md5.remove(storage_driver)
                destination_dir = "DrvBkp " + \
                    os.environ['COMPUTERNAME']+" "+current_datetime + \
                    "\\"+storage_driver[1]
                shutil.copytree(root, destination_dir, dirs_exist_ok=True)
                continue
