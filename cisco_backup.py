from netmiko import ConnectHandler
import getpass
import threading
import time
import os

from models.command import Command


def get_current_date():
    day = time.strftime('%d')
    month = time.strftime('%m')
    year = time.strftime('%Y')
    return day + "-" + month + "-" + year


def get_filename_success(device, extension="txt"):
    return "{device_ip}-{current_date}.{extension}".format(
        device_ip=device['ip'],
        current_date=get_current_date(),
        extension=extension
    )


def get_filename_error(device, extension="txt"):
    return "{device_ip}-{current_date}Error.{extension}".format(
        device_ip=device['ip'],
        current_date=get_current_date(),
        extension=extension
    )


def get_filename_summary(extension="csv"):
    return "summary.{ext}".format(
        ext=extension
    )


def get_credentials():
    username = input("username ")
    password = getpass.getpass()
    secret = getpass.getpass()

    return username, password, secret


def get_devices(username, password, secret):
    devices = []
    ip_list_file = open("iplist.csv")

    for line in ip_list_file:

        if not line.strip():
            continue

        devices.append({
            'device_type': line.strip("\n").split(",")[1],
            'ip': line.strip("\n").split(",")[0],
            'username': username,
            'password': password,
            'secret': secret,
            'session_log': 'log.txt'
        })

    return devices


def backup_configs(device, commands):

    # create today folder is not exist
    today_folder = get_current_date()
    os.makedirs(get_current_date(), exist_ok=True)

    summary = os.path.join(today_folder, get_filename_summary())
    save_summary = open(summary, "a")

    try:
        remote_conn = ConnectHandler(**device)

        # save successful connection into today folder
        filename = os.path.join(today_folder, get_filename_success(device))
        save_config = open(filename, "w+")

        for command in commands:
            actions = command.command_action.split(";")
            if len(actions) == 0:
                continue
            elif len(actions) == 1:
                output = getattr(remote_conn, command.command_type)(actions[0])
            else:
                output = getattr(remote_conn, command.command_type)(actions)

            save_config.write(output)

        save_summary.write("{ip},{status}".format(
            ip=device['ip'],
            status="Success"
        ))

        save_config.close()
        remote_conn.disconnect()
    except Exception as e:
        filename = os.path.join(today_folder, get_filename_error(device))
        save_error = open(filename, "w+")
        save_error.write("Access to " + device['ip'] + " failed, backup did not taken. Exception: " + str(e))
        save_error.close()

        save_summary.write("{ip},{status}".format(
            ip=device['ip'],
            status="Failed"
        ))
    finally:
        save_summary.close()


def get_command_dict():
    command_dict = dict()

    if not os.path.isdir('commands'):
        return command_dict

    for filename in os.listdir('commands'):
        with open(os.path.join('commands', filename), 'r') as f:
            key = os.path.splitext(filename)[0]
            command_dict[key] = []
            for line in f:
                if not line.strip():
                    continue
                str_line = line.strip().split(",")
                command = Command(command_type=str_line[0], command_action=str_line[1])
                command_dict[key].append(command)

    return command_dict


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    command_dict = get_command_dict()
    if not command_dict.keys():
        print('Please config command of device in folder commands')
        return

    username, password, secret = get_credentials()
    devices = get_devices(username, password, secret)
    chunk_size = 10
    device_chunks = list(chunks(devices, chunk_size))

    for chunk in device_chunks:
        print("Starting backup {total_device} devices".format(total_device=len(chunk)))
        for device in chunk:
            child_thread = threading.Thread(target=backup_configs, args=(device, command_dict[device['device_type']]))
            child_thread.start()
        main_thread = threading.currentThread()
        for child_thread in threading.enumerate():
            if child_thread != main_thread:
                child_thread.join()


if __name__ == "__main__":
    main()
