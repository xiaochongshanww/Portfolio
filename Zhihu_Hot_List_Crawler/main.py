import matplotlib.pyplot as plt
from zhihuhot import ZhihuHot
from matplotlib import rcParams


# 设置字体为 SimHei（黑体）或其他支持中文的字体
rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
rcParams['axes.unicode_minus'] = False  # 解决负号显示为方块的问题

zhihu_hot = ZhihuHot()
zhihu_hot.prepare()
hot_dict = zhihu_hot.get_hot_dict()

print(zhihu_hot.hot_dict)

plt.figure(figsize=(15, 10))

titles, heats = zhihu_hot.trans_hot_dict_to_list()

# 生成条形图的 Y 轴位置（偶数位置）
bar_positions = [x * 2 for x in range(1, len(titles) + 1)]

# 生成标题的 Y 轴位置（奇数位置）
title_positions = [x * 2 - 1 for x in range(1, len(titles) + 1)]

# 横向条形图
bars = plt.barh(bar_positions, heats, color='skyblue')

# 将标题添加到对应条形图下方
for index, value in enumerate(heats):
    plt.text(5, title_positions[index], f"{titles[index]} 热度: {value}万", va='center', ha='left', fontsize=10)  # 在标题位置添加标题

# 设置标题和标签
plt.title('知乎热榜TOP30', fontsize=16)
plt.xlabel('热度值', fontsize=12)
plt.ylabel('热门话题排行', fontsize=12)

# 设置 Y 轴刻度值和标签
plt.yticks(bar_positions, [y for y in range(30, 0, -1)])  # 设置交替显示的刻度标签

plt.tight_layout()
plt.show()