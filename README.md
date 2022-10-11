# Dialogue tree command block generator
An Amulet Editor operation that creates command blocks according to a dialogue tree file.

## Installing
1. Go to `https://github.com/remuladgryta/Amulet-Dialogue-Tree/releases` and download the latest zip file.
2. Copy `dialoguetree.py` from the zip into your Amulet `plugins/operations/` folder
3. The generator should now show up in the dropdown list of operations in Amulet's 3D editor the next time you open a world.


See the included `bridgevendor.xml` example for details on how to write your own
dialogue tree file. A dialogue can have multiple entry points. To start a
dialogue for a player, add a tag to the player corresponding to the dialogue id
and state id you want them to enter. For example if you want Notch to enter the
bridgevendor dialogue in the intro state, run `/tag Notch add bridgevendor.next.intro`
