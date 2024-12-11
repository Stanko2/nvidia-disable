import os
import subprocess
import re

APP_DIRECTORIES = [
    "/usr/share/applications/",
    "/usr/local/share/applications/",
    "~/.local/share/applications/",
    "~/.config/autostart/",
    "~/.config/autostart-scripts/"
]

def check_dependencies():
    if os.path.exists("/usr/bin/firejail"):
        print("Firejail is installed.")
    else:
        print("Firejail is not installed. You need to install it first.")
        exit(1)

    output = subprocess.run("MESA_VK_DEVICE_SELECT=list /usr/bin/vulkaninfo")
    if not re.search(r"[Ii]ntel", str(output.stdout)):
        print("Intel graphics card is not detected.")
        print("You probably need to install vulkan-intel and vulkan-mesa-layers packages.")
        exit(1)



def load_applications():
    apps = {}
    with open("tested_apps", "r") as file:
        for line in file:
            parsed = line.split("#")[0].strip()
            if parsed == "":
                continue
            app, args = parsed.split(":")
            apps[app] = args

    return apps


def disable_nvidia_for_apps():
    apps = load_applications()
    print(apps)
    for directory in APP_DIRECTORIES:
        if not os.path.exists(directory):
            continue
        for app in os.listdir(directory):
            app_regex = ""
            for a in apps.keys():
                if re.search(a, app):
                    app_regex = a
                    break
            if app_regex == "":
                # print("App " + app + " is not in the list of tested apps. Skipping.")
                continue
            else:
                print("Disabling nvidia for " + app)
            patched = False
            data = ""
            with open(directory + app, "r") as file:
                new_command = r"Exec=firejail --profile=/etc/firejail/no-nvidia.profile \1"
                if apps[app_regex] != "":
                    new_command += " " + apps[app_regex]
                for line in file:
                    if re.search("firejail", line):
                        patched = True
                        continue
                    if not re.search(r"^Exec=", line):
                        data += line
                        continue
                    data += re.sub(r"^Exec=(.*)$", new_command, line)
            if not patched:
                with open(directory + app, "w") as file:
                    file.write(data)
            else:
                print("App " + app + " is already patched. Skipping.")


def revert():
    apps = load_applications()
    for directory in APP_DIRECTORIES:
        if not os.path.exists(directory):
            continue
        for app in os.listdir(directory):
            app_regex = ""
            for a in apps.keys():
                if re.search(a, app):
                    app_regex = a
                    break

            if app_regex == "":
                # print("App " + app + " is not in the list of tested apps. Skipping.")
                continue
            else:
                print("Reverting changes for " + app)

            with open(directory + app, "r+") as file:
                old_command = r"^Exec=firejail --profile=/etc/firejail/no-nvidia.profile (.*) " + apps[app_regex] + "$"
                data = ""
                for line in file:
                    if not re.search(old_command, line):
                        data+=line
                        continue

                    data += re.sub(old_command, r"Exec=\1", line)

                file.seek(0)
                file.write(data)

def convert_absolute_paths(path):
    user = os.getenv("SUDO_USER")
    if not user:
        return
    for i in range(len(APP_DIRECTORIES)):
        if APP_DIRECTORIES[i][0] == "~":
            APP_DIRECTORIES[i] = APP_DIRECTORIES[i].replace("~", "/home/" + user)

if __name__ == '__main__':
    if os.getuid() != 0:
        print("You need to run this script as root.")
        exit(1)

    print(os.getenv("SUDO_USER"))

    disable_nvidia_for_apps()
    # revert()
