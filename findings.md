# Findings

## 2026-04-15
- Workspace hien co 1 file chinh: driverbackup-win.py.
- Chua co planning files truoc do.
- Se can refactor manh de dap ung day du yeu cau UI/feature/threading/i18n.
- Script hien tai backup bang cach quet DriverStore va so khop MD5 toi INF dang su dung.
- Chua co restore, chua co GUI, chua co co che xin quyen admin, chua co log file.
- README hien tai chi mo ta script CLI, can viet lai cho ung dung desktop PyQt6.
- Da bo sung core/winget_manager.py voi cac ham get_installed_apps, export/import, install_app, install_multiple_apps, search/filter.
- UI da tach thanh 2 tab Drivers va Applications, dung QThread worker de tranh block.
- Da them Full Backup System de backup driver + danh sach apps da chon.
