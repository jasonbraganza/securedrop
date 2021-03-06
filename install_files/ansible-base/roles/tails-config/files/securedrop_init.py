#!/usr/bin/python

import grp
import os
import io
import pwd
import sys
import subprocess


# check for root
if os.geteuid() != 0:
    sys.exit('You need to run this as root')

# paths
path_torrc_additions = '/home/amnesia/Persistent/.securedrop/torrc_additions'
path_torrc_backup = '/etc/tor/torrc.bak'
path_torrc = '/etc/tor/torrc'
path_desktop = '/home/amnesia/Desktop/'
path_persistent_desktop = '/lib/live/mount/persistence/TailsData_unlocked/dotfiles/Desktop/'  # noqa: E501
path_securedrop_root = '/home/amnesia/Persistent/securedrop'
path_securedrop_admin_venv = os.path.join(path_securedrop_root,
                                          'admin/.venv/bin/python')
path_securedrop_admin_init = os.path.join(path_securedrop_root,
                                          'admin/securedrop_admin/__init__.py')
path_gui_updater = os.path.join(path_securedrop_root,
                                'journalist_gui/SecureDropUpdater')

# load torrc_additions
if os.path.isfile(path_torrc_additions):
    with io.open(path_torrc_additions) as f:
        torrc_additions = f.read()
else:
    sys.exit('Error opening {0} for reading'.format(path_torrc_additions))

# load torrc
if os.path.isfile(path_torrc_backup):
    with io.open(path_torrc_backup) as f:
        torrc = f.read()
else:
    if os.path.isfile(path_torrc):
        with io.open(path_torrc) as f:
            torrc = f.read()
    else:
        sys.exit('Error opening {0} for reading'.format(path_torrc))

    # save a backup
    with io.open(path_torrc_backup, 'w') as f:
        f.write(torrc)

# append the additions
with io.open(path_torrc, 'w') as f:
    f.write(torrc + torrc_additions)

# reload tor
try:
    subprocess.check_call(['systemctl', 'reload', 'tor@default.service'])
except subprocess.CalledProcessError:
    sys.exit('Error reloading Tor')

# Turn off "automatic-decompression" in Nautilus to ensure the original
# submission filename is restored (see
# https://github.com/freedomofpress/securedrop/issues/1862#issuecomment-311519750).
subprocess.call(['/usr/bin/dconf', 'write',
                 '/org/gnome/nautilus/preferences/automatic-decompression',
                 'false'])

# Set journalist.desktop and source.desktop links as trusted with Nautilus (see
# https://github.com/freedomofpress/securedrop/issues/2586)
# set euid and env variables to amnesia user
amnesia_gid = grp.getgrnam('amnesia').gr_gid
amnesia_uid = pwd.getpwnam('amnesia').pw_uid
os.setresgid(amnesia_gid, amnesia_gid, -1)
os.setresuid(amnesia_uid, amnesia_uid, -1)
env = os.environ.copy()
env['XDG_CURRENT_DESKTOP'] = 'GNOME'
env['DESKTOP_SESSION'] = 'default'
env['DISPLAY'] = ':1'
env['XDG_RUNTIME_DIR'] = '/run/user/{}'.format(amnesia_uid)
env['XDG_DATA_DIR'] = '/usr/share/gnome:/usr/local/share/:/usr/share/'
env['HOME'] = '/home/amnesia'
env['LOGNAME'] = 'amnesia'
env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/{}/bus'.format(
        amnesia_uid)

# remove existing shortcut, recreate symlink and change metadata attribute
# to trust .desktop
for shortcut in ['source.desktop', 'journalist.desktop']:
    subprocess.call(['rm', path_desktop + shortcut], env=env)
    subprocess.call(['ln', '-s', path_persistent_desktop + shortcut,
                     path_desktop + shortcut], env=env)
    subprocess.call(['gio', 'set', path_desktop + shortcut,
                     'metadata::trusted', 'yes'], env=env)

# reacquire uid0 and notify the user
os.setresuid(0, 0, -1)
os.setresgid(0, 0, -1)
subprocess.call(['tails-notify-user',
                 'SecureDrop successfully auto-configured!',
                 'You can now access the Journalist Interface.\n',
                 'If you are an admin, you can now SSH to the servers.'])

# As the amnesia user, check for SecureDrop workstation updates.
os.setresgid(amnesia_gid, amnesia_gid, -1)
os.setresuid(amnesia_uid, amnesia_uid, -1)
output = subprocess.check_output([path_securedrop_admin_venv,
                                  path_securedrop_admin_init,
                                  '--root', path_securedrop_root,
                                  'check_for_updates'], env=env)

flag_location = "/home/amnesia/Persistent/.securedrop/securedrop_update.flag"
if 'Update needed' in output or os.path.exists(flag_location):
    # Start the SecureDrop updater GUI.
    subprocess.Popen(['python3', path_gui_updater], env=env)
