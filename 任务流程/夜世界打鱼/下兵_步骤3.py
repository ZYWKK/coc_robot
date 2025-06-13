from 任务流程.基础任务框架 import 任务上下文
from 任务流程.夜世界打鱼.夜世界基础任务 import 夜世界基础任务
from 模块.检测.模板匹配器 import 模板匹配引擎
import random

class 下兵(夜世界基础任务):
    def __init__(self ,上下文: '任务上下文'):
        super().__init__(上下文)


    def 执行(self) -> bool:

        try:
            self.上下文.脚本延时(random.randint(500, 1000))
            self.执行下兵操作()

            # 选择英雄
            self.上下文.点击(47, 545)

            # 出英雄
            self.上下文.点击(55, 299)

            # 放英雄技能
            self.上下文.脚本延时(3000)
            self.上下文.点击(42, 554)

            while self.尝试点击放兵种技能():
                self.上下文.脚本延时(random.randint(20, 60))
                self.上下文.置脚本状态("放兵中技能")
            return True
        except RuntimeError as e:
            self.异常处理(e)
            return False

    def 执行下兵操作(self):
        区域字典 = {
            "左上": ((21, 257), (389, 29)),
            "右上": ((467, 26), (751, 249)),
            "右下": ((769, 336), (557, 463)),
            "左下": ((145, 399), (29, 280)),
        }

        区域项列表 = list(区域字典.items())
        random.shuffle(区域项列表)

        for 名称, (左上, 右下) in 区域项列表:
            if self.尝试在区域内完成下兵(左上, 右下):
                self.上下文.置脚本状态("兵已经下完")
                return

    def 尝试在区域内完成下兵(self, 左上角: tuple, 右下角: tuple) -> bool:
        """在指定区域内尝试完成下兵操作，若提示下满兵则返回 True"""
        坐标列表 = self.生成随机坐标点(左上角, 右下角, random.randint(2, 6))

        for 坐标 in 坐标列表:
            if self.下兵并检测是否完成下兵(坐标):
                return True
        return False

    def 下兵并检测是否完成下兵(self, 坐标: tuple) -> bool:
        """点击指定坐标，并判断是否出现下兵完成提示"""
        self.上下文.点击(坐标[0], 坐标[1], random.randint(80, 180))
        是否匹配, _ = self.是否出现图片("夜世界_请选择其它兵种.bmp")
        return 是否匹配


    def 尝试点击放兵种技能(self):
        """验证是否已开始战斗"""
        是否匹配, (x, y) = self.是否出现图片("夜世界_兵种技能色块.bmp")
        if 是否匹配:
            self.上下文.点击(x-21, y+49)
            return True
        else:
            return False

    def 异常处理(self, 异常: Exception,**关键字参数):
        super().异常处理(异常)
        self.上下文.发送重启请求(f"任务[{self.__class__.__name__}] 触发了异常：{异常}")

    @staticmethod
    def 生成随机坐标点(起点, 终点, 点数量=1, 最大扰动=5):
        起点x, 起点y = 起点
        终点x, 终点y = 终点
        随机点列表 = []

        for i in range(点数量):
            t = random.uniform(0, 1)  # 插值比例
            x = 起点x + (终点x - 起点x) * t
            y = 起点y + (终点y - 起点y) * t

            # 加一点扰动，模拟人类随机操作
            x += random.uniform(-最大扰动, 最大扰动)
            y += random.uniform(-最大扰动, 最大扰动)

            随机点列表.append((int(x), int(y)))

        return 随机点列表

