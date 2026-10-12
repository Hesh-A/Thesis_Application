# Swallow Audio Annotation Application

The Swallow Audio Annotation Application is a desktop tool for organizing and reviewing cervical auscultation recordings from premature infants. It brings participant and session metadata, audio, swallow timestamps, waveform and spectrogram views, and text annotations into one application.

The application is intended to support clinical and research review. It does not automatically diagnose aspiration or classify swallow sounds. Flagged-swallow status comes from the imported spreadsheet metadata.

## What the Application Does

- Imports participant, session, and swallow timing data from Excel workbooks.
- Stores imported records and annotations in a local SQLite database.
- Browses recordings by participant, session, and swallow.
- Displays audio as a waveform and spectrogram, with swallow ranges highlighted on both views.
- Synchronizes audio playback with the timeline and provides zooming, scrolling, and adjustable spectrogram parameters.
- Marks swallows flagged in the spreadsheet with a red dot in the swallow list. Selecting a flagged swallow also shows a red plot highlight.
- Saves an editable text annotation for each selected swallow.

## Requirements

- Python 3.10 or newer.
- Windows, macOS, or Linux with a working Qt display and multimedia/audio backend.
- A workbook and WAV recordings are only needed to import and review data; the app can start with an empty project.

## Installation and Launch

The Python source is intended to run on Windows, macOS, and Linux. Native executable bundles are platform-specific; this repository currently has a tested Windows PyInstaller build, not macOS or Linux builds.

From the extracted project folder, create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate it with:

```sh
source .venv/bin/activate
```

Install the same application dependencies on each platform:

```sh
python -m pip install -r requirements.txt
```

On systems where the Python 3 command is named `python3`, use `python3` in place of `python` below. Start the application from the project root:

```sh
python main.py
```

The launcher starts the local FastAPI backend and the desktop GUI. The backend listens on `127.0.0.1:8000`; keep this port available. The API's interactive documentation is available at `http://127.0.0.1:8000/docs` while the backend is running. First launch creates an empty project in the operating system's Documents folder under `Swallow Audio Annotation`, including its `database` and `audio` subfolders. No cloud service is used.

### Platform Status

| Platform | How to run or build | Status |
| --- | --- | --- |
| Windows | Run from source as above, or build the PyInstaller bundle below. | Windows bundle built and smoke-tested. |
| macOS | Run from source as above on a Mac. | Source path documented; native `.app` not built or tested here. |
| Linux | Run from source as above on Linux. | Source path documented; native Linux bundle not built or tested here. |

Qt multimedia uses each operating system's audio backend. Linux may require distribution-provided Qt/XCB and multimedia packages if PyQt6 reports missing platform or audio plugins.

## Windows Packaging

Build on Windows with the same Python environment used for the app. From the project root:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --noconfirm swallow_audio_annotation.spec
```

PyInstaller writes temporary build files to `build/` and the one-folder app to `dist/SwallowAudioAnnotation/`. Keep the entire output folder together; do not send only the `.exe`. To make a ZIP in PowerShell:

```powershell
Compress-Archive -Path .\dist\SwallowAudioAnnotation -DestinationPath .\SwallowAudioAnnotation-Windows.zip
```

The Windows spec excludes the old `MSVCP140.dll` bundled by Qt because it caused an access violation on the tested system. The target Windows computer must have the current **Microsoft Visual C++ 2015-2022 x64 Redistributable** installed. The app and its Python dependencies are bundled; the VC++ runtime is a Windows system prerequisite.

`swallow_audio_annotation.spec` is a PyInstaller build recipe. Its sections, in order, set the source folder, describe the files and imports PyInstaller analyzes, remove the outdated runtime DLL, package pure Python modules, create a GUI executable without a console, and collect the executable and dependencies into the output folder. Re-run the command above after changing app code; then test the new `dist/` output and recreate the ZIP. An old ZIP does not update when `dist/` is rebuilt.

The Windows spec is not a Mac or Linux build recipe. To provide native bundles for those systems, run and test a separate PyInstaller build on each target operating system. Until that is done, Mac/Linux users can run the Python source using the steps above.

## Prepare the Data

Use the three-row Excel workbook template (`.xlsx` recommended; `.xls` is also accepted). Row 2 contains the `Participant` and `Total Swallows` headers, row 3 labels swallow timestamp pairs as `Start` and `Stop`, and session data starts on row 4. Flat-header workbooks are not supported.

| Template column | Purpose |
| --- | --- |
| A (`Entry Number`) | Session identifier. |
| B (`Participant`) | Participant identifier with `(asp)` or `(no asp)` for session aspiration status. |
| G (`Final Audio start`) | Recording start time used to align spreadsheet timestamps with the WAV file. |
| I (`Total Swallows`) | Number of swallow events in the session. |
| J onward | Start and stop timestamps for each numbered swallow. |

Tag individual swallow timestamps with `(asp)` or `(no asp)` to record their aspiration status. The importer reports rows or swallow timings it skips because of missing or invalid data.

Place each recording at the project-relative path `audio/<participant-id>.wav`; for example, participant `P64` should have a recording at `audio/P64.wav`. The import process associates sessions with this path. Confirm that the participant ID and WAV filename match.

## Review a Recording

1. Launch the app with `python main.py`.
2. Choose **Import Data** from the application menu and select the workbook. The app reports how many rows were processed and shows any import warnings.
3. Select a participant, then a session. The session's recording and swallow list are loaded.
4. Select a swallow to seek to its time range. The selected region is highlighted in the waveform and spectrogram, and playback is positioned shortly before it. A flagged swallow is marked with a red dot and labeled as flagged when selected.
5. Use the play/pause control to listen; adjust volume as needed. When a swallow is selected, playback is limited to the nearby context around that event.
6. Use the timeline zoom and scroll controls to inspect other parts of the recording. Adjust the spectrogram's frequency range, window, hop size, FFT multiplier, window type, dynamic range, and colormap for closer inspection.
7. Enter or edit a note in the annotation panel and choose **Save**. Select another swallow to review its note or add a separate annotation.

## Data Storage

The application creates and uses `database/swallow.db` for participant, session, swallow, and annotation data. Imported records and saved annotations persist between launches. Back up this database and the original workbook and WAV files according to your project's data-management requirements. The app runs its API locally; it does not provide a cloud service or an annotation-export workflow.

## Portable Projects

Use **File > Export Project** to create a `.swallowproj` archive containing a SQLite snapshot and every WAV file referenced by its sessions. Export refuses missing recordings by default. You can explicitly confirm an incomplete archive for testing: missing recordings are omitted and their paths are cleared only in the archive's database copy; the current database and audio files are unchanged. Do not use an incomplete archive for a full recording review. **File > Open Project** extracts an archive into a new folder within the directory you select. It never replaces an existing project folder. Close and reopen the app to switch to the extracted project; the current project remains active until then. **Import Data** is still for Excel workbooks, not project archives.

You can also choose a project folder explicitly when launching from the project root:

```sh
python main.py --project "path/to/extracted/project"
```

The project folder must contain `database/swallow.db` and the referenced `audio/` files. Archives are **not encrypted** and may contain sensitive recordings and annotations; share and store them only through approved research-data channels. Close any other running app instance before reopening a project, because the local API uses port `8000`.

## Troubleshooting

- **The recording does not load:** Check that `audio/<participant-id>.wav` exists and that the participant ID matches the workbook.
- **The backend or data requests fail:** Make sure port `8000` is available and start the application from the project root.
- **An import fails:** Check the required column names and close the workbook in Excel before trying again. Review any warnings shown after an import.
- **Audio is silent:** Check the system output device and volume. Qt multimedia playback depends on the operating system's audio backend.

## Tests

Install the test runner in the active environment:

```sh
python -m pip install pytest
```

Run the automated tests from the project root with:

```sh
python -m pytest
```

Tests are grouped into two folders:

- `tests/unit/` covers focused parsing, API handler, and startup behavior.
- `tests/feature/` covers spreadsheet imports and project archive workflows.

Run a group independently with:

```sh
python -m pytest tests/unit
python -m pytest tests/feature
```