import re
import sqlite3
from datetime import datetime
from my_log import logger
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base


class GirlInfo:
    def __init__(self):
        self.nick_name = "NULL"  # 昵称
        self.age = 0  # 年龄
        self.height = 0  # 身高
        self.constellation = "NULL"  # 星座
        self.education = "NULL"  # 学历
        self.work_info = "NULL"  # 工作信息
        self.salary = "NULL"  # 薪资
        self.hometown = "NULL"  # 家乡
        self.current_location = "NULL"  # 当前城市
        self.love_target = "NULL"  # 恋爱目标
        self.brife_introduction = "NULL"  # 个人简介
        self.real_name_certification = False  # 实名认证
        self.basic_info_list = list()  # 基本资料列表
        self.is_like = False  # 是否喜欢
        self.log_time = None  # 入库时间

    @property
    def basic_info_list(self):
        return self._basic_info_list
    
    @basic_info_list.setter
    def basic_info_list(self, info_list):
        if info_list.count("基本资料") > 1:
            # 找到第二个"基本资料"的索引
            second_index = info_list.index("基本资料", info_list.index("基本资料") + 1)
            # 截取列表，保留第二个"基本资料"之前的所有元素
            info_list = info_list[:second_index]
        if len(info_list) > 8:
            self._basic_info_list = info_list[:8]
        else:
            self._basic_info_list = info_list
    
    def get_info_from_basic_info_list(self):
        """
        从基本信息列表中获取信息
        """
        self.get_height()
        self.get_constellation()
        self.get_education()
        self.get_work_info()
        self.get_salary()
        self.get_hometown()
        self.get_current_location()
    
    def get_height(self):
        """
        获取身高信息
        """
        for info in self.basic_info_list:
            if re.search(r"(\d+)cm", info, re.I | re.M):
                height = re.findall(r"(\d+)cm", info)[0]
                self.height = int(height)
                break
            
    def get_constellation(self):
        """
        获取星座信息
        """
        for info in self.basic_info_list:
            if re.search(r"\S+座", info, re.I | re.M):
                self.constellation = info
                break
    
    def get_education(self):
        """
        获取学历信息
        """
        for info in self.basic_info_list:
            if re.search(r"大学|学院|学校|大专以下", info, re.I | re.M):
                self.education = info
                break
            
    def get_work_info(self):
        """
        获取工作信息
        """
        for info in self.basic_info_list:
            if re.search(r"cm", info, re.I | re.M):
                continue
            if re.search(r"\S+座", info, re.I | re.M):
                continue
            if re.search(r"大学|学院|学校|大专以下", info, re.I | re.M):
                continue
            if re.search(r"年薪", info, re.I | re.M):
                continue
            if re.search(r"家乡", info, re.I | re.M):
                continue
            if re.search(r"现居地", info, re.I | re.M):
                continue
            if re.search(r"基本资料", info, re.I | re.M):
                continue
            self.work_info = info
            break
        
    def get_salary(self):
        """
        获取薪资信息
        """
        for info in self.basic_info_list:
            if re.search(r"年薪", info, re.I | re.M):
                self.salary = info
                break
            
    def get_hometown(self):
        """
        获取家乡信息
        """
        for info in self.basic_info_list:
            if re.search(r"家乡", info, re.I | re.M):
                self.hometown = re.findall(r"家乡(.+)", info)[0]
                break
            
    def get_current_location(self):
        """
        获取现居地
        """
        for info in self.basic_info_list:
            if re.search(r"现居地", info, re.I | re.M):
                self.current_location = re.findall(r"现居地(.+)", info)[0]
                break
            
    def print_info(self):
        """
        打印基本信息
        """
        logger.info("================================")
        logger.info(f"昵称: {self.nick_name}")
        logger.info(f"年龄: {self.age}岁")
        logger.info(f"身高: {self.height}cm")
        logger.info(f"星座: {self.constellation}")
        logger.info(f"学历: {self.education}")
        logger.info(f"工作信息: {self.work_info}")
        logger.info(f"薪资: {self.salary}")
        logger.info(f"家乡: {self.hometown}")
        logger.info(f"现居地: {self.current_location}")
        logger.info(f"个人简介: {self.brife_introduction}")
        logger.info("================================")
        
    def get_log_time(self):
        """
        获取当前时间
        """
        self.log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # 写入数据库
    def write_to_db(self, db_conn,table_name='girls_info'):
        """
        写入数据库
        """
        self.get_log_time()
        # 使用参数化插入，避免直接拼接字符串引发 SQL 注入
        sql = f"INSERT INTO {table_name} (nick_name, age, height, constellation, education, work_info, salary, hometown, current_location, love_target, brife_introduction, real_name_certification, is_like, log_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        values = (
            self.nick_name,
            int(self.age),
            self.height,
            self.constellation,
            self.education,
            self.work_info,
            self.salary,
            self.hometown,
            self.current_location,
            self.love_target,
            self.brife_introduction,
            1 if self.real_name_certification else 0,
            1 if self.is_like else 0,
            self.log_time
        )
        # 执行插入操作
        db_conn.execute(sql, values)