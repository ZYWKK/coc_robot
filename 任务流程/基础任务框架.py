

import queue
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Tuple

from 工具包.工具函数 import 生成贝塞尔轨迹
from 数据库.任务数据库 import 任务数据库
from 核心.op import op类

from 核心.键盘操作 import 键盘控制器
from 核心.鼠标操作 import 鼠标控制器
from 模块.雷电模拟器操作类 import 雷电模拟器操作类

@dataclass
class 任务上下文:
    机器人标志: str
    数据库: 任务数据库
    消息队列: queue.Queue
    继续事件: threading.Event
    停止事件: threading.Event
    op:op类
    雷电模拟器:雷电模拟器操作类
    键盘:键盘控制器
    鼠标:鼠标控制器
    置脚本状态:Callable

    # def 置脚本状态(self, 日志内容:str, 超时的时间:float=60):
    #     print(f"[机器人消息] {self.机器人标志} {time.strftime('%Y年%m月%d日 %H:%M:%S')}: {日志内容}")
    #     self.数据库.记录日志(self.机器人标志, 日志内容, time.time() + 超时的时间)

    def 发送重启请求(self, 原因: str):
        """发送重启请求并终止当前线程"""
        self.置脚本状态(f"主动请求重启，原因：{原因}")
        # 发送结构化消息到监控中心
        self.消息队列.put({
            "类型": "重启请求",
            "机器人标志": self.机器人标志,
            "原因": 原因
        })

        # 设置停止事件以终止当前线程,正在执行的任务执行到延时时,会判断这个标志,然后触发退出
        self.停止事件.set()

    def 脚本延时(self, 毫秒数):
        for _ in range(毫秒数):
            time.sleep(0.001)


            if not self.继续事件.is_set():
                self.继续事件.wait()

            if self.停止事件.is_set():
                self.置脚本状态("收到停止事件")
                self.op.安全清理()
                raise SystemExit(f"收到退出请求,主动退出线程,机器人{self.机器人标志}已关闭")

    def 点击(self,x,y,延时=None,是否精确点击=False):
        # 延时默认值
        if 延时 is None:
            延时 = random.randint(400, 600)

        # 精确点击控制
        随机半径 = 0 if 是否精确点击 else 6

        # 加随机偏移
        x = random.randint(x - 随机半径, x + 随机半径)
        y = random.randint(y - 随机半径, y + 随机半径)

        if self.鼠标 is None:
            raise RuntimeError("鼠标控制器未初始化")

        self.鼠标.移动到(x, y)
        self.鼠标.左键点击()
        self.脚本延时(延时)

    def 滑动屏幕(self, 起点坐标, 终点坐标):
        """使用贝塞尔曲线模拟人类滑动操作"""
        起点x, 起点y = 起点坐标
        终点x, 终点y = 终点坐标

        # 随机偏移增强人类行为模拟
        起点x += random.randint(-5, 5)
        起点y += random.randint(-5, 5)
        终点x += random.randint(-5, 5)
        终点y += random.randint(-5, 5)

        # 控制点随机生成在起点和终点附近
        控制点1 = (
            起点x + (终点x - 起点x) * 0.3 + random.randint(-30, 30),
            起点y + (终点y - 起点y) * 0.3 + random.randint(-30, 30),
        )
        控制点2 = (
            起点x + (终点x - 起点x) * 0.6 + random.randint(-30, 30),
            起点y + (终点y - 起点y) * 0.6 + random.randint(-30, 30),
        )

        路径点 = 生成贝塞尔轨迹((起点x, 起点y), 控制点1, 控制点2, (终点x, 终点y), 步数=random.randint(25, 40))

        self.鼠标.移动到(路径点[0][0], 路径点[0][1])
        self.鼠标.左键按下()

        for 当前点 in 路径点[1:]:
            self.鼠标.移动到(当前点[0], 当前点[1])
            self.脚本延时(random.randint(5, 15))  # 模拟人类微小不规律移动

        self.鼠标.左键抬起()
        self.脚本延时(random.randint(500, 1000))


from abc import ABC, abstractmethod


class 基础任务(ABC):
    """游戏任务基类"""
    def __init__(self,上下文: '任务上下文'):
        self.上下文=上下文

    @abstractmethod
    def 执行(self, 上下文: '任务上下文') -> bool:
        """
        返回True继续下一个任务，返回False终止流程
        """
        pass



    def 异常处理(self, 上下文: '任务上下文', 异常: Exception,是否重启游戏=True):
        上下文.置脚本状态(f"任务[{self.__class__.__name__}] 异常：{异常}")
        if 是否重启游戏:
            上下文.雷电模拟器.关闭模拟器中的应用(上下文.数据库.获取机器人设置(上下文.机器人标志).部落冲突包名)
            上下文.置脚本状态("重启游戏")
            上下文.脚本延时(2000)
            上下文.雷电模拟器.打开应用(上下文.数据库.获取机器人设置(上下文.机器人标志).部落冲突包名)

    def 已出现图片(self, 模板路径: str, 区域: Tuple[int, int, int, int] = (0, 0, 800, 600),相似度阈值=0.9) -> Tuple[
        bool, Tuple[int, int]]:
        """
        当前机器人操作的模拟器是否出现指定图片，并返回坐标。

        参数:
            模板路径: 模板图路径（可为多个路径用 | 分隔）
            区域: 指定识别区域，格式为 (x1, y1, x2, y2)

        返回:
            是否匹配, (x, y) 坐标
        """
        x1, y1, x2, y2 = 区域
        屏幕图像 = self.上下文.op.获取屏幕图像cv(x1, y1, x2, y2)
        是否匹配, (x, y), _ = self.模板识别.执行匹配(屏幕图像, 模板路径, 相似度阈值)

        # 注意坐标需要加上区域偏移量
        if 是否匹配:
            return True, (x + x1, y + y1)
        else:
            return False, (x + x1, y + y1)
