# ArkUI-X Hypium使用指导

## 框架概述

DevEco Testing Hypium （以下简称Hypium）是跨平台ArkUI-X的UI自动化测试框架，支持用户使用Python语言为应用编写UI自动化测试脚本，主要包含以下特性：

1. Hypium提供了**控件定位**能力，支持触摸屏、功能键等**模拟输入**功能，适用于多种场景的自动化用例编写需求，支持Android、iOS手机设备。
2. Hypium能够为执行的用例生成详细的**用例执行报告**，并且自动记录设备日志以及执行步骤截图，为用户提供高效、专业的测试执行与结果分析体验。

## 安装向导

**1.安装Python**

推荐从[Python官网](https://www.python.org/)安装Python3.10版本。

**2.安装PyCharm**

推荐从[PyCharm官网](https://www.jetbrains.com.cn/en-us/pycharm/)安装2022.3以后的社区版本。

**3.安装Hypium**

使用安装包离线安装的方式。

需要下载四个安装包，分别为：xdevice、xdevice-devicetest、xdevice-ohos和hypium。

其中，xdevice、xdevice-devicetest和xdevice-ohos从如下地址下载：[下载地址](https://developer.huawei.com/consumer/cn/download/deveco-testing-hypium)，进入链接后选择“DevEco Testing Hypium 6.x.x.x”版本进行下载。这里以6.0.7.210版本为例，下载后解压缩，从压缩包中找到如下三个文件：xdevice-6.0.7.210.tar.gz、xdevice-devicetest-6.0.7.210.tar.gz、xdevice-ohos-6.0.7.210.tar.gz

hypium安装包放在本文档的同级目录中，地址如下：[Hypium安装包](./hypium-7.0.1.0.tar.gz)。

将上述安装包找到之后，按照顺序安装4个安装包，命令如下：

```bash
python -m pip install xdevice-6.0.7.210.tar.gz
python -m pip install xdevice-devicetest-6.0.7.210.tar.gz
python -m pip install xdevice-ohos-6.0.7.210.tar.gz
python -m pip install hypium-7.0.1.0.tar.gz
```

**4.DevEco Testing Hypium插件安装及使用方法**
PyCharm插件安装及使用方法，请参考[DevEco Testing Hypium插件安装及使用方法](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)中的第5部分：《5.DevEco Testing Hypium插件安装及使用方法》。

## 创建Hypium工程

点击PyCharm菜单，选择File -> New Project 进入模板工程创建面板。

![image-1](./ArkUI-X%20Hypium使用指导.assets/1.png)

点击左侧的DevEco Testing Hypium，可以创建Hypium用例模板工程。

![image-2](./ArkUI-X%20Hypium使用指导.assets/2.png)

选择对应模板，配置工程路径以及Python环境参数。点击Create即可创建Hypium测试用例工程。工程目录中包含一个模板用例和一个模板配置文件user_config.xml（仅支持单设备）。

创建完成后的界面如下图所示。

![image-3](./ArkUI-X%20Hypium使用指导.assets/3.png)

若出现未配置Python解释器警告，则点击PyCharm右上角设置，为工程配置环境。

![image-4](./ArkUI-X%20Hypium使用指导.assets/4.png)

打开config/user_config.xml文件，当设备本地连接时需配置如下参数。详细说明见[新增工程配置详细介绍](#新增工程配置详细介绍)。

![image-5](./ArkUI-X%20Hypium使用指导.assets/5.png)

可在PyCharm终端键入python -m hypium.docs查询跨平台Hypium接口文档，并在testcases/Example.py中编写用例，即可完成Hypium工程。代码示例如下

```python
# !/usr/bin/env python
# coding: utf-8
# 导入 Hypium 测试框架的核心模块
from hypium import UiDriver, BY          # UiDriver: UI自动化驱动；BY: 元素定位方式（如ID、文本等）
from devicetest.core.test_case import TestCase, Step  # TestCase: 测试用例基类；Step: 步骤日志装饰器

# 被测应用的包名，请替换为实际应用包名
PACKAGE = "com.example.arkuitest"

# 自定义断言函数：比较实际值与期望值，不等则抛出异常并输出友好信息
def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: actual={actual!r}, expected={expected!r}")

# 测试类必须继承自 TestCase
class Example(TestCase):
    def __init__(self, controllers):
        # 设置测试用例标识（通常为类名）
        self.TAG = self.__class__.__name__
        # 调用父类初始化，传入标识和控制器参数
        TestCase.__init__(self, self.TAG, controllers)
        # 连接设备上的 UiDriver，用于后续UI操作
        self.driver = UiDriver.connect()

    # 测试方法：具体测试逻辑
    def _test_tc_01_click(self):
        # 通过组件ID查找按钮组件
        button = self.driver.find_component(BY.id("clickBtn"))
        # 执行点击操作
        self.driver.click(button)
        # 等待0.5秒，确保UI响应
        self.driver.wait(0.5)

        # 查找显示结果的组件
        result = self.driver.find_component(BY.id("clickResult"))
        # 断言结果文本与预期一致
        assert_equal(result.getText(), "点击成功", "点击结果不符合预期")

    # setup：初始化工作
    def setup(self):
        Step("【setup】启动被测应用")   # Step用于在报告中记录关键步骤
        self.driver.start_app(PACKAGE)  # 启动应用
        self.driver.wait(2)             # 等待2秒至应用完全启动

    # process：核心测试流程，按顺序调用具体的测试方法
    def process(self):
        self._test_tc_01_click()        # 执行测试逻辑
        print("[hypium] Example — PASS") # 测试通过时输出
        self.driver.wait(2)              # 可选等待，便于观察结果

    # teardown：测试结束后清理工作（如停止应用）
    def teardown(self):
        Step("【teardown】停止被测应用")
        self.driver.stop_app(PACKAGE)    # 停止应用

# 当脚本直接运行时，创建测试实例并执行完整生命周期
if __name__ == "__main__":
    test = Example(controllers={"devices": [], "testargs": {}})
    test.setup()        # 执行初始化
    try:
        test.process()  # 执行测试主体
    finally:
        test.teardown() # 确保最终执行清理工作
```

**查找组件边界代码参考**
```python
    def _get_viewport_bounds(self, component):
        """获取组件边界"""
        try:
            bounds = self.driver.get_component_property(component, "bounds")
        except Exception as e:
            raise AssertionError(f"无法通过 get_component_property 获取组件 bounds: {e}")
        if bounds is None or not all(hasattr(bounds, name) for name in ("left", "right", "top", "bottom")):
            raise AssertionError("组件 bounds 属性无效")
        return bounds
```

**判定组件是否位于可见屏幕内代码参考**
```python
    def _get_component_viewport_state(self, component_id, comp):
        """判断组件是否位于当前可见屏幕内，并给出建议滚动方向。"""
        bounds = self._get_viewport_bounds(comp)
        width, height = self.driver.get_display_size()
        center_x = (bounds.left + bounds.right) // 2
        center_y = (bounds.top + bounds.bottom) // 2
        fully_in_viewport = (
            bounds.left >= 0 and bounds.right <= width and
            bounds.top >= 0 and bounds.bottom <= height
        )
        center_in_viewport = 0 <= center_x <= width and 0 <= center_y <= height
        is_visible = fully_in_viewport and center_in_viewport

        suggested_direction = None
        reason = "visible"
        if not is_visible:
            if bounds.top >= height or center_y > height:
                suggested_direction = "UP"
                reason = "below_screen"
            elif bounds.bottom <= 0 or center_y < 0:
                suggested_direction = "DOWN"
                reason = "above_screen"
            elif bounds.left >= width or center_x > width:
                reason = "right_of_screen"
            elif bounds.right <= 0 or center_x < 0:
                reason = "left_of_screen"
            else:
                reason = "partially_outside_viewport"
        return is_visible, suggested_direction
```

**屏幕滚动代码参考**
```python
    def _swipe_screen(self, direction, distance=40, swipe_time=0.6):
        """用绝对屏幕坐标滑动"""
        try:
            self.driver.swipe(direction, distance=distance, swipe_time=swipe_time)
            self.driver.wait(0.5)
            return True
        except Exception as e:
            print(f"[scroll] _swipe_screen('{direction}') 异常: {e}")
            return False
```

##### 新增工程配置详细介绍

```text
<?xml version="1.0" encoding="UTF-8"?>
<user_config>
    <environment>
        <device type="usb-hdc">
            <sn></sn>
        </device>
        <!-- 仅当调试跨平台设备时，增加arkuix标签。 -->
        <arkuix>
	        <!-- platform：调试设备系统android/ios -->
            <platform>android</platform>
            <!-- host：远端server的ip，本地设备非必填。 -->
            <host>127.0.0.1</host>
            <!-- port：远端server的端口，本地设备非必填。 -->
            <port>8017</port>
            <!-- device_id：所连接设备Id。 -->
            <device_id>af7bf9e</device_id>
            <!-- connect_timeout：连接超时时长，默认无需填写。 -->
            <connect_timeout>10</connect_timeout>
            <!-- recv_timeout：接收超时时长，默认无需填写。 -->
            <recv_timeout>60</recv_timeout>
        </arkuix>
    </environment>
    <testcases>
        <dir>/testcases</dir>
    </testcases>
    <loglevel>DEBUG</loglevel>
    <devicelog>ON</devicelog>
</user_config>
```
其中，设备Id的获取方式如下：</br>
Android设备： 在终端中敲入命令adb devices，即可获取到设备的Id。</br>
iOS设备：打开Xcode，在菜单栏选择 Window → Devices and Simulators，在弹出的窗口中，左侧边栏列出的所有连接设备，其右侧显示的“Identifier”即为该设备的Id</br>

## 创建ETS测试工程

根据https://gitcode.com/arkui-x/cli/blob/master/README.md官方文档配置ACE Tools工具链。

**创建ETS测试工程**

打开命令行，键入ace create arkuitest(包名)，创建工程(SDK按本机环境选择)。

![image-6](./ArkUI-X%20Hypium使用指导.assets/6.png)

**编写ETS页面**

Python 用例依赖 ETS 页面中的组件 ID。

使用DevEco Studio打开已创建工程，编写ETS 测试 UI 代码放在entry/src/main/ets/pages目录下。

![image-7](./ArkUI-X%20Hypium使用指导.assets/7.png)

界面代码参考如下：

```ts
@Entry
@Component
struct Index {
  @State clickResult: string = '未点击'

  build() {
    Column({ space: 12 }) {
      Button('点击按钮')
        .id('clickBtn')
        .width('88%')
        .height(48)
        .onClick(() => {
          this.clickResult = '点击成功'
        })

      Text(this.clickResult)
        .id('clickResult')
        .fontSize(16)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }
}
```

要求：

1. 可操作组件必须设置唯一的 `.id(...)`。
2. 校验结果必须有独立组件显示。
3. Python 用例中的 `BY.id(...)` 必须和 ETS 中的 `id` 一致。

## 启动端对端测试

1.连接Android设备，打开终端，进入deveco工程目录，键入ace test apk --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --socket命令，等待测试工程安装、启动。

![image-8](./ArkUI-X%20Hypium使用指导.assets/8.png)

##### iOS

```bash
ace test ios --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --device <device_id> --socket
```

##### Android

```bash
ace test apk --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --device <device_id> --socket
```

其中，device子命令是可选的，只有当多个设备连接在电脑上时才需要指定。

socket、device子命令详细用法见https://gitcode.com/arkui-x/cli/blob/master/README.md#ace-test。

2.执行PyCharm中用例
使用PyCharm打开Example.py文件，点击运行按钮。

![image-9](./ArkUI-X%20Hypium使用指导.assets/9.png)

3.结果显示

1. Python 用例执行后输出 `Example — PASS`。
2. ETS 页面中的 `clickResult` 从“未点击”变为“点击成功”。
3. 应用退出。

## 已有Hypium测试工程跨平台运行更改

1.增加config/user_config.xml文件中配置。platform、package_name、device_id等。

![image-10](./ArkUI-X%20Hypium使用指导.assets/10.png)

2.若xts用例的执行影响Hypium测试，将下图中xts执行语句注释即可。

![image-13](./ArkUI-X%20Hypium使用指导.assets/11.png)

3.需由Deveco Studio终端键入命令，启动测试应用。

## 常见问题

**ArkUI-X hypium not found**

原因：

- `hypium` 没有放到 `venv/thirdparty/hypium`

处理：

- 检查 `venv/thirdparty/hypium/__init__.py` 是否存在

**iOS 无法连接**

原因：

- user_config.xml中device_id 未配置
- 没有先执行 `ace test ios ... --socket`

处理：

- 填写正确的 iOS 设备号
- 重新执行 `ace test --socket`

**Android 多设备连接错误**

原因：

- 多台设备同时连接，但user_config.xml中device_id 未配置

处理：

- 在user_config.xml中配置正确的device_id

**组件查找失败**

原因：

- ETS 页面没有对应的 `id`
- Python 用例中的 `BY.id(...)` 与 ETS 中的 `id` 不一致

处理：

- 检查 `clickBtn`、`clickResult` 等组件 ID 是否一致
