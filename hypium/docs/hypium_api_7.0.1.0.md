**配套Hypium版本: 7.0.1.0**

# hypium.action.device.uidriver

**类型**: `module`

## UiDriver

**类型**: `class`

**描述**

设备Ui测试核心功能类, 提供控件查找/设备点击/滑动操作, app启动停止等常用功能

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.action.device.uidriver import UiDriver
```

### connect

```python
def connect() -> 'UiDriver'
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

在非hypium用例类中快速创建driver, hypium用例类中请使用UiDriver(self.device1)创建UiDriver
默认连接第一可用的设备
跨平台场景连接设备，需要配置user_config.xml文件，详细说明请参考《ArkUI-X Hypium使用指导》

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | -        |

**返回值**

无返回值描述

**示例**

```python
# 连接默认设备
driver = UiDriver.connect()
# 注意结束driver使用后需要调用driver.close清理端口, 释放资源
driver.close()
```

### close

```python
def close()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

关闭驱动, 断开与设备的连接并清理连接资源。
仅当使用UiDriver.connect方式创建设备驱动，并且驱动对象不再使用时调用。
如果在Hypium框架用例工程中创建驱动则无需主动调用，任务直接结束会自动完成释放。

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 通过UiDriver.connect方式连接
driver = UiDriver.connect()
# 调用driver执行操作
driver.go_home()
# 不再使用driver时关闭
driver.close()
```

### get_device_type

```python
def get_device_type() -> str
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

读取设备类型

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

接口返回如下字符串中的一种："phone", "tablet", "wearable", "sdcard", "nosdcard", "default"

**示例**

```python
# 读取设备类型
deviceType = driver.get_device_type()
```

### shell

```python
def shell(cmd: str, timeout: float = 60) -> str
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

在设备端shell中执行命令

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| cmd | 执行的shell命令 |
| timeout | 超时时间, 单位秒 |

**返回值**

命令执行后的回显内容

**示例**

```python
# 在设备shell中执行命令ls -l
echo = driver.shell("ls -l")
# 在设备shell中执行命令top, 设置10秒超时时间
echo = driver.shell("top", timeout=10)
```

### wait

```python
def wait(wait_time: float)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

等待wait_time秒

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| wait_time | 等待秒数 |

**返回值**

无返回值描述

**示例**

```python
# 等待5秒钟
driver.wait(5)
```

### start_app

```python
def start_app(package_name: str, page_name: str = None, params: str = "", wait_time: float = 1)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据包名启动指定的app

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| package_name | 应用程序包名(bundle_name) |
| page_name | 应用内页面名称(iOS平台该参数无效) |
| params | 传递给启动命令行参数 |
| wait_time | 发送启动指令后，等待app启动的时间 |

**返回值**

无返回值描述

**示例**

```python
# 启动包名为com.example.app应用的MainAbility
driver.start_app("com.example.app", "MainAbility")
```

### stop_app

```python
def stop_app(package_name: str, wait_time: float = 0.5)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

停止指定的应用

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| package_name | 应用程序包名 |
| wait_time | 停止app后延时等待的时间, 单位为秒 |

**返回值**

无返回值描述

**示例**

```python
# 停止包名为com.example.app的应用
driver.stop_app("com.example.app")
```

### uninstall_app

```python
def uninstall_app(package_name: str)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

卸载App

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| package_name | 需要卸载的app包名 |

**返回值**

无返回值描述

**示例**

```python
driver.uninstall_app("com.ohos.devicetest")
```

### clear_app_data

```python
def clear_app_data(package_name: str)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

清除app的数据

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| package_name | app包名 |

**返回值**

无返回值描述

**示例**

```python
# 清除包名为com.tencent.mm的应用的所有数据
driver.clear_app_data("com.tencent.mm")
```

### drag

```python
def drag(start: Union[ISelector, tuple, IUiComponent], end: Union[ISelector, tuple, IUiComponent], area: Union[ISelector, IUiComponent] = None, drag_time: float = 1, speed: int = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据指定的起始和结束位置执行拖拽操作，起始和结束的位置可以为控件或者屏幕坐标

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| start | 拖拽起始位置，支持三种类型：<br>1. BY控件选择器<br>2. 控件对象<br>3. 屏幕坐标（通过tuple类型指定，例如(100, 200)， 其中100为x轴坐标，200为y轴坐标，<br>或相对于区域长度和宽度的比例坐标，例如(0.1, 0.2)。) |
| end | 拖拽结束位置<br>1. BY控件选择器<br>2. 控件对象<br>3. 屏幕坐标（通过tuple类型指定，例如(100, 200)， 其中100为x轴坐标，200为y轴坐标，<br>或者相对于区域长度和宽度的比例坐标，例如(0.1, 0.2)。) |
| area | 拖拽操作区域，可以为控件BY.text("画布"), 或者使用find_component找到的控件对象。<br>目前仅在start或者end为坐标时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域<br>的相对位置坐标。 |
| drag_time | 拖动的时间， 默认为1s |
| speed | 拖拽速度，取值范围为200-40000的整数，指定速度时, drag_time不生效 |

**返回值**

无返回值描述

**示例**

```python
# 拖拽文本为"文件.txt"的控件到文本为"上传文件"的控件
driver.drag(BY.text("文件.txt"), BY.text("上传文件"))
# 拖拽id为"start_bar"的控件到坐标(100, 200)的位置, 拖拽时间为2秒
driver.drag(BY.key("start_bar"), (100, 200), drag_time=2)

# 在id为"Canvas"的控件上执行拖拽操作，从"Canvas"控件中(0.1， 0.5)的位置拖拽到(0.9, 0.5)位置。
# 假如"Canvas"控件左上角坐标(100, 100), 宽度为200，高度为50，此操作等价于
# driver.drag((100 + 0.1 * 200, 100 + 0.5 * 50), (100 + 0.9 * 200, 100 + 0.5 * 50))
driver.drag((0.1, 0.5), (0.9, 0.5), area=BY.id("Canvas"))

# 在滑动条上执行拖拽操作, 以滑动条组件左上角为原点, 从滑动条区域中的(10, 10)拖拽到(10, 200)。
# 假设滑动条左上角坐标为(500, 500), 此操作等价于driver.drag((500 + 10, 500 + 10), (500 + 10, 500 + 200))
driver.drag((10, 10), (10, 200), area=BY.type("Slider"))
```

### touch

```python
def touch(target: Union[ISelector, IUiComponent, tuple], mode: str = "normal", scroll_target: Union[ISelector, IUiComponent] = None, wait_time: float = 0.1, offset: tuple = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据选定的控件或者坐标位置执行点击操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 需要点击的目标，可以为控件(通过By类指定)或者屏幕坐标(通过tuple类型指定，<br>例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象 |
| mode | 点击模式，目前支持:<br>"normal" 点击<br>"long" 长按（长按后放开）<br>"double" 双击 |
| scroll_target | 指定可滚动的控件，在该控件中滚动搜索指定的目标控件target。仅在<br>target为`By`对象时有效 |
| wait_time | 点击后等待响应的时间，默认0.1s |
| offset | 点击坐标相对目标控件的偏移, 例如(0.5, 0.5)表示点击目标中心, (0, 0)表示左上角, (1, 1)表示右下角<br>支持负数, 每个方向的偏移值取值范围为[-1, 1] |

**返回值**

无返回值描述

**示例**

```python
# 点击文本为"hello"的控件
driver.touch(BY.text("hello"))
# 点击(100, 200)的位置
driver.touch((100, 200))
# 点击比例坐标为(0.8, 0.9)的位置
driver.touch((0.8, 0.9))
# 双击确认按钮(控件文本为"确认", 类型为"Button")
driver.touch(BY.text("确认").type("Button"), mode="double")
# 在类型为Scroll的控件上滑动查找文本为"退出"的控件并点击
driver.touch(BY.text("退出"), scroll_target=BY.type("Scroll"))
# 长按比例坐标为(0.8, 0.9)的位置
driver.touch((0.8, 0.9), mode="long")
```

### press_combination_key

```python
def press_combination_key(key1: Union[KeyCode, int], key2: Union[KeyCode, int], key3: Union[KeyCode, int] = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

按下组合键, 支持2键或者3键组合

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| key1 | 组合键第一个按键 |
| key2 | 组合键第二个按键 |
| key3 | 组合键第三个按键 |

**返回值**

无返回值描述

**示例**

```python
# 同时按下ctrl, shift和F键
driver.press_combination_key(KeyCode.CTRL_LEFT, KeyCode.SHIFT_LEFT, KeyCode.F)
```

### press_key

```python
def press_key(key_code: Union[KeyCode, int], key_code2: Union[KeyCode, int] = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

按下指定按键(按组合键请使用press_combination_key)

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| key_code | 需要按下的按键编码 |
| key_code2 | 需要按下的按键编码 |

**返回值**

无返回值描述

**示例**

```python
# 按下F键
driver.press_key(KeyCode.F)
```

### press_home

```python
def press_home()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

按下HOME键

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 按下home键
driver.press_home()
```

### go_home

```python
def go_home()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

返回桌面(等价于按下HOME键)

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 返回桌面
driver.go_home()
```

### go_back

```python
def go_back()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

返回上一级

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 返回上一级
driver.go_back()
```

### press_power

```python
def press_power()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

按下电源键

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 按下电源键
driver.press_power()
```

### slide

```python
def slide(start: Union[ISelector, tuple], end: Union[ISelector, tuple], area: Union[ISelector, IUiComponent] = None, slide_time: float = DEFAULT_SLIDE_TIME)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据指定的起始和结束位置执行滑动操作，起始和结束的位置可以为控件或者屏幕坐标。该接口用于执行较为精准的滑动操作。

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| start | 滑动起始位置，可以为控件BY.text("滑块")或者坐标(100, 200), 或者使用find_component找到的控件对象 |
| end | 滑动结束位置，可以为控件BY.text("最大值")或者坐标(100, 200), 或者使用find_component找到的控件对象 |
| area | 滑动操作区域，可以为控件BY.text("画布")。目前仅在start或者end为坐标<br>时生效，指定区域后，当start和end为坐标时，其坐标将被视为相对于指定的区域<br>的相对位置坐标。 |
| slide_time | 滑动操作总时间，单位秒 |

**返回值**

无返回值描述

**示例**

```python
# 从类型为Slider的控件滑动到文本为最大的控件
driver.slide(BY.type("Slider"), BY.text("最大"))
# 从坐标100, 200滑动到300，400
driver.slide((100, 200), (300, 400))
# 从坐标100, 200滑动到300，400, 滑动时间为3秒
driver.slide((100, 200), (300, 400), slide_time=3)
# 在类型为Slider的控件上从(0, 0)滑动到(100, 0)
driver.slide((0, 0), (100, 0), area = BY.type("Slider"))
```

### swipe

```python
def swipe(direction: str, distance: int = 60, area: Union[ISelector, IUiComponent] = None, side: str = None, start_point: tuple = None, swipe_time: float = 0.3, speed: int = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

在屏幕上或者指定区域area中执行朝向指定方向direction的滑动操作。该接口用于执行不太精准的滑动操作。

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| direction | 滑动方向，目前支持:<br>UiParam.LEFT 左滑<br>UiParam.RIGHT 右滑<br>UiParam.UP 上滑<br>UiParam.DOWN 下滑 |
| distance | 相对滑动区域总长度的滑动距离，范围为1-100, 表示滑动长度为滑动区域总长度的1%到100%， 默认为60 |
| area | 通过控件指定的滑动区域 |
| side | 滑动位置， 指定滑动区域内部(屏幕内部)执行操作的大概位置，支持:<br>UiParam.LEFT 靠左区域<br>UiParam.RIGHT 靠右区域<br>UiParam.TOP 靠上区域<br>UiParam.BOTTOM 靠下区域 |
| start_point | 滑动起始点, 默认为None, 表示在区域中间位置执行滑动操作, 可以传入滑动起始点坐标，支持使用(0.5, 0.5)<br>这样的比例坐标。当同时传入side和start_point的时候, |
| swipe_time | 滑动时间（s)， 默认0.3s |
| speed | 滑动速度，取值范围为200-40000的整数，单位像素/秒, 指定速度时, swipe_time不生效 |

**返回值**

无返回值描述

**示例**

```python
# 在屏幕上向上滑动, 距离40
driver.swipe(UiParam.UP, distance=40)
# 在屏幕上向右滑动, 滑动时间为0.1秒
driver.swipe(UiParam.RIGHT, swipe_time=0.1)
# 在屏幕起始点为比例坐标为(0.8, 0.8)的位置向上滑动，距离30
driver.swipe(UiParam.UP, 30, start_point=(0.8, 0.8))
# 在屏幕左边区域向下滑动， 距离30
driver.swipe(UiParam.DOWN, 30, side=UiParam.LEFT)
# 在屏幕右侧区域向上滑动，距离30
driver.swipe(UiParam.UP, side=UiParam.RIGHT)
# 在类型为Scroll的控件中向上滑动
driver.swipe(UiParam.UP, area=BY.type("Scroll"))
```

### find_component

```python
def find_component(target: ISelector, scroll_target: ISelector = None) -> IUiComponent
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据BY指定的条件查找控件, 返回满足条件的第一个控件对象

在跨平台场景下，该接口查找范围是整个页面，包含不可见区域。

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 使用By对象描述的查找条件 |
| scroll_target | 滑动scroll_target控件, 搜索target |

**返回值**

返回控件对象IUiComponent, 如果没有找到满足条件的控件，则返回None

**示例**

```python
# 查找类型为button的第一个控件对象
component = driver.find_component(BY.type("button"))
# 获取控件对象的文本
text = component.getText()
# 在类型为Scroll的控件上滚动查找文本为"拒绝"的控件
component = driver.find_component(BY.text("拒绝"), scroll_target=BY.type("Scroll"))
```

### find_all_components

```python
def find_all_components(target: ISelector, index: int = None) -> Union[IUiComponent, List[IUiComponent]]
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

根据BY指定的条件查找控件, 返回满足条件的所有控件对象列表, 或者列表中第index个控件对象

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 使用By对象描述的查找条件 |
| index | 默认为None, 表示返回所有控件列表，当传入整数时, 返回列表中第index个对象 |

**返回值**

返回控件对象IUiComponent或者控件对象列表, 例如[component1, component2], 每个
如果没有找到满足条件的控件，则返回None

**示例**

```python
# 查找所有类型为"button"的控件
components = driver.find_all_components(BY.type("Button"))
# 查找满足条件的第3个控件(index从0开始)
component = driver.find_all_components(BY.type("Button"), 2)
# 点击控件
driver.touch(component)
```

### get_display_size

```python
def get_display_size() -> (int, int)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

返回屏幕分辨率

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

(宽度, 高度)

**示例**

```python
# 获取屏幕分辨率
width, height = driver.get_display_size()
```

### get_component_property

```python
def get_component_property(component: Union[ISelector, IUiComponent], property_name: str) -> Any
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

获取指定控件属性

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| component | By对象指定的控件或者IUiComponent控件对象 |
| property_name | 属性名称, 目前支持:<br>"id", "text", "type", "enabled", "focused", "clickable", "scrollable"<br>"checked", "checkable", "bounds", "selected" |

**返回值**

指定控件的指定属性值

**示例**

```python
# 获取类型为"checkbox"的控件的checked状态
checked = driver.get_component_property(BY.type("Toggle"), "checked")
# 获取id为"text_container"的控件的文本属性
text = driver.get_component_property(BY.key("text_container"), "text")
```

### get_component_pos

```python
def get_component_pos(component: Union[ISelector, IUiComponent]) -> (int, int)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

获取指定控件的中心点坐标

**支持平台**：Android 、iOS

**参数说明**

| 参数名称  | 参数说明                                 |
| --------- | ---------------------------------------- |
| component | By对象指定的控件或者IUiComponent控件对象 |

**返回值**

指定控件的中心点坐标

**示例**

```python
# 获取id为"text_container"的控件的中心点坐标
text = driver.get_component_pos(BY.key("text_container"))
```

### input_text

```python
def input_text(component: Union[ISelector, IUiComponent], text: str)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

向指定控件中输入文本内容

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| component | 需要输入文本的控件，可以使用ISelector对象，<br>或者使用find_component找到的控件对象 |
| text | 需要输入的文本 |

**返回值**

无返回值描述

**示例**

```python
# 在类型为"TextInput"的控件中输入文本"hello world"
driver.input_text(BY.type("TextInput"), "hello world")
```

### pinch_in

```python
def pinch_in(area: Union[ISelector, IUiComponent, Rect], scale: float = 0.4, direction: str = "diagonal", **kwargs)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

在控件上捏合缩小

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| area | 手势执行的区域 |
| scale | 缩放的比例, [0, 1], 值越小表示缩放操作距离越长, 缩小的越多 |
| direction | 双指缩放时缩放操作方向, 支持<br>"diagonal" 对角线滑动<br>"horizontal" 水平滑动 |
| kwargs | 可选滑动配置参数<br>dead_zone_ratio 缩放操作时控件靠近边界不可操作的区域占控件长度/宽度的比例, 默认为0.2, 调节范围为(0, 0.5) |

**返回值**

无返回值描述

**示例**

```python
# 在类型为Image的控件上进行双指捏合缩小操作
driver.pinch_in(BY.type("Image"))
# 在类型为Image的控件上进行双指捏合缩小操作, 设置水平方向捏合
driver.pinch_in(BY.type("Image"), direction="horizontal")
```

### fling

```python
def fling(direction: str, speed: str = "fast")
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

执行抛滑操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| direction | 滑动方向，目前支持:<br>"LEFT" 左滑<br>"RIGHT" 右滑<br>"UP" 上滑<br>"DOWN" 下滑 |
| speed | 滑动速度, 目前支持三档:<br>UiParam.FAST 快速<br>UiParam.NORMAL 正常速度<br>UiParam.SLOW 慢速 |

**返回值**

无返回值描述

**示例**

```python
# 向上抛滑
driver.fling("UP")
# 向下慢速抛滑
driver.fling("DOWN", speed=UiParam.SLOW)
```

### inject_gesture

```python
def inject_gesture(gesture: Gesture, speed: int = 2000)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

执行自定义滑动手势操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| gesture | 描述手势操作的Gesture对象 |
| speed | 滑动速率，取值范围为200-40000的整数，默认值为2000，单位：px/s。 |

**返回值**

无返回值描述

**示例**

```python
from hypium import Gesture
# 创建一个gesture对象
gesture = Gesture()
# 获取控件计算器的位置
pos = driver.findComponent(BY.text("计算器")).getBoundsCenter()
# 获取屏幕尺寸
size = driver.getDisplaySize()
# 起始位置, 长按2秒
gesture.start(pos.to_tuple(), 2)
# 移动到屏幕边缘
gesture.move_to(Point(size.X - 20, int(size.Y / 2)).to_tuple())
# 停留2秒
gesture.pause(2)
# 移动到(360, 500)的位置
gesture.move_to(Point(360, 500).to_tuple())
# 停留2秒结束
gesture.pause(2)
# 执行gesture对象描述的操作
driver.inject_gesture(gesture)
```

### inject_multi_finger_gesture

```python
def inject_multi_finger_gesture(gestures: List[Gesture], speed: int = 2000)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

注入多指手势操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| gestures | 表示单指手势操作的Gesture对象列表，每个Gesture对象描述一个手指的操作轨迹。 |
| speed | 滑动速率，取值范围为200-40000的整数，默认值为2000，单位：px/s。 |

**返回值**

无返回值描述

**示例**

```python
# 导入Gesture对象
from hypium import Gesture
# 创建手指1的手势, 从(0.4, 0.4)的位置移动到(0.2, 0.2)的位置
gesture1 = Gesture().start((0.4, 0.4)).move_to((0.2, 0.2), interval=1)
# 创建手指2的手势, 从(0.6, 0.6)的位置移动到(0.8, 0.8)的位置
gesture2 = Gesture().start((0.6, 0.6)).move_to((0.8, 0.8), interval=1)
# 注入多指操作
driver.inject_multi_finger_gesture((gesture1, gesture2))
```

### two_finger_swipe

```python
def two_finger_swipe(start1: tuple, end1: tuple, start2: tuple, end2: tuple, duration: float = 0.5)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

执行双指滑动操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| start1 | 手指1起始坐标 |
| end1 | 手指1起始坐标 |
| start2 | 手指2起始坐标 |
| end2 | 手指2结束坐标 |
| duration | 滑动操作持续时间 |

**返回值**

无返回值描述

**示例**

```python
# 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8)
driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8))
# 执行双指滑动操作, 手指1从(0.4, 0.4)滑动到(0.2, 0.2), 手指2从(0.6, 0.6)滑动到(0.8, 0.8), 持续时间3秒
driver.two_finger_swipe((0.4, 0.4), (0.2, 0.2), (0.6, 0.6), (0.8, 0.8), duration=3)
# 查找Image类型控件
comp = driver.find_component(BY.type("Image"))
```

### click

```python
def click(target: Union[ISelector, IUiComponent, tuple], offset=None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

模拟点击操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 点击操作目标 |
| offset | 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1<br>如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置 |

**返回值**

无返回值描述

**示例**

```python
# 点击蓝牙控件
driver.click(BY.text("蓝牙"))
# 点击蓝牙控件左上角(偏移0, 0)
driver.click(BY.text("蓝牙"), offset=(0, 0))
# 点击蓝牙控件中偏移为0.8, 0.8的位置
driver.click(BY.text("蓝牙"), offset=(0.8, 0.8))
# 点击蓝牙控件正上方, 同蓝牙控件距离为蓝牙控件高度的80%的位置(0.5, -0.8)
driver.click(BY.text("蓝牙"), offset=(0.5, -0.8))
```

### double_click

```python
def double_click(target: Union[ISelector, IUiComponent, tuple], offset=None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

模拟点击操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 点击操作目标 |
| offset | 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1<br>如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置 |

**返回值**

无返回值描述

**示例**

```python
# 点击蓝牙控件
driver.double_click(BY.text("测试按钮"))
# 点击蓝牙控件左上角(偏移0, 0)
driver.double_click(BY.text("测试按钮"), offset=(0, 0))
```

### long_click

```python
def long_click(target: Union[ISelector, IUiComponent, tuple], offset=None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `UiDriver`

**类型**: 函数

**描述**

执行长按操作

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| target | 需要点击的目标，可以为控件查找条件, 控件对象或者屏幕坐标(通过tuple类型指定，<br>例如(100, 200)， 其中100为x轴坐标，200为y轴坐标), 或者使用find_component找到的控件对象 |
| offset | 点击坐标在目标控件区域的偏移值, 不设置时默认为(0.5, 0.5), 表示控件中心。支持设置范围是0到1<br>如(0.1, 0.1)表示点击目标左上角为坐标原点x方向10%, y方向10%的位置 |

**返回值**

无返回值描述

**示例**

```python
# 长按文本为"按钮"的控件
driver.long_click(BY.text("按钮"))
# 长按(100, 200)的位置
driver.long_click((100, 200))
# 长按文本为"设置"的控件左上角(偏移0, 0)
driver.long_click(BY.text("设置"), offset=(0, 0))
```

### Screen

**类型**: `class`

**描述**

设备屏幕功能类，提供唤醒屏幕、关闭屏幕、获取屏幕点亮状态、屏幕旋转等功能。

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.action.device.uidriver import UiDriver
```

#### close

```python
def close()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `Screen`

**类型**: 函数

**描述**

关闭屏幕, 如果屏幕已经关闭则无动作

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| -------- | -------- |
| -        | -        |

**返回值**

无返回值描述

**示例**

```python
# 关闭屏幕
driver.Screen.close()
```

#### is_on

```python
def is_on()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `Screen`

**类型**: 函数

**描述**

获取屏幕是否亮屏

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| -------- | -------- |
| -        | -        |

**返回值**

返回bool类型，True表示亮屏，False表示息屏

**示例**

```python
# 获取屏幕是否亮屏
driver.Screen.is_on()
```

#### wake_up

```python
def wake_up()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `Screen`

**类型**: 函数

**描述**

唤醒屏幕

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| -------- | -------- |
| -        | -        |

**返回值**

无返回值描述

**示例**

```python
# 唤醒屏幕
driver.Screen.wake_up()
```

#### set_rotation

```python
def set_rotation(rotation: DisplayRotation)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `Screen`

**类型**: 函数

**描述**

将设备的屏幕显示方向设置为指定的显示方向。

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明                                        |
| -------- | ----------------------------------------------- |
| rotation | 屏幕旋转方向, 取值范围为DisplayRotation枚举值。 |

**返回值**

无返回值描述

**示例**

```python
# 顺时针选择90度
driver.Screen.set_rotation(DisplayRotation.ROTATION_90)
# 顺时针选择180度
driver.Screen.set_rotation(DisplayRotation.ROTATION_180)
```

### ScreenLock

**类型**: `class`

**描述**

设备锁屏功能类，提供获取锁屏状态等功能。

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.action.device.uidriver import UiDriver
```

#### is_locked

```python
def is_locked()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `ScreenLock`

**类型**: 函数

**描述**

获取系统是否在锁屏状态

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| -------- | -------- |
| -        | -        |

**返回值**

返回bool类型，True表示在锁屏状态，False表示不在锁屏状态

**示例**

```python
# 获取系统是否在锁屏状态
driver.ScreenLock.is_locked()
```

### TimeLocale

**类型**: `class`

**描述**

系统语言地区功能类，提供获取系统语言地区等功能。

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.action.device.uidriver import UiDriver
```

#### get_language

```python
def get_language()
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `TimeLocale`

**类型**: 函数

**描述**

获取系统语言地区

**支持平台**：Android

**参数说明**

| 参数名称 | 参数说明 |
| -------- | -------- |
| -        | -        |

**返回值**

返回系统语言地区，字符串类型

**示例**

```python
# 获取系统语言地区
driver.TimeLocale.get_language()
```

### Assert

**类型**: `class`

**描述**

基础断言操作

**支持平台**：Android、iOS

**导入方式**

```python
from hypium.action.device.uidriver import UiDriver
```

#### not_equal

```python
def not_equal(actual: Any, expect: Any = True, fail_msg: str = None)
```

**归属模块**: `hypium.action.device.uidriver`

**归属类**: `Assert`

**类型**: 函数

**描述**

检查实际值于预期值不等

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| actual | 实际值 |
| expect | 期望值 |
| fail_msg | 检查失败时打印的内容 |

**返回值**

无返回值描述

**示例**

```python
# 检查实际值和期望值不相等
driver.Assert.not_equal(actual, "a")
```

# hypium.model.basic_data_type

**类型**: `module`

## Rect

**类型**: `class`

**描述**

表示矩形的区域的位置

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import Rect
```

### get_size

```python
def get_size() -> (int, int)
```

**归属模块**: `hypium.model.basic_data_type`

**归属类**: `Rect`

**类型**: 函数

**描述**

获取矩形区域的宽度和长度

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

tuple类型,  (width, height)

**示例**

```python
# 无示例
```

### get_center

```python
def get_center() -> (int, int)
```

**归属模块**: `hypium.model.basic_data_type`

**归属类**: `Rect`

**类型**: 函数

**描述**

获取矩形区域的中心点坐标

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

(center_x, center_y)

**示例**

```python
# 无示例
```

### get_pos

```python
def get_pos(x_offset: float, y_offset: float) -> (int, int)
```

**归属模块**: `hypium.model.basic_data_type`

**归属类**: `Rect`

**类型**: 函数

**描述**

获取矩形区域内部指定位置的屏幕坐标

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| x_offset | 矩形区域内部x方向偏移, 支持相对距离[0, 1], 大于1表示固定像素长度 |
| y_offset | 矩形区域内部y方向偏移, 支持相对距离[0, 1], 大于1表示固定像素长度 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

## Point

**类型**: `class`

**描述**

表示一个坐标点

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import Point
```

### to_tuple

```python
def to_tuple()
```

**归属模块**: `hypium.model.basic_data_type`

**归属类**: `Point`

**类型**: 函数

**描述**

将Point对象转换为tuple类型, (x, y)

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

## MatchPattern

**类型**: `class`

**描述**

指定BY选择器的匹配模式, 例如BY.text("app_", MatchPattern.STARTS_WITH)
```
from hypium.model import MatchPattern
```

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import MatchPattern
```

## DisplayRotation

**类型**: `class`

**描述**

屏幕旋转角度，在UiDriver.setDisplayRotation中使用
```
from hypium.model import DisplayRotation
```

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import DisplayRotation
```

## KeyCode

**类型**: `class`

**描述**

键盘码
```
from hypium.model import KeyCode
```

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import KeyCode
```

## UiParam

**类型**: `class`

**描述**

Ui操作控制相关的常量
```
from hypium.model import UiParam
```

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.model.basic_data_type import UiParam
```

# hypium.uidriver.by

**类型**: `module`

## By

**类型**: `class`

**描述**

控件选择器, 在点击/查找控件接口中指定控件, 例如BY.text("中文").key("xxxx")
注意该类的方法只能顺序传参, 不支持通过key=value的方式指定参数

**支持平台**：Android 、iOS

**导入方式**

```python
from hypium.uidriver.by import By
```

### text

```python
def text(txt: str, mp: MatchPattern = MatchPattern.EQUALS) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过文本选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| txt | 控件的text属性值 |
| mp | 匹配模式, MatchPattern枚举变量 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### key

```python
def key(key: str) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过key选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| key | 控件的key属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### id

```python
def id(compId: str) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过id选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| - | - |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### type

```python
def type(tp: str) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过控件类型选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| tp | 控件的类型属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### checkable

```python
def checkable(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过checkable属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的checkable属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### longClickable

```python
def longClickable(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

通过longClickable属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的longClickable属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### clickable

```python
def clickable(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定clickable属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的clickable属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### scrollable

```python
def scrollable(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定scrollable属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的scrollable属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### enabled

```python
def enabled(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定enabled属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的enabled属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### focused

```python
def focused(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定focused属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的focused属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### selected

```python
def selected(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定selected属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的selected属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### checked

```python
def checked(b: bool = True) -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定checked属性选择控件

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| b | 目标控件的checked属性值 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### isBefore

```python
def isBefore(by: 'By') -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定控件位于另一个控件之前

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| by | 通过By指定的另外一个控件 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### isAfter

```python
def isAfter(by: 'By') -> 'By'
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定控件位于另一个控件之后

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| by | 通过By指定的另外一个控件 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```

### within

```python
def within(by: 'By')
```

**归属模块**: `hypium.uidriver.by`

**归属类**: `By`

**类型**: 函数

**描述**

指定目前控件位于另外一个控件中

**支持平台**：Android 、iOS

**参数说明**

| 参数名称 | 参数说明 |
| --- | --- |
| by | 通过By指定的另外一个控件 |

**返回值**

无返回值描述

**示例**

```python
# 无示例
```
