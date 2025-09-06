# ArkUI-X跨平台自动化测试框架

## 简介
ArkUI-X跨平台测试框架代码仓，包含单元测试框架(JsUnit)和Ui测试框架(UiTest)，为跨平台应用开发自动化测试用例提供所需的能力。

- 单元测试框架：支持测试用例基础运行机制，并提供测试用例执行前预处理、执行后清理、断言等能力。
- Ui测试框架：支持针对应用界面的控件进行查找，并可基于控件或坐标进行如点击、滑动等基本操作能力。

## 目录
```
arkXtest 
  |-----jsunit  单元测试框架
  |-----uitest  UI测试框架
```

##  单元测试框架功能特性

| No.  | 特性     | 功能说明                             |
| ---- | -------- | ------------------------------------ |
| 1    | 基础流程 | 支持编写及异步执行基础用例。         |
| 2    | 断言库   | 判断用例实际期望值与预期值是否相符。 |

###  基础流程

测试用例中定义describe代表一个测试套， it代表一条用例。

| No.  | API        | 功能说明                                                     |
| ---- | ---------- | ------------------------------------------------------------ |
| 1    | describe   | 定义一个测试套，支持两个参数：测试套名称和测试套函数。       |
| 2    | beforeAll  | 在测试套内定义一个预置条件，在所有测试用例开始前执行且仅执行一次，支持一个参数：预置动作函数。 |
| 3    | beforeEach | 在测试套内定义一个单元预置条件，在每条测试用例开始前执行，执行次数与it定义的测试用例数一致，支持一个参数：预置动作函数。 |
| 4    | afterEach  | 在测试套内定义一个单元清理条件，在每条测试用例结束后执行，执行次数与it定义的测试用例数一致，支持一个参数：清理动作函数。 |
| 5    | afterAll   | 在测试套内定义一个清理条件，在所有测试用例结束后执行且仅执行一次，支持一个参数：清理动作函数。 |
| 6    | it         | 定义一条测试用例，支持三个参数：用例名称，过滤参数和用例函数。 |
| 7    | expect     | 支持bool类型判断等多种断言方法。                             |

示例代码可参考[使用指南](https://gitee.com/arkui-x/docs/blob/master/zh-cn/application-dev/test/arkxtest.md#编写测试代码-1)。

###  断言库

断言功能列表：

| No.  | API                              | 功能说明                                                     |
| ---- | -------------------------------- | ------------------------------------------------------------ |
| 1    | assertClose                      | 检验actualvalue和expectvalue(0)的接近程度是否是expectValue(1)。 |
| 2    | assertContain                    | 检验actualvalue中是否包含expectvalue。                       |
| 3    | assertEqual                      | 检验actualvalue是否等于expectvalue(0)。                      |
| 4    | assertFail                       | 抛出一个错误。                                               |
| 5    | assertFalse                      | 检验actualvalue是否是false。                                 |
| 6    | assertTrue                       | 检验actualvalue是否是true。                                  |
| 7    | assertInstanceOf                 | 检验actualvalue是否是expectvalue类型，支持基础类型。         |
| 8    | assertLarger                     | 检验actualvalue是否大于expectvalue。                         |
| 9    | assertLess                       | 检验actualvalue是否小于expectvalue。                         |
| 10   | assertNull                       | 检验actualvalue是否是null。                                  |
| 11   | assertThrowError                 | 检验actualvalue抛出Error内容是否是expectValue。              |
| 12   | assertUndefined                  | 检验actualvalue是否是undefined。                             |
| 13   | assertNaN                        | @since1.0.4 检验actualvalue是否是一个NAN                     |
| 14   | assertNegUnlimited               | @since1.0.4 检验actualvalue是否等于Number.NEGATIVE_INFINITY  |
| 15   | assertPosUnlimited               | @since1.0.4 检验actualvalue是否等于Number.POSITIVE_INFINITY  |
| 16   | assertDeepEquals                 | @since1.0.4 检验actualvalue和expectvalue是否完全相等         |
| 17   | assertPromiseIsPending           | @since1.0.4 判断promise是否处于Pending状态。                 |
| 18   | assertPromiseIsRejected          | @since1.0.4 判断promise是否处于Rejected状态。                |
| 19   | assertPromiseIsRejectedWith      | @since1.0.4 判断promise是否处于Rejected状态，并且比较执行的结果值。 |
| 20   | assertPromiseIsRejectedWithError | @since1.0.4 判断promise是否处于Rejected状态并有异常，同时比较异常的类型和message值。 |
| 21   | assertPromiseIsResolved          | @since1.0.4 判断promise是否处于Resolved状态。                |
| 22   | assertPromiseIsResolvedWith      | @since1.0.4 判断promise是否处于Resolved状态，并且比较执行的结果值。 |
| 23   | not                              | @since1.0.4 断言取反,支持上面所有的断言功能                  |

示例代码：

```js
import { describe, it, expect } from '@ohos/hypium'
export default async function abilityTest() {
  describe('assertTest', function () {
    it('assertClose_success', 0, function () {
      let a = 100
      let b = 0.1
      expect(a).assertClose(99, b)
    })
    it('assertClose_fail', 0, function () {
      let a = 100
      let b = 0.1
      expect(a).assertClose(1, b)
    })
    it('assertClose_null_fail_001', 0, function () {
      let a = 100
      let b = 0.1
      expect(a).assertClose(null, b)
    })
    it('assertClose_null_fail_002', 0, function () {
      expect(null).assertClose(null, 0)
    })
    it('assertEqual', 0, function () {
      let a = 1;
      let b = 1;
      expect(a).assertEqual(b)
    })
    it('assertFail', 0, function () {
      expect().assertFail();
    })
    it('assertFalse', 0, function () {
      let a = false;
      expect(a).assertFalse();
    })
    it('assertTrue', 0, function () {
      let a = true;
      expect(a).assertTrue();
    })
    it('assertInstanceOf_success', 0, function () {
      let a = 'strTest'
      expect(a).assertInstanceOf('String')
    })
    it('assertLarger', 0, function () {
      let a = 1;
      let b = 2;
      expect(b).assertLarger(a);
    })
    it('assertLess', 0, function () {
      let a = 1;
      let b = 2;
      expect(a).assertLess(b);
    })
    it('assertNull', 0, function () {
      let a = null;
      expect(a).assertNull()
    })
    it('assertThrowError', 0, function () {
      function testError() {
        throw new Error('error message')
      }
      expect(testError).assertThrowError('error message')
    })
    it('assertUndefined', 0, function () {
      let a = undefined;
      expect(a).assertUndefined();
    })
    it('assertNaN', 0, function () {
      let a = 'str'
      expect(a).assertNaN()
    })
    it('assertInstanceOf_success', 0, function () {
      let a = 'strTest'
      expect(a).assertInstanceOf('String')
    })
    it('assertNaN_success',0, function () {
      expect(Number.NaN).assertNaN(); // true
    })
    it('assertNegUnlimited_success',0, function () {
      expect(Number.NEGATIVE_INFINITY).assertNegUnlimited(); // true
    })
    it('assertPosUnlimited_success',0, function () {
      expect(Number.POSITIVE_INFINITY).assertPosUnlimited(); // true
    })
    it('not_number_true',0, function () {
      expect(1).not().assertLargerOrEqual(2)
    })
    it('not_number_true_1',0, function () {
      expect(3).not().assertLessOrEqual(2);
    })
    it('not_NaN_true',0, function () {
      expect(3).not().assertNaN();
    })
    it('not_contain_true',0, function () {
      let a = "abc";
      let b= "cdf"
      expect(a).not().assertContain(b);
    })
    it('not_large_true',0, function () {
      expect(3).not().assertLarger(4);
    })
    it('not_less_true',0, function () {
      expect(3).not().assertLess(2);
    })
    it('not_undefined_true',0, function () {
      expect(3).not().assertUndefined();
    })
    it('deepEquals_null_true',0, function () {
      // Defines a variety of assertion methods, which are used to declare expected boolean conditions.
      expect(null).assertDeepEquals(null)
    })
    it('deepEquals_array_not_have_true',0, function () {
      // Defines a variety of assertion methods, which are used to declare expected boolean conditions.
      const  a= []
      const  b= []
      expect(a).assertDeepEquals(b)
    })
    it('deepEquals_map_equal_length_success',0, function () {
      // Defines a variety of assertion methods, which are used to declare expected boolean conditions.
      const a =  new Map();
      const b =  new Map();
      a.set(1,100);
      a.set(2,200);
      b.set(1, 100);
      b.set(2, 200);
      expect(a).assertDeepEquals(b)
    })
    it("deepEquals_obj_success_1", 0, function () {
      const a = {x:1};
      const b = {x:1};
      expect(a).assertDeepEquals(b);
    })
    it("deepEquals_regExp_success_0", 0, function () {
      const a = new RegExp("/test/");
      const b = new RegExp("/test/");
      expect(a).assertDeepEquals(b)
    })
    it('test_isPending_pass_1', 0, function () {
      let p = new Promise(function () {
      });
      expect(p).assertPromiseIsPending();
    });
    it('test_isRejected_pass_1', 0, function () {
      let p = Promise.reject({
        bad: 'no'
      });
      expect(p).assertPromiseIsRejected();
    });
    it('test_isRejectedWith_pass_1', 0, function () {
      let p = Promise.reject({
        res: 'reject value'
      });
      expect(p).assertPromiseIsRejectedWith({
        res: 'reject value'
      });
    });
    it('test_isRejectedWithError_pass_1', 0, function () {
      let p1 = Promise.reject(new TypeError('number'));
      expect(p1).assertPromiseIsRejectedWithError(TypeError);
    });
    it('test_isResolved_pass_1', 0, function () {
      let p = Promise.resolve({
        res: 'result value'
      });
      expect(p).assertPromiseIsResolved();
    });
    it('test_isResolvedTo_pass_1', 0, function () {
      let p = Promise.resolve({
        res: 'result value'
      });
      expect(p).assertPromiseIsResolvedWith({
        res: 'result value'
      });
    });
    it('test_isPending_failed_1', 0, function () {
      let p = Promise.reject({
        bad: 'no1'
      });
      expect(p).assertPromiseIsPending();
    });
    it('test_isRejectedWithError_failed_1', 0, function () {
      let p = Promise.reject(new TypeError('number'));
      expect(p).assertPromiseIsRejectedWithError(TypeError, 'number one');
    });
  })
}
```

> 说明
>
> 单元测试框架代码复用OpenHarmony平台代码，具体可[查看](https://gitee.com/openharmony/testfwk_arkxtest)。

##  Ui测试框架功能特性

| No.  | 特性          | 功能说明                                                     |
| ---- | ------------- | ------------------------------------------------------------ |
| 1    | **Driver**    | Ui测试的入口，提供查找控件，检查控件存在性以及注入按键能力。 |
| 2    | **On**        | 用于描述目标控件特征(文本、id、类型等)，`Driver`根据`On`描述的控件特征信息来查找控件。 |
| 3    | **Component** | Driver查找返回的控件对象，提供查询控件属性，滑动查找等触控和检视能力。 |

### 使用说明

- 导入模块

```
import {Driver,ON,Component,Uiwindow,MatchPattern} from '@ohos.UiTest'
```

> 说明
>
> 1. **On**提供的接口均为同步接口，使用者可以使用**builder**模式链式调用其接口构造控件筛选条件。
> 2. **Driver**和**Component**类提供的接口均为**Promise**异步回调，需使用**await**调用。
> 3. Ui测试用例均需使用**异步**语法编写用例。

- 测试用例。


```
import {describe, beforeAll, beforeEach, afterEach, afterAll, it, expect} from '@ohos/hypium'

export default async function abilityTest() {
  describe('uiTestDemo', function() {
    it('uitest_demo0', 0, async function() {
      // create Driver
      let driver = Driver.create()
      // find component by text
      let button = await driver.findComponent(ON.text('hello').enabled(true))
      // click component
      await button.click()
      // get and assert component text
      let content = await button.getText()
      expect(content).assertEqual('clicked!')
    })
  })
}
```
