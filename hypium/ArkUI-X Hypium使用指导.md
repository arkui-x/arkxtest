# ArkUI-X Hypium使用指导

## 框架概述

DevEco Testing Hypium （以下简称Hypium）是跨平台ArkUI-X的UI自动化测试框架，支持用户使用Python语言为应用编写UI自动化测试脚本，主要包含以下特性：

1. Hypium提供了**控件定位**能力，支持触摸屏、功能键等**模拟输入**功能，能够覆盖多类场景上的自动化用例编写需求，支持Android、iOS手机设备。
2. Hypium能够为执行的用例生成详细的**用例执行报告**，并且自动记录设备日志以及执行步骤截图，为用户提供高效和专业的测试用例执行和结果分析体验。

## 安装向导

**1.安装Python**

推荐从[Python官网](https://www.python.org/)安装Python3.10版本。

**2.安装PyCharm**

推荐从[PyCharm官网](https://www.jetbrains.com.cn/en-us/pycharm/)安装2022.3以后的社区版本。

**3.安装Hypium**

[下载DevEco Testing Hypium安装包]()。下载后解压该安装包。进入解压后的文件目录执行以下命令，按照顺序安装4个安装包（命令中版本号仅做示例，请以实际版本号为准）。

```python
python -m pip install xdevice-6.0.6.210.tar.gz
python -m pip install xdevice-devicetest-6.0.6.210.tar.gz
python -m pip install xdevice-ohos-6.0.6.210.tar.gz
python -m pip install hypium-7.0.1.0.tar.gz

# 此版本仅作为示例，实际请根据项目使用的版本选择
```

## 创建Hypium工程

点击PyCharm顶部，选择File -> New Project 进入模板工程创建面板。

![image-1](./ArkUI-X%20Hypium使用指导.assets/1.png)

点击左侧的DevEco Testing Hypium，可以创建Hypium用例模板工程。

![image-2](./ArkUI-X%20Hypium使用指导.assets/2.png)

选择对应模板，配置工程路径以及Python环境参数，点击Create即可创建Hypium测试用例工程。工程目录中包含一个模板用例和一个模板配置文件user_config.xml（仅支持单设备）。

创建完成后的界面如下图所示。

![image-3](./ArkUI-X%20Hypium使用指导.assets/3.png)

若产生警告无配置Python解释器，则点击PyCharm右上角设置，为工程配置环境。

![image-4](./ArkUI-X%20Hypium使用指导.assets/4.png)

打开config/user_config.xml文件，当设备本地连接时需配置如下参数。详细说明见[新增工程配置详细介绍](#新增工程配置详细介绍)。

![image-5](./ArkUI-X%20Hypium使用指导.assets/5.png)

可在PyCharm终端键入python -m hypium.docs查询跨平台hypium接口文档，编写testcases/Example.py中用例，即完成Hypium工程。代码示例如下

```python
# !/usr/bin/env python
# coding: utf-8
from hypium import UiDriver, BY
from devicetest.core.test_case import TestCase, Step
PACKAGE = "com.example.arkuitest"

def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: actual={actual!r}, expected={expected!r}")
        
class Example(TestCase):
    def __init__(self, controllers):
        self.TAG = self.__class__.__name__
        TestCase.__init__(self, self.TAG, controllers)
        self.driver = UiDriver.connect()

    def _test_tc_01_click(self):
        button = self.driver.find_component(BY.id("clickBtn"))
        self.driver.click(button)
        self.driver.wait(0.5)

        result = self.driver.find_component(BY.id("clickResult"))
        assert_equal(result.getText(), "点击成功", "点击结果不符合预期")

    def setup(self):
        Step("【setup】启动被测应用")
        self.driver.start_app(PACKAGE)
        self.driver.wait(2)

    def process(self):
        self._test_tc_01_click()
        print("[hypium] Example — PASS")
        self.driver.wait(2)

    def teardown(self):
        Step("【teardown】停止被测应用")
        self.driver.stop_app(PACKAGE)


if __name__ == "__main__":
    test = Example(controllers={"devices": [], "testargs": {}})
    # test.setup()
    try:
        test.process()
    finally:
        test.teardown()
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
            <!-- host：远端server的ip，本地设备无需填写。 -->
            <host>127.0.0.1</host>
            <!-- port：远端server的端口，本地设备无需填写。 -->
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

## 创建ETS 测试工程

根据https://gitcode.com/arkui-x/cli/blob/master/README.md官方文档配置ACE Tools工具链。

**创建ETS测试工程**

打开命令行，键入ace create arkuitest(包名)，创建工程(SDK按本机环境选择)。

![image-6](./ArkUI-X%20Hypium使用指导.assets/6.png)

**编写ETS页面**

Python 用例依赖 ETS 页面中的组件 ID。

使用DevEco Studio打开已创建工程，编写ETS 测试 UI 代码放在entry/src/ohosTest/ets/testability目录下。

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

1.链接Android设备，打开终端，键入ace test apk --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --socket命令，等待测试工程安装、启动。

![image-8](./ArkUI-X%20Hypium使用指导.assets/8.png)

##### iOS

```bash
ace test ios --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --device <device_id> --socket
```

##### Android

```bash
ace test apk --b com.example.arkuitest --m entry_test --unittest OpenHarmonyTestRunner --device <device_id> --socket
```

socket、device子命令详细用法见https://gitcode.com/arkui-x/cli/blob/master/README.md#ace-test。

2.执行PyCharm中用例

![image-9](./ArkUI-X%20Hypium使用指导.assets/9.png)

3.结果显示

2. Python 用例执行后输出 `Example — PASS`。
3. ETS 页面中的 `clickResult` 从“未点击”变为“点击成功”。
3. 应用退出。

## 已有Hypium测试工程跨平台运行更改

1.增加config/user_config.xml文件中配置。platform、package_name、device_id等。

![image-10](./ArkUI-X%20Hypium使用指导.assets/10.png)

2.将原有页面及资源从main目录下移至ohosTest目录下。

![image-11](./ArkUI-X%20Hypium使用指导.assets/11.png)

3.注释原有Hypium工程中的启动测试demo语句，跨平台测试由工具链命令启动被测页面。

![image-12](./ArkUI-X%20Hypium使用指导.assets/12.png)

4.若xts用例的执行影响Hypium测试，将下图中xts执行语句注释即可。

![image-13](./ArkUI-X%20Hypium使用指导.assets/13.png)

5.需由Deveco Studio终端键入命令，启动测试页面。

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
