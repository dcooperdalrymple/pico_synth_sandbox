# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import os
import storage
import usb_hid
import usb_cdc

# Disable write protection and unnecessary usb features
storage.remount("/", False, disable_concurrent_write_protection=True)
usb_hid.disable()
usb_cdc.enable(console=True, data=False)

dirs = ("/apps", "/presets", "/samples", "/songs")
for dir in dirs:
    try:
        os.stat(dir)
    except:
        os.mkdir(dir)
