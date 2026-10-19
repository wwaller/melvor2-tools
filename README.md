# melvor2-tools

Tools for Melvor Idle 2.

## save-converter

Makes a playtest save loadable in the Melvor Idle 2 Demo. The Demo only loads saves whose header marks them as Demo saves; the converter sets that one flag and leaves the rest of the save byte for byte, so the Demo reads the same character. The Demo's level 60 cap and locked content still apply.

```sh
uv run save-converter/convert.py my-save.txt            # a save string from the playtest's Export Save
uv run save-converter/convert.py save_<id>.sav --install # a save file, copied straight into the Demo's saves folder
```

It writes `<name>-demo.sav` and `<name>-demo.txt` next to the input. Paste the `.txt` string into the Demo's Import Save, or use `--install`. The Demo keeps at most 5 saves.

Saves from before Alpha 0.11.0 have no Demo flag; load them in the playtest once and export again.

Tests: `uv run save-converter/dev/test_convert.py`. `save-converter/dev/game-reader` builds a save with the Demo's own `SaveWriter` and reads one back with its `SaveReader`, using the installed Demo's assembly; it needs the .NET 10 SDK:

```sh
dotnet run --project save-converter/dev/game-reader -- make playtest.sav playtest.txt
uv run save-converter/convert.py playtest.txt
dotnet run --project save-converter/dev/game-reader -- read playtest-demo.txt
```
