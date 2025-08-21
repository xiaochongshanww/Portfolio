# 收集知乎热榜数据
from zhihuhot import ZhihuHot
import time
import json
import os

zhihu_hot = ZhihuHot()
zhihu_hot.prepare()
hot_dict = zhihu_hot.get_hot_dict()
existing_data = dict()

cur_time = time.strftime("%Y-%m-%d_%H_%M_%S", time.localtime())
hot_data_file_name = f"zhihu_hot_data_{cur_time}.json"
# 检查文件是否存在
if not os.path.exists(hot_data_file_name):
    # 如果文件不存在，创建一个空文件并写入空字典
    with open(hot_data_file_name, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

with open(hot_data_file_name, 'r+', encoding='utf-8') as f:
    # 读取现有数据，反序化为字典
    existing_data = json.load(f)
    existing_data[cur_time] = hot_dict
    # 使用r+模式，需要先把文件指针移动到开头
    f.seek(0)  # 将文件指针移动到开头
    json.dump(existing_data, f, ensure_ascii=False, indent=4)
    
for i in range(100):
    time.sleep(6)  # 每隔十分钟收集一次数据
    hot_dict = zhihu_hot.get_hot_dict()
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(hot_data_file_name, 'r+', encoding='utf-8') as f:
        # 读取现有数据，反序化为字典
        existing_data = json.load(f)
        existing_data[cur_time] = hot_dict
        f.seek(0)  # 将文件指针移动到开头
        json.dump(existing_data, f, ensure_ascii=False, indent=4)


