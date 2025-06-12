import queue

import threading
import time
import random

from 任务流程.世界跳转.到主世界任务 import 到主世界任务
from 任务流程.世界跳转.到夜世界任务 import 到夜世界任务
from 任务流程.升级城墙 import 城墙升级任务
from 任务流程.启动模拟器 import 启动模拟器任务
from 任务流程.基础任务框架 import 任务上下文
from 任务流程.夜世界打鱼 import 夜世界打鱼任务
from 任务流程.打开进攻页面 import 打开进攻页面任务
from 任务流程.搜索敌人 import 搜索目标敌人任务
from 任务流程.更新账号资源状态 import 更新资源状态任务
from 任务流程.检查图像 import 检查图像任务
from 任务流程.检测游戏登录状态 import 检测游戏登录状态任务
from 任务流程.等待战斗结束并回营 import 等待战斗结束并回营任务
from 任务流程.进攻 import 进攻任务
from 数据库.任务数据库 import 任务数据库, 机器人设置
from 核心.op import op类

from 核心.键盘操作 import 键盘控制器
from 核心.鼠标操作 import 鼠标控制器
from 模块.雷电模拟器操作类 import 雷电模拟器操作类
from 核心.核心异常们 import 图像获取失败


class 自动化机器人:
    """为单个用户提供游戏自动化服务的机器人实例"""

    def __init__(self, 机器人标志: str, 消息队列: queue.Queue, 数据库: 任务数据库):
        # 基础属性
        self.机器人标志 = 机器人标志
        self.消息队列 = 消息队列#用来给监控中心发送消息
        self.数据库 = 数据库


        self.继续事件 = threading.Event()
        self.停止事件 = threading.Event()
        self.停止事件.set()#目前未启动线程,处于停止状态
        self.雷电模拟器=雷电模拟器操作类(self.数据库.获取机器人设置(机器人标志).雷电模拟器索引)
        self.op:op类



    def 启动(self):
        if self.停止事件.is_set() :
            self.停止事件.clear()
            self.主线程 = threading.Thread(
                target=self._任务流程,
                name=f"任务线程-{self.机器人标志}",
                daemon=True
            )
            self.主线程.start()


        else:
            print("目前线程未停止,无需再次启动")

    def 暂停(self):
        """标记暂停状态"""
        print("已暂停")
        self.继续事件.clear()

    def 继续(self):
        """清除暂停状态"""
        print("已继续")
        self.继续事件.set()


    def 停止(self, 停止原因=""):
        """标记终止状态"""
        self.继续()#唤醒可能已经暂停的线程
        self.停止事件.set()
        #等待线程停止,如果未启动则没有主线程属性,加一层判断
        if hasattr(self, "主线程") and self.主线程.is_alive():
            self.主线程.join()

    @property
    def 设置(self) -> 机器人设置:
        配置 = self.数据库.获取机器人设置(self.机器人标志)
        return 配置

    @property
    def 当前状态(self) -> str:
        if self.停止事件.is_set():
            return "已停止"
        elif not self.继续事件.is_set():
            return "暂停中"
        else:
            return "运行中"

    def _任务流程(self):
        """主任务逻辑"""
        self.op = op类()
        if self.op is None:
            print("op创建失败")

        上下文=任务上下文(
            机器人标志=self.机器人标志,
            消息队列=self.消息队列,
            数据库= self.数据库,
            停止事件=self.停止事件,
            继续事件=self.继续事件,
            op=self.op,
            雷电模拟器=self.雷电模拟器,
            鼠标=鼠标控制器(self.雷电模拟器.取绑定窗口句柄()),
            键盘=键盘控制器(self.雷电模拟器.取绑定窗口句柄())
        )
        上下文.置脚本状态("开始执行",1000)
        上下文.继续事件.set()
        try:
            启动模拟器任务().执行(上下文)
            上下文.op.绑定(self.雷电模拟器.取绑定窗口句柄的下级窗口句柄())
            检查图像任务().执行(上下文)
            检测游戏登录状态任务().执行(上下文)
            到夜世界任务().执行(上下文)
            夜世界打鱼任务().执行(上下文)
            # while True:
            #     检测游戏登录状态任务().执行(上下文)
            #     更新资源状态任务().执行(上下文)
            #     城墙升级任务().执行(上下文)
            #     上下文.脚本延时(random.randint(500,3000))
            #     打开进攻页面任务().执行(上下文)
            #     搜索目标敌人任务().执行(上下文)
            #     进攻任务().执行(上下文)
            #     等待战斗结束并回营任务().执行(上下文)
            #     上下文.置脚本状态("进攻完毕,到循环头")


            print("-"*10+F"{self.机器人标志} 线程自然消亡"+"-"*10)
            self.停止事件.set()#标志目前线程已经停止了,以免监控中心一直启动

        except 图像获取失败 as e:
             上下文.发送重启请求(f"异常: {str(e)}")
             print("-"*10+F"{self.机器人标志} 线程因为异常而消亡"+"-"*10+f"异常: {str(e)}")
        except SystemExit as e:
            print("-"*10+F"{self.机器人标志} 线程因为捕获到退出而消亡"+"-"*10)
        finally:
            上下文.op.安全清理()



    def 检查超时(self)  -> tuple[bool, str]:
        """检查是否超时，返回 (是否超时, 原因)。未超时返回 (False, '')"""

        最后日志 = self.数据库.读取最后日志(self.机器人标志)
        # 无历史日志的情况
        if not 最后日志:
            return (False, "无历史日志记录")  # 无日志视为第一次启动,不是超时的异常状态

        # 主动停止不视为超时
        if self.停止事件.is_set():

            return (False, F"{self.机器人标志} 线程已主动停止,不是异常状态")



        if time.time() > 最后日志.下次超时:
            实际间隔 = round(time.time() - 最后日志.记录时间)
            超时阈值 = round(最后日志.下次超时 - 最后日志.记录时间)

            原因 = (
                f"数据库最后日志记录已超时（内容：[{最后日志.日志内容}]），"
                f"实际间隔 {实际间隔} 秒超过阈值 {超时阈值} 秒"
            )

            return True,原因

        return (False, "")

