# DriverBackup Win (PyQt6)

## Tieng Viet

Ung dung desktop Windows de:
- Backup/Restore driver
- Backup/Restore danh sach ung dung qua WinGet
- Quan ly theo 2 tab: Drivers va Applications

Ung dung duoc thiet ke theo huong modular, clean code, de mo rong va tai su dung logic cho CLI.

### Kien truc project

```text
project/
|
|-- main.py
|-- ui/
|   |-- main_window.py
|-- core/
|   |-- driver_loader.py
|   |-- backup.py
|   |-- restore.py
|   |-- md5_utils.py
|   |-- admin.py
|   |-- winget_manager.py
|-- utils/
|   |-- logger.py
|   |-- file_utils.py
|   |-- lang.py
|-- config/
|   |-- settings.json
|-- lang/
|   |-- lang.json
```

### Chuc nang chinh

#### Drivers tab
- Load danh sach driver tu `DRIVERQUERY /FO CSV /SI`
- Tim kiem + loc
- Checkbox tung dong, `Select All`/`Unselect All`
- Backup selected drivers (mode `full`/`strict`)
- Quick backup
- Restore driver tu folder backup
- Export CSV danh sach driver

#### Applications tab
- Load danh sach app da cai qua `winget list`
- Tim kiem + loc theo source (winget/msstore)
- Checkbox tung app, `Select All`/`Unselect All`
- Backup selected apps ra JSON/CSV
- Import file backup app JSON
- Restore selected apps bang `winget install --id <id> -e --silent`
- Quick restore all apps hien thi
- Export script `.bat` de cai lai app

#### System level
- Nut `Full Backup System`: backup driver + app list
- Da ngon ngu VI/EN qua `lang/lang.json`
- Threading bang `QThread` de khong block UI
- Logging ra GUI + file
- Co ho tro xin quyen Administrator

### Cai dat moi truong (bat buoc dung venv)

```powershell
python -m venv venv
venv\Scripts\activate
pip install PyQt6
```

Khuyen nghi them (de build exe):

```powershell
pip install pyinstaller
```

### Chay ung dung

```powershell
venv\Scripts\activate
python main.py
```

### Build exe voi PyInstaller

```powershell
venv\Scripts\activate
pyinstaller --noconfirm --clean --windowed --onefile --name DriverBackupWin --icon easy-installation.ico --add-data "easy-installation.ico;." --add-data "config;config" --add-data "lang;lang" main.py
```

Sau khi build xong, file release nam tai `dist\DriverBackupWin.exe`.

### Ghi chu van hanh

- Mot so tinh nang (backup/restore driver, winget install) can quyen admin.
- WinGet can co san tren may (Windows Package Manager).
- Log mac dinh luu theo `config/settings.json`.

## English

Windows desktop app for:
- Driver Backup/Restore
- Installed apps Backup/Restore via WinGet
- Two main tabs: Drivers and Applications

The app follows a modular, clean-code architecture so logic can be extended and reused for CLI workflows.

### Project structure

```text
project/
|
|-- main.py
|-- ui/
|   |-- main_window.py
|-- core/
|   |-- driver_loader.py
|   |-- backup.py
|   |-- restore.py
|   |-- md5_utils.py
|   |-- admin.py
|   |-- winget_manager.py
|-- utils/
|   |-- logger.py
|   |-- file_utils.py
|   |-- lang.py
|-- config/
|   |-- settings.json
|-- lang/
|   |-- lang.json
```

### Main features

#### Drivers tab
- Load driver list from `DRIVERQUERY /FO CSV /SI`
- Search and filter
- Per-row checkbox with `Select All`/`Unselect All`
- Backup selected drivers (`full`/`strict` mode)
- Quick backup
- Restore drivers from backup folder
- Export driver list to CSV

#### Applications tab
- Load installed apps via `winget list`
- Search and filter by source (winget/msstore)
- Per-row checkbox with `Select All`/`Unselect All`
- Backup selected apps to JSON/CSV
- Import app backup JSON file
- Restore selected apps using `winget install --id <id> -e --silent`
- Quick restore for all displayed apps
- Export `.bat` reinstall script

#### System level
- `Full Backup System` button: backup drivers + app list
- VI/EN language support via `lang/lang.json`
- `QThread` background workers to keep UI responsive
- Logging to GUI and file
- Administrator privilege support

### Environment setup (venv required)

```powershell
python -m venv venv
venv\Scripts\activate
pip install PyQt6
```

Recommended for building exe:

```powershell
pip install pyinstaller
```

### Run the app

```powershell
venv\Scripts\activate
python main.py
```

### Build exe with PyInstaller

```powershell
venv\Scripts\activate
pyinstaller --noconfirm --clean --windowed --onefile --name DriverBackupWin --icon easy-installation.ico --add-data "easy-installation.ico;." --add-data "config;config" --add-data "lang;lang" main.py
```

After build, release artifact is available at `dist\DriverBackupWin.exe`.

### Runtime notes

- Some features (driver backup/restore, winget install) require admin privileges.
- WinGet must be available on the system.
- Default log file location is configured in `config/settings.json`.

## License

MIT License (MIT). See [LICENSE](LICENSE).