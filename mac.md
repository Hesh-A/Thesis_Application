# Run and Test the Source on macOS

This guide runs the Python source directly. It does not build or package a Mac app.

## 1. Prepare the Source

Extract the source ZIP. It should contain `main.py`, `requirements.txt`, and the `api/`, `audio/`, `database/`, and `frontend/` source folders, including `frontend/main_window.ui`.

Do not include private databases, recordings, workbooks, or project archives unless they are approved test data. Do not use the Windows `.exe` or PyInstaller spec on Mac.

## 2. Set Up Python

Install Python 3.10 or newer. In Terminal, change to the extracted source folder, then create and activate a virtual environment:

```sh
cd /path/to/Thesis_App
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Launch and Test

Run the source app directly:

```sh
python main.py
```

The app should open without an existing database or WAV file. It creates an empty project under the Mac user's Documents folder, in `Swallow Audio Annotation`. Keep Terminal open while testing so errors remain visible.

If approved, non-sensitive test data is available, test opening a project archive with **File > Open Project**. Select the `.swallowproj`, choose a parent folder for extraction, then close the app and run `python main.py` again from the same Terminal and source folder. The archive contains a database and may contain recordings and annotations, so share it only when authorized.

To test playback and spectrograms, import an approved workbook and put its matching WAV recordings in the project's `audio/` folder. For example, participant `P64` needs `audio/P64.wav`.

## Qt Cocoa Plugin Troubleshooting

If startup says it cannot find the Qt platform plugin `cocoa`, activate the virtual environment, clear Qt plugin overrides, and retry:

```sh
source .venv/bin/activate
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM
python main.py
```

If it still fails, collect Qt's search log and check whether PyQt6 includes the Cocoa plugin:

```sh
QT_DEBUG_PLUGINS=1 python main.py 2>&1 | tee qt-plugin-error.log
plugin_path="$(python -c 'from PyQt6.QtCore import QLibraryInfo; print(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))')"
echo "$plugin_path"
ls "$plugin_path/platforms/libqcocoa.dylib"
```

Send the log and command output. Do not copy a Cocoa plugin from a different Qt installation; the plugin must match the PyQt6 Qt version and Mac architecture.

## 4. Report Results

Please report whether the app opened, the macOS and Python versions, which features were tested, and the full Terminal output if anything failed. This source path has not yet been verified on a Mac.
