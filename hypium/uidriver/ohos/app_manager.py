import json
import zipfile
from typing import Optional


def get_hap_info(hap_path) -> dict:
    """读取hap包中的pack.info信息"""
    try:
        with zipfile.ZipFile(hap_path) as f:
            data = f.read("pack.info")
        return json.loads(data.decode(encoding="utf-8", errors="ignore"))
    except Exception as e:
        return {}


def get_hap_version_code(hap_path) -> int:
    """从hap中读取version, 失败则返回-1"""
    info = get_hap_info(hap_path)
    try:
        version_code = info.get("summary").get('app').get("version").get("code")
        return version_code
    except Exception as e:
        return -1


def get_bundle_info(driver, bundle_name):
    info = driver.execute_shell_command(f"bm dump -n {bundle_name}")
    bundle_info = None
    start = info.find(":")
    if start < 0:
        raise ValueError("Can't get bundle_info for [%s], please check if application installed" % bundle_name)
    try:
        json_data = info[start + 1:].strip()
        bundle_info = json.loads(json_data)
    except Exception as e:
        driver.log.error("Fail get bundle info: %s" % repr(e))
    if bundle_info is None:
        raise ValueError("Can't get bundle_info for [%s], please check if application installed" % bundle_name)
    return bundle_info


def _is_launcher_ability(ability_info: dict):
    """判断是否支持桌面启动"""
    skills = ability_info['skills']
    if len(skills) <= 0:
        return False
    actions = skills[0]["actions"]
    if "action.system.home" in actions:
        return True
    else:
        return False


def get_icon_abilities(driver, bundle_name):
    result = []
    bundle_info = get_bundle_info(driver, bundle_name)
    hap_module_infos = bundle_info.get("hapModuleInfos")
    main_entry = bundle_info.get("mainEntry")
    for hap_module_info in hap_module_infos:
        # 尝试读取moduleInfo
        try:
            ability_infos = hap_module_info.get("abilityInfos")
            module_main = hap_module_info["mainAbility"]
        except Exception as e:
            driver.log_warning(f"Fail to parse moduleInfo item, {repr(e)}")
            continue

        # 尝试读取abilityInfo
        for ability_info in ability_infos:
            try:
                if _is_launcher_ability(ability_info):
                    icon_ability_info = {
                        "name": ability_info["name"],
                        "moduleName": ability_info["moduleName"],
                        "moduleMainAbility": module_main,
                        "mainModule": main_entry,
                    }
                    result.append(icon_ability_info)
            except Exception as e:
                driver.log_warning(f"Fail to parse ability_info item, {repr(e)}")
                continue
    return result


def _is_equal_and_not_none(a, b):
    return all((
        a == b,
        a is not None,
        a != ""
    ))


def get_main_ability(driver, bundle_name: str) -> Optional[dict]:
    abilities = get_icon_abilities(driver, bundle_name)
    if len(abilities) <= 0:
        return None
    for item in abilities:
        score = 0
        name = item.get("name")
        module_main_ability = item.get("moduleMainAbility")
        module_name = item.get("moduleName")
        main_module = item.get("mainModule")
        # 判断ability和模块设置的mainAbility是否等同
        if _is_equal_and_not_none(name, module_main_ability):
            score += 20

        # 判断entry是否为主entry
        if _is_equal_and_not_none(module_name, main_module):
            score += 100
        item["score"] = score
    abilities.sort(key=lambda x: x.get("score"), reverse=True)
    driver.log_debug(f"all icon abilities: {abilities}")
    if len(abilities) > 1:
        names = [ability.get("name") for ability in abilities]
        driver.log_warning(f"bundle has multiple abilities, {names}")
    return abilities[0]
