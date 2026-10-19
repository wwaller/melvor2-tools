# melvor2-tools

Tools for Melvor Idle 2.

## save-converter

Makes a playtest save loadable in the Melvor Idle 2 Demo. The Demo only loads saves whose header marks them as Demo saves; the converter sets that flag and gives the copy a new id, leaving the rest of the save byte for byte, so the Demo reads the same character. The Demo's level 60 cap and locked content still apply.

```sh
uv run save-converter/convert.py save_<id>.sav   # a playtest save file
uv run save-converter/convert.py my-save.txt     # or a save string from the playtest's Export Save
```

It writes `<name>-demo.txt` to the current folder (or `--out`); paste that string into the Demo's Import Save. Importing is the way in: a save file dropped into the saves folder is deleted the next time the game syncs with the cloud. Playtest saves live in `~/Library/Application Support/Games By Malcs/Melvor Idle 2/steam/<Steam id>/saves`, a folder the Demo shares, so after the import both games list the original and the Demo copy.

Saves from before Alpha 0.11.0 have no Demo flag; load them in the playtest once and convert again.

Tests: `uv run save-converter/dev/test_convert.py`. `save-converter/dev/game-reader` builds a save with the Demo's own `SaveWriter` and reads one back with its `SaveReader`, using the installed Demo's assembly; it needs the .NET 10 SDK:

```sh
dotnet run --project save-converter/dev/game-reader -- make playtest.sav playtest.txt
uv run save-converter/convert.py playtest.txt
dotnet run --project save-converter/dev/game-reader -- read playtest-demo.txt
```
