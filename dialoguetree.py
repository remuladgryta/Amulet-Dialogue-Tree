"""
This license applies to this file only.
-- begin license --
MIT License
Copyright (c) 2022 Remuladgryta
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-- end license --
"""


from amulet.api.selection import SelectionGroup
from amulet.api.level import BaseLevel
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet.api.block_entity import BlockEntity
from amulet_nbt import *

import xml.etree.ElementTree as ET

operation_options = {
    "Dialogue xml":["file_open"]
}

BLOCK_VERSION = ("java", (1, 16, 3))

def operation(
    world: BaseLevel, dimension: Dimension, selection: SelectionGroup, options: dict
):
    if len(selection) < 1:
        raise Exception("You need to select an area to place command blocks in.")

    path = options["Dialogue xml"]
    command_chains = parse_dialogue_xml(path)

    box = selection[0]
    x, y, z = box.min_x, box.min_y, box.min_z
    for dx, chain in enumerate(command_chains):
        generate_commandblock_chain(chain, world, dimension, x+dx, y, z+1)
        yield (1+dx)/len(command_chains)

    generate_on_off_switch(world, dimension, x, y, z, len(command_chains))

def parse_dialogue_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    dialogue_id = root.get("id")
    chains = []
    chains.append(["scoreboard objectives add dialogueOption trigger"])
    for state_node in root.iter("state"):
        chains += state(dialogue_id, state_node)
    chains.append(endstate(dialogue_id))
    return chains


def generate_commandblock_chain(chain, world, dimension, x, y, z):
    headblock = Block.from_string_blockstate("minecraft:repeating_command_block[facing=south,conditional=false]")
    chainblock = Block.from_string_blockstate("minecraft:chain_command_block[facing=south,conditional=false]")

    #create head of chain
    commandblock_data = TAG_Compound()
    commandblock_data["Command"] = TAG_String(chain[0])
    block_entity = BlockEntity("minecraft", "command_block", x, y, z, commandblock_data)
    world.set_version_block(x, y, z, dimension, BLOCK_VERSION, headblock, block_entity)

    #create tail
    for dz, command in enumerate(chain[1:], start=1):
        commandblock_data = TAG_Compound()
        commandblock_data["Command"] = TAG_String(command)
        commandblock_data["auto"] = TAG_Byte(1)
        block_entity = BlockEntity("minecraft", "command_block", x, y, z+dz, commandblock_data)
        world.set_version_block(x, y, z+dz, dimension, BLOCK_VERSION, chainblock, block_entity)

def generate_on_off_switch(world, dimension, x, y, z, length):
    base_command = "fill {x1} {y} {z} {x2} {y} {z} {block}"

    fill_command = base_command.format(x1=x, y=y, z=z, x2=x+length, block="minecraft:redstone_block")
    fill_block = Block.from_string_blockstate("minecraft:repeating_command_block[facing=east]")
    fill_data = TAG_Compound()
    fill_data["Command"] = TAG_String(fill_command)
    fill_entity = BlockEntity("minecraft", "command_block", x+2, y+2, z, fill_data)
    world.set_version_block(x+2, y+2, z, dimension, BLOCK_VERSION, fill_block, fill_entity)

    empty_command = base_command.format(x1=x, y=y, z=z, x2=x+length, block="minecraft:air")
    empty_block = Block.from_string_blockstate("minecraft:chain_command_block[facing=east]")
    empty_data = TAG_Compound()
    empty_data["Command"] = TAG_String(empty_command)
    empty_data["auto"] = TAG_Byte(1)
    empty_entity = BlockEntity("minecraft", "command_block", x+3, y+2, z, empty_data)
    world.set_version_block(x+3, y+2, z, dimension, BLOCK_VERSION, empty_block, empty_entity)

    lamp = Block.from_string_blockstate("minecraft:redstone_lamp")
    world.set_version_block(x+1, y+2, z, dimension, BLOCK_VERSION, lamp)

    lever = Block.from_string_blockstate("minecraft:lever[face=wall,facing=west]")
    world.set_version_block(x, y+2, z, dimension, BLOCK_VERSION, lever)


class Chain():
    def __init__(self, tag):
        self.chain = []
        self.selector = "@a[tag={}]".format(tag)
        self.tag = tag

    def command(self, c, **kwargs):
        self.chain.append(
            c.format(
                select=self.selector,
                tag=self.tag,
                **kwargs
            )
        )
        return self

def parse_rawtext_json(text):
    if (text[0] == "{" and text[-1] == "}") or (text[0] == "[" and text[-1] == "]") or (text[0] == '"' and text[-1] == '"'):
        return text
    else:
        return '"' + text + '"'

def state(dialogue_id, state_node):
        state_id = state_node.get("id")
        if state_id == "end":
            raise Exception('"end" is a reserved special state, you may not declare it.')
        state_tag = ".".join([dialogue_id, state_id])
        state_transition_tag = ".".join([dialogue_id, "next", state_id])
        transition_chain = Chain(tag=state_transition_tag)
        options = []
        for child in state_node.iter():
            if child.tag == "message":
                message(transition_chain, child)
            elif child.tag == "option":
                options.append(
                    option(transition_chain, dialogue_id, state_id, len(options)+1, child)
                )
            elif child.tag == "command":
                transition_chain.command(child.text)

        if(options):
            (transition_chain
                .command("scoreboard players reset {select} dialogueOption")
                .command("scoreboard players enable {select} dialogueOption")
            )

        (transition_chain
            .command("tag {select} add {newtag}",
                newtag=".".join([dialogue_id, state_id])
            )
            .command("tag {select} remove {tag}")
        )

        return [transition_chain.chain] + options

def endstate(dialogue_id):
    tag = dialogue_id + ".next.end"
    select = "@a[tag={tag}]".format(tag=tag)
    return ["tag {select} remove {tag}".format(select=select, tag=tag)]

def message(chain: Chain, message_node):
    if message_node.get("speaker"):
        chain.command('tellraw {select} ["[", {{"selector":"{speaker}"}}, "]", {msg}]', speaker=message_node.get("speaker"), msg=parse_rawtext_json(message_node.text))
    else:
        chain.command("tellraw {select} {msg}", msg=parse_rawtext_json(message_node.text))


def option(transition_chain, dialogue_id: str, state_id: str, optnum: int, option_node):
    # emit this dialogue option during state transition
    option_text = parse_rawtext_json(option_node.text)
    rawtext = (
    '{' +
        '"text":"[{optnum}]", '.format(optnum=optnum) +
        '"color":"yellow",' +
        '"clickEvent":{{"action":"run_command", "value":"/trigger dialogueOption set {optnum}"}},'.format(optnum=optnum) +
        '"extra":[{' +
            '"color":"white", "text":{opttext}'.format(opttext=option_text) +
        '}]' +
    '}'
    )
    transition_chain.command("tellraw {select} {raw}", raw=rawtext)

    # handle trigger
    state_tag = ".".join([dialogue_id, state_id])
    tmp_tag = state_tag + ".opt" + str(optnum)
    nextstate = option_node.get("next")
    transition_tag = ".".join([dialogue_id, "next", nextstate])
    chain = Chain(tag=tmp_tag)
    (
        chain.command("tag @a[tag={state_tag},scores={{dialogueOption={optnum}}}] add {tag}",
            optnum=optnum,
            state_tag=state_tag
        )
        .command("tag {select} add {transition}", transition=transition_tag)
        .command("tag {select} remove {state_tag}", state_tag=state_tag)
        .command("scoreboard players reset {select} dialogueOption")
        .command("tag {select} remove {tag}")
    )
    return chain.chain


export = {
    "name": "Dialogue tree generator",
    "options":operation_options,
    "operation":operation,
}

