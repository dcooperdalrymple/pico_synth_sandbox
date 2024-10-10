# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import time
import os
import gc
import supervisor
import synthmenu
import synthkeyboard
import hardware

DELAY = 0.5
APP_DIR = "/apps"

def format_name(name:str) -> str:
    name = name.lower().replace('_', ' ').replace('-', ' ').split()
    for i in range(len(name)):
        name[i] = name[i][0].upper() + name[i][1:]
    return " ".join(name)

def get_enum(cls) -> tuple:
    items = []
    for name in dir(cls):
        if name[0] == '_':
            continue
        items.append((format_name(name), getattr(cls, name)))
    return tuple(items)

def set_attribute(items:list|tuple|object, name:str, value:any, offset:float = 0.0) -> None:
    if type(items) is not list and type(items) is not tuple:
        items = tuple([items])
    for i, item in enumerate(items):
        if hasattr(item, name):
            if type(value) is float and offset > 0.0:
                setattr(item, name, value + offset * (i - (len(items) - 1) / 2))
            else:
                setattr(item, name, value)

def set_global_attribute(value:any, name:str) -> None:
    if name in globals():
        globals()[name] = value

def write_message(msg:str, delay:bool|float = False) -> None:
    hardware.lcd.cursor_position(0, 1)
    hardware.lcd.message = msg
    if delay:
        time.sleep(delay if type(delay) is float else DELAY)

def load_patch(menu:synthmenu.Menu, item:synthmenu.Item, value:int, prepend:str = 'patch') -> bool:
    on_update = item.on_update
    item.on_update = None
    result = menu.read("/presets/{:s}-{:d}.json".format(prepend, value))
    if not result:
        menu.reset(True)
    menu.do_update()
    item.data = value
    item.on_update = on_update
    return result

def save_patch(menu:synthmenu.Menu, value:int, prepend:str = 'patch') -> bool:
    write_message("Saving...")
    if (result := menu.write("/presets/{:s}-{:d}.json".format(prepend, value))):
        write_message("Complete!", True)
    else:
        write_message("Failed!", True)
    return result

def copy_data(source:str|synthmenu.Group, target:str|synthmenu.Group|list[str|synthmenu.Group], menu:synthmenu.Menu = None) -> None:
    write_message("Copying...")

    if type(source) is str and menu is not None:
        source = menu.find(source)
    
    if type(target) is not list:
        target = [target]
    for i in range(len(target)):
        if type(target[i]) is str and menu is not None:
            target[i] = menu.find(target)
    target = list(filter(lambda item: isinstance(item, synthmenu.Group), target))

    if not isinstance(source, synthmenu.Group) or not len(target):
        write_message("Failed!", True)
        return
    
    data = source.data
    for item in target:
        item.data = data

    write_message("Complete!", True)

def load_app(filename:str|None = None) -> bool:
    write_message("Loading...")
    if filename is not None:
        filename = APP_DIR + "/" + filename
        try:
            os.stat(filename)
        except OSError as e:
            write_message("Failed!", True)
            return False
    hardware.deinit()
    gc.collect()
    supervisor.set_next_code_file(
        filename=filename,
        reload_on_success=True,
        reload_on_error=True,
        sticky_on_success=True,
        sticky_on_error=False,
        sticky_on_reload=False,
    )
    supervisor.reload()
    return True

def load_launcher() -> None:
    load_app()

encoder_position = None
def handle_controls(menu:synthmenu.Menu) -> None:
    global encoder_position
    if encoder_position is None:
        encoder_position = [encoder.position for encoder in hardware.encoders]

    for i, encoder in enumerate(hardware.encoders):
        position = encoder.position
        hardware.buttons[i].update()

        if position > encoder_position[i]:
            for j in range(position - encoder_position[i]):
                menu.next() if not i else menu.increment()
        elif position < encoder_position[i]:
            for j in range(encoder_position[i] - position):
                menu.previous() if not i else menu.decrement()
        if hardware.buttons[i].rose:
            if not i:
                menu.exit()
            elif isinstance(menu.selected.current_item, (synthmenu.Group, synthmenu.Action)):
                menu.select()
        
        encoder_position[i] = position

# Premade Groups

def get_arpeggiator_group(arpeggiator:synthkeyboard.Arpeggiator) -> synthmenu.Group:
    arpeggiator_steps = get_enum(synthkeyboard.TimerStep)
    arpeggiator_modes = get_enum(synthkeyboard.ArpeggiatorMode)
    return synthmenu.Group("Arp", (
        synthmenu.Bool(
            title="Enabled",
            on_update=lambda value, item: set_attribute(arpeggiator, 'active', value),
        ),
        synthmenu.List(
            title="Mode",
            items=tuple([item[0] for item in arpeggiator_modes]),
            on_update=lambda value, item: set_attribute(arpeggiator, 'mode', arpeggiator_modes[value][1]),
        ),
        synthmenu.Number(
            title="Octaves",
            step=1,
            default=0,
            minimum=-4,
            maximum=4,
            decimals=0,
            on_update=lambda value, item: set_attribute(arpeggiator, 'octaves', value),
        ),
        synthmenu.Number(
            title="Tempo",
            step=1,
            default=120,
            minimum=60,
            maximum=240,
            append=" bpm",
            on_update=lambda value, item: set_attribute(arpeggiator, 'bpm', value),
        ),
        synthmenu.Percentage(
            title="Gate",
            default=0.5,
            step=0.05,
            on_update=lambda value, item: set_attribute(arpeggiator, 'gate', value),
        ),
        synthmenu.List(
            title="Steps",
            items=tuple([item[0] for item in arpeggiator_steps]),
            on_update=lambda value, item: set_attribute(arpeggiator, 'steps', arpeggiator_steps[value][1]),
        ),
        synthmenu.Percentage(
            title="Prob",
            default=1.0,
            on_update=lambda value, item: set_attribute(arpeggiator, 'probability', value),
        ),
    ))
