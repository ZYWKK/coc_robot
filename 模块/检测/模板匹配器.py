# 模板匹配器.py
import sys

import cv2
import numpy as np
import threading
from pathlib import Path
from collections import OrderedDict
from typing import Tuple, Optional, Union


class 模板匹配引擎:
    """带缓存的线程安全模板匹配引擎（单例模式）"""
    _单例实例 = None
    _单例锁 = threading.Lock()
    _已初始化 = False

    def __new__(cls, *args, **kwargs):
        with cls._单例锁:
            if not cls._单例实例:
                cls._单例实例 = super().__new__(cls)
        return cls._单例实例

    def 获取资源目录(self):
        """兼容 PyInstaller 打包后的资源目录"""
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path.cwd()  # 或者 Path(__file__).parent

    def __init__(self, 最大缓存数=50, 图片库路径: Union[str, Path] = None):
        """初始化模板匹配引擎

        参数：
            最大缓存数: 最大缓存的模板数量（默认50）
            图片库路径: 模板图片的根目录（默认使用当前目录/img）
        """
        if self.__class__._已初始化:
            return

        # 初始化路径配置
        资源目录 = self.获取资源目录()
        self.图片库路径 = Path(图片库路径) if 图片库路径 else 资源目录 / "img"

        if not self.图片库路径.exists():
            raise ValueError(f"图片库路径不存在：{self.图片库路径}")

        # 初始化缓存系统
        self.模板缓存 = OrderedDict()
        self.缓存锁 = threading.RLock()
        self.最大缓存数 = 最大缓存数

        # 线程计数器
        self.线程计数器 = 0
        self.计数器锁 = threading.Lock()

        self.__class__._已初始化 = True

    def _安全加载模板(self, 模板相对路径: str) -> Optional[np.ndarray]:
        """带LRU缓存的模板加载方法"""
        完整路径 = self.图片库路径 / 模板相对路径.strip()

        # 检查文件是否存在
        if not 完整路径.exists():
            return None

        # 尝试从缓存获取
        with self.缓存锁:
            if str(完整路径) in self.模板缓存:
                # 更新缓存顺序
                self.模板缓存.move_to_end(str(完整路径))
                return self.模板缓存[str(完整路径)]

        # 缓存未命中时加载
        try:
            # 从可能包含中文的路径读取文件
            文件数据 = np.fromfile(完整路径, dtype=np.uint8)
            模板图像 = cv2.imdecode(文件数据, cv2.IMREAD_COLOR)
            if 模板图像 is None:
                return None
        except Exception as 异常:
            print(f"加载模板失败：{完整路径}，错误：{异常}")
            return None

        # 更新缓存
        with self.缓存锁:
            self.模板缓存[str(完整路径)] = 模板图像
            if len(self.模板缓存) > self.最大缓存数:
                # 移除最久未使用的模板
                self.模板缓存.popitem(last=False)

        return 模板图像

    def 执行匹配(self, 底图: np.ndarray, 模板路径: Union[str, list], 相似度阈值=0.8, 匹配算法=cv2.TM_CCOEFF_NORMED, 调试模式=False) -> Tuple[bool, Tuple[int, int], Optional[np.ndarray]]:
        """执行模板匹配操作

        参数：
            底图: 要搜索的底图（BGR格式）
            模板路径: 模板路径（支持用|分隔多个路径）
            相似度阈值: 匹配阈值（0-1）
            匹配算法: OpenCV模板匹配算法
            调试模式: 是否生成调试图像

        返回：
            (是否匹配, 中心坐标, 调试图像)
        """
        # 更新线程计数器
        with self.计数器锁:
            self.线程计数器 += 1
            当前线程号 = self.线程计数器

        # 处理多模板路径
        if isinstance(模板路径, str):
            模板路径列表 = 模板路径.split('|')
        else:
            模板路径列表 = 模板路径

        调试图像 = 底图.copy() if 调试模式 else None
        匹配结果 = (False, (0, 0))

        for 相对路径 in 模板路径列表:
            # 加载模板图像
            模板 = self._安全加载模板(相对路径)
            if 模板 is None:
                continue

            # 校验模板尺寸
            模板高, 模板宽 = 模板.shape[:2]
            if 模板高 > 底图.shape[0] or 模板宽 > 底图.shape[1]:
                if 调试模式:
                    print(f"→ 线程 {当前线程号} 模板尺寸过大：{相对路径}")
                continue

            # 执行模板匹配
            try:
                匹配度图 = cv2.matchTemplate(底图, 模板, 匹配算法)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(匹配度图)

                # 根据算法类型判断匹配结果
                if 匹配算法 in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    最佳值, 最佳位置 = min_val, min_loc
                    是否匹配 = 最佳值 <= 相似度阈值
                else:
                    最佳值, 最佳位置 = max_val, max_loc
                    是否匹配 = 最佳值 >= 相似度阈值

                # 调试绘图
                if 调试模式 and 调试图像 is not None:
                    颜色 = (0, 255, 0) if 是否匹配 else (0, 0, 255)
                    cv2.rectangle(
                        调试图像,
                        最佳位置,
                        (最佳位置[0] + 模板宽, 最佳位置[1] + 模板高),
                        颜色,
                        2
                    )
                    cv2.putText(
                        调试图像,
                        f"{相对路径} {最佳值:.2f}",
                        (最佳位置[0], 最佳位置[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        颜色,
                        1
                    )

                if 是否匹配:
                    中心点 = (最佳位置[0] + 模板宽 // 2, 最佳位置[1] + 模板高 // 2)
                    匹配结果 = (True, 中心点)
                    break

            except Exception as 异常:
                if 调试模式:
                    print(f"→ 线程 {当前线程号} 匹配出错：{str(异常)}")
                continue

        # 返回结果
        if 调试模式:
            return (*匹配结果, 调试图像)
        return (*匹配结果, None)


# 使用示例
if __name__ == "__main__":
    # 初始化引擎（图片库路径根据实际情况修改）
    引擎 = 模板匹配引擎(图片库路径="C:/Users/Hello/PycharmProjects/coc_robot/img")

    # 验证单例
    实例1 = 模板匹配引擎()
    实例2 = 模板匹配引擎()
    print(f"单例验证：{id(实例1) == id(实例2)}")

    # 模拟多线程测试

    def 测试任务(线程名称):
        底图 = cv2.imread(r"D:\yolo\coc\images\69906343.bmp")
        结果 = 引擎.执行匹配(
            底图=底图,
            模板路径="下兵界面兵种状态/未选中/弓箭女王.bmp",
            调试模式=True
        )
        print(11)
        if 结果[0]:
            cv2.imwrite(f"{线程名称}1.jpg", 结果[2])

    # 创建测试线程
    线程列表 = []
    for i in range(3):
        线程 = threading.Thread(target=测试任务, args=(f"线程{i + 1}",))
        线程列表.append(线程)
        线程.start()

    # 等待所有线程完成
    for 线程 in 线程列表:
        线程.join()
