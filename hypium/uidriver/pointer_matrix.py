from .frontend_api import FrontEndClass, frontend_api, do_hypium_rpc, ApiConfig
from .uicomponent import Point


class PointerMatrix(FrontEndClass):
    """@inner 记录手势点位的矩阵"""
    @staticmethod
    @frontend_api(since=9)
    def create(device, fingers: int, steps: int) -> 'PointerMatrix':
        pass

    def setPoint(self, finger: int, step: int, point: Point, interval: int = None):
        if interval is not None:
            point.X += 65536 * interval
        return do_hypium_rpc(ApiConfig(since=9), "PointerMatrix.setPoint", self, finger, step, point)


FrontEndClass.frontend_type_creators['PointerMatrix'] = lambda ref: PointerMatrix(ref)
