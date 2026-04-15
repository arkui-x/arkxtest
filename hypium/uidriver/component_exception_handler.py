
def handle_component_exception(comp, action):
    from hypium.uidriver.uitree import BySelector
    driver = getattr(comp, "driver", None)
    if not driver:
        return False, None
    try:
        comp = driver.findComponent(BySelector.from_by(comp._sourcing_call[2][0]))
        action = getattr(comp, action, None)
        if callable(action):
            return True, action()
    except Exception as e:
        driver.log_warning(f"Fail to handle comp exception, {repr(e)}")
        return False, None
    return False, None

