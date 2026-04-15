from lxml import etree


def register_xpath_custom_func(function_name, function):
    ns = etree.FunctionNamespace(None)
    ns[function_name] = function


def build_xml_tree(json_node):
    """将uitest格式的json控件树转换为xml控件树"""
    # 读取attributes
    attributes = json_node.get("attributes", {})
    # 构建xml element
    tag = attributes.get("type", "orgRoot")
    if not isinstance(tag, str) or len(tag) == 0:
        tag = "orgRoot"
    current_xml_node = etree.Element(tag, attrib=attributes)
    for child_json_node in json_node.get("children"):
        child_xml_node = build_xml_tree(child_json_node)
        current_xml_node.append(child_xml_node)
    return current_xml_node
