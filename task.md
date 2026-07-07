你是tkinter python脚本高手。
我需要写一个windows下可以运行的gui程序。名字就叫cmd_sender。
实现这样的功能：
1、主体界面是一个编辑器。可以打开编辑多个文本文件。
2、当光标定位到某个行的时候，该行文本最左边有一个发送按钮。点击可以进行发送。
3、界面上有一个图标，点击它拖动到任意的窗口程序，则可以把cmd_sender跟目标窗口绑定起来。这个时候点击发送按钮，是把对应的行的文本输入到目标窗口里。
4、可以选中多行，右键选择发送。
帮我实现这个程序。只需要一个python文件。

不过这里有一个关键点需要先说明：

> **Tkinter 本身无法可靠地向其它 Windows 程序输入文字。**
>
> 需要调用 Win32 API。因此建议只依赖：
>
> * tkinter（Python自带）
> * ctypes（Python自带）
>
> 不需要 pywin32，不需要 PyQt。

---

我建议整体架构如下，比直接写代码后期维护容易很多。

| 模块           | 功能         |
| ------------ | ---------- |
| Editor       | 多Tab文本编辑器  |
| FileManager  | 打开/保存文件    |
| TargetWindow | 记录绑定窗口HWND |
| Sender       | 发送文本到目标窗口  |
| DragFinder   | 拖拽寻找窗口     |
| LineBar      | 左侧发送按钮     |
| PopupMenu    | 右键发送多行     |

整个程序仍然只有一个python文件。

---

## UI效果

```
+------------------------------------------------------------+
| File Edit                         [🎯] 当前: notepad.exe   |
+------------------------------------------------------------+
|------------------------------------------------------------|
|▶| first command                                            |
| | second command                                           |
|▶| third command                                            |
| | fourth command                                           |
|------------------------------------------------------------+
```

其中

```
▶
```

就是发送按钮。

只有当前行显示。

---

## 编辑器

Tkinter推荐使用

```
Text
```

不要用Entry。

支持

```
Undo
Redo
Copy
Paste
```

例如

```
text = tk.Text(
    undo=True,
    wrap="none"
)
```

---

## 多文件

建议采用

```
ttk.Notebook
```

```
+-----------------------------+
| test.txt | cmd.txt | xxx.txt|
+-----------------------------+
```

每个Tab一个Text。

保存

```
Ctrl+S

Ctrl+O

Ctrl+N
```

---

## 当前行发送按钮

Tkinter没有"行按钮"这种控件。

推荐的方法：

左边放一个Canvas。

```
Canvas
│
├─▶
│
│
├─▶
│
```

Canvas实时跟随Text滚动。

根据

```
text.index("insert")
```

知道当前行。

然后

```
text.dlineinfo(index)
```

获得当前行坐标。

```
info = text.dlineinfo("insert")

x
y
height
```

于是

Canvas上画一个Button。

```
canvas.create_window(
    10,
    y,
    window=button
)
```

这样按钮始终跟着当前行移动。

---

## 如何知道当前行

监听

```
<KeyRelease>

<ButtonRelease>

<Motion>
```

每次

```
current_line = text.index("insert").split(".")[0]
```

更新按钮。

---

## 发送流程

```
按钮

↓

取得当前行

↓

line = text.get(
    "10.0",
    "10.end"
)

↓

send(line)
```

---

## 拖动绑定窗口

这个功能Windows API支持。

很多截图软件就是这样做。

例如

```
🎯
```

鼠标按下

```
SetCapture()
```

鼠标移动

```
WindowFromPoint()
```

得到

```
HWND
```

然后高亮窗口。

鼠标松开

```
保存HWND
```

以后一直发送给它。

---

## 如何高亮目标窗口

可以画一个透明框。

WinAPI

```
GetWindowRect()

Rectangle()

InvertRect()
```

或者Tkinter建立

```
overrideredirect(True)
```

透明窗口。

---

## 发送文本

最简单：

```
SendMessage(
    hwnd,
    WM_SETTEXT,
    ...
)
```

但是很多程序不支持。

推荐：

```
SetForegroundWindow()

SendInput()
```

模拟键盘。

支持：

* CMD
* PowerShell
* Notepad++
* VSCode
* SecureCRT
* XShell
* MobaXterm
* 微信
* QQ

流程：

```
SetForegroundWindow(hwnd)

Sleep(50ms)

Ctrl+A (可选)

输入字符

Enter (可选)
```

---

## SendInput实现

Windows提供

```
SendInput()
```

模拟

```
KEYDOWN

KEYUP
```

Unicode字符直接发送。

不用剪贴板。

---

## 发送中文

不要

```
WM_CHAR
```

推荐

```
KEYEVENTF_UNICODE
```

可以直接

```
你好
```

不会乱码。

---

## 右键发送

获取

```
sel.first

sel.last
```

得到

```
开始行

结束行
```

例如

```
10

20
```

循环

```
for line in range(start,end+1):
```

发送。

菜单

```
--------------------
发送
复制
剪切
粘贴
--------------------
```

---

## 支持快捷键

建议支持：

| 快捷键          | 功能    |
| ------------ | ----- |
| Ctrl+N       | 新建    |
| Ctrl+O       | 打开    |
| Ctrl+S       | 保存    |
| Ctrl+Shift+S | 另存    |
| Ctrl+F       | 查找    |
| F5           | 发送当前行 |
| Ctrl+Enter   | 发送当前行 |
| Shift+F5     | 发送选中行 |

---

## 文件结构（仍然只有一个文件）

虽然只有一个 `.py` 文件，但建议内部按类组织：

```python
class CmdSenderApp

class EditorTab

class Sender

class TargetWindow

class DragTarget

class LineCanvas

class FileManager
```

总代码量大约：

| 模块       | 代码量  |
| -------- | ---- |
| GUI      | 400行 |
| 编辑器      | 250行 |
| 发送WinAPI | 300行 |
| 拖拽绑定     | 250行 |
| 文件管理     | 150行 |
| 菜单快捷键    | 150行 |

总计约 **1400～1700 行**，功能会比较完整且可维护。

**我建议不要压缩代码**，否则 Win32 API、Text 同步滚动、行按钮定位等逻辑会变得难以维护。

这个方案完全可以做成**一个独立的 `cmd_sender.py` 文件**，在 Windows 下直接运行（Python 3.10+），除了 Python 标准库外无需任何第三方依赖。
