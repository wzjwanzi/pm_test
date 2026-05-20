# UI 修改前必读

下次修改桌面版 UI 前，先阅读本文件，再改 `desktop_app.py`。本项目用户主要使用 release 里的 exe/Tk 桌面版，不要只验证 Web 页面。

## 已犯过的问题

1. 只确认控件创建成功，没有确认用户实际窗口第一屏是否看得到。
2. 内容超过窗口高度时，反复压缩控件，而不是先加整体滚动容器。
3. 混淆桌面版和 Web 版，改了 `templates/index.html` 但用户看的其实是 exe。
4. 没有根据用户截图反推当前可见区域，导致判断偏向“没打包/旧路径”。
5. 新增“用例总列表”后挤掉“用例选项”，让基站 Web、基站 SSH 的勾选项不可见。
6. 没有用接近用户截图的窗口高度验证布局。
7. 没有先固定布局原则，导致控件位置反复移动。

## 当前应保持的布局原则

1. `批量执行` 页必须整体可纵向滚动。
2. “用例选项”优先可见，且四组顺序保持为：`基站 Web`、`基站 SSH`、`灌包服务器`、`手机`。
3. `基站 Web` 必须能看到 `收集日志`、`启动抓包`。
4. `基站 SSH` 必须能看到 `输出日志`。
5. “用例总列表”使用竖向用例方框，每个方框代表一个可命名用例。
6. 运行用例时，“当前运行步骤”要能显示当前用例执行到哪一步。
7. 历史结果、原始明细、操作总结可以放在下方，通过滚动查看。

## 修改 UI 后必须验证

1. 运行源码级 Tk 初始化，确认 `pm_scroll_canvas` 存在。
2. 确认操作组顺序为 `基站 Web`、`基站 SSH`、`灌包服务器`、`手机`。
3. 确认 `operation_vars` 包含：
   - `base_web_collect_log`
   - `base_web_start_capture`
   - `base_ssh_output_log`
   - `server_down_ping`
   - `phone_up_ping`
4. 用接近用户截图的窗口高度检查：不用放大窗口，也能通过滚动访问所有区域。
5. 重新打包后，只验证默认路径：
   `D:\test\mobile_automation_platform\release\MobileTestPlatform\MobileTestPlatform.exe`
6. 如果 release 目录被占用，先检查并停止当前 release 下的 `MobileTestPlatform.exe` 或 `adb.exe`，再打包。

## 推荐验证命令

```powershell
python -m py_compile desktop_app.py
```

```powershell
$env:TCL_LIBRARY='D:\test\mobile_automation_platform\release\MobileTestPlatform\_internal\_tcl_data'
$env:TK_LIBRARY='D:\test\mobile_automation_platform\release\MobileTestPlatform\_internal\_tk_data'
@'
import desktop_app
desktop_app._import_tk_modules()
tk = desktop_app.tk
root = tk.Tk()
root.withdraw()
app = desktop_app.DesktopApp(root)
root.update_idletasks()
print('has_scroll=', hasattr(app, 'pm_scroll_canvas'))
print('groups=', [name for name, _ in app._operation_groups()])
print('actions=', sorted(app.operation_vars.keys()))
print('scrollregion=', app.pm_scroll_canvas.cget('scrollregion'))
root.destroy()
'@ | python -
```
