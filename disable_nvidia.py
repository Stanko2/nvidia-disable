import os
import subprocess
import re
import argparse
import sys

parser = argparse.ArgumentParser(description="Disables nvidia GPU for specific applications.")
parser.add_argument("-r", "--revert", help="Reverts changes made by this script.", action="store_true")
parser.add_argument("-l", "--list", help="Lists applications that could be optimized", action="store_true")
parser.add_argument("-a", "--apply", help="Applies changes to the system", action="store_true")
args = parser.parse_args()

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

def list_apps():
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
                continue
            yield (directory + app, app_regex, apps[app_regex])


def disable_nvidia_for_apps():
    for path, app, args in list_apps():
        data = ""
        patched = False
        with open(path, "r") as file:
            new_command = r"Exec=firejail --profile=/etc/firejail/no-nvidia.profile \1"
            if args != "":
                new_command += " " + args
            for line in file:
                if re.search("firejail", line):
                    patched = True
                    continue
                if not re.search(r"^Exec=", line):
                    data += line
                    continue
                data += re.sub(r"^Exec=(.*)$", new_command, line)
        if not patched:
            with open(path, "w") as file:
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


def get_gpu_id(is_integrated):
    process = subprocess.Popen("/usr/bin/vulkaninfo",env={
        "MESA_VK_DEVICE_SELECT": "list"
    }, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    data = str(error).split('\\n')

    regex = r"GPU [0-9]: ([0-9a-f]{4}:[0-9a-f]{4}) .*[Ii]ntegrated.*"

    if not is_integrated:
        regex = r"GPU [0-9]: ([0-9a-f]{4}:[0-9a-f]{4}) .*NVIDIA.*"

    for line in data:
        a = re.search(regex, line)
        if a != None:
            print(a.group(1))
            return a.group(1)

def do_general_tweaks():
    intel_id = get_gpu_id(True)
    vulkan_set_primary_gpu(intel_id)

def generate_firejail_profile():
    profile = ""
    with open("no-nvidia.profile", "r") as base:
        profile = base.read()
    name = get_nvidia_card_name()
    if name:
        profile += "blacklist /sys/class/drm/" + name + "/*\n"

    with open("/etc/firejail/no-no-nvidia.profile", "w") as file:
        file.write(profile)

def get_nvidia_card_pci(name):
    for file in os.listdir("/sys/class/drm/"+name+"/device/"):
        a = re.search(r"pci([0-9]+:[0-9]*:[0-9.]*)", file)
        if a:
            return a.group(1)

def get_nvidia_card_name():
    nvidia_vendor_id = get_gpu_id(False).split(":")[0]
    for card in os.listdir("/sys/class/drm/"):
        if not re.search(r"card[0-9]+.*", card):
            continue
        try:
            with open("/sys/class/drm/"+ card+ "/device/vendor") as v:
                vendor = v.readline().strip()
                if re.search(nvidia_vendor_id, vendor):
                    return card
        except (FileNotFoundError, NotADirectoryError):
            continue

def vulkan_set_primary_gpu(gpu_id):
    process = subprocess.Popen("/usr/bin/vulkaninfo",env={
        "MESA_VK_DEVICE_SELECT": gpu_id
    }, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()

if __name__ == '__main__':
    convert_absolute_paths(APP_DIRECTORIES)

    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    if args.revert:
        if os.getuid() != 0:
            print("You need to run this script as root to revert changes.")
            exit(1)
        revert()
    elif args.list:
        for path, app, args in list_apps():
            if args == "":
                print(path)
            else:
                print(path + ":" + args)
    elif args.apply:
        if os.getuid() != 0:
            print("You need to run this script as root to apply changes.")
            exit(1)
        check_dependencies()
        generate_firejail_profile()
        do_general_tweaks()
        disable_nvidia_for_apps()

    # get_intel_id()
    # generate_firejail_profile()
