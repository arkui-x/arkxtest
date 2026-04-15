from hypium.uidriver.uitree import BySelector

pop_window_rules_en = [
    {
        "selectors": [
            BySelector().text("Agree"),
            BySelector().text("Cancel"),
            BySelector().key("Paf.Permission.ic_guide"),
            BySelector().text("(?i).+Privacy.+", match_pattern="regexp"),
            BySelector().text("(?i).+Permissions.+", match_pattern="regexp"),
            BySelector().text("(?i)this app.+", match_pattern="regexp")

        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("Skip"),
            BySelector().text("New zoom"),
            BySelector().text("zoom experience", match_pattern="contains")
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("Skip"),
            BySelector().text("New zoom"),
            BySelector().text("zoom experience", match_pattern="contains")
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("(?i)^Skip$", match_pattern="regexp"),
            BySelector().type("SwiperIndicator"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("(?i)^get started$", match_pattern="regexp"),
            BySelector().text("Easy Editing"),
            BySelector().type("SwiperIndicator"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("OK"),
            BySelector().text("Use USB to"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("Cancel"),
            BySelector().text("Celia Chat"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("Cancel"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    }
]

pop_window_rules_ch = [
    {
        "selectors": [
            BySelector().type("Button").text("取消"),
            BySelector().type("Button").text("设置网络"),
            BySelector().text("网络未连接", match_pattern="contains")
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("知道了"),
            BySelector().text("网络未连接，请检查网络设置", match_pattern="contains"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("选择中文键盘布局", match_pattern="contains"),
            BySelector().text("26键"),
            BySelector().text("9键"),
            BySelector().text("手写"),
            BySelector().text("下一步")
        ],
        "target_index": 4
    },
    {
        "selectors": [
            BySelector().text("同意"),
            BySelector().text("取消"),
            BySelector().key("Paf.Permission.ic_guide"),
            BySelector().text("隐私", match_pattern="contains"),
            BySelector().text("本应用.+", match_pattern="regexp")

        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("取消"),
            BySelector().text("下一步"),
            BySelector().text("小艺对话"),
            BySelector().text("长按底部导航条", match_pattern="contains")
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("跳过"),
            BySelector().type("SwiperIndicator"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("立即体验"),
            BySelector().text("影像智能编辑"),
            BySelector().type("SwiperIndicator"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("取消"),
            BySelector().text("电池电量不足"),
            BySelector().text("请尽快接通电源", "contains"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("确定"),
            BySelector().text("USB 连接方式"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("允许"),
            BySelector().text("不允许"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("仅使用期间允许"),
            BySelector().text("不允许"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("知道了"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("始终允许"),
            BySelector().text("不允许"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().type("Button"),
            BySelector().type("Popup"),
            BySelector().text("长按内容至浮起，可拖拽到底部小艺")
        ],
        "target_index": 0
    },
    {
      # 华为分享提示弹窗
        "selectors": [
            BySelector().text("同意"),
            BySelector().type("Dialog"),
            BySelector().text("华为分享")
        ],
        "target_index": 0
    },
    {
        "selectors": [
            BySelector().text("关闭"),
            BySelector().text("小艺对话"),
            BySelector().type("Dialog"),
        ],
        "target_index": 0
    }
]

pop_window_rules = pop_window_rules_ch + pop_window_rules_en
