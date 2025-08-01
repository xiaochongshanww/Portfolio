from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from time import sleep
from PIL import Image
import pytesseract
import os
import re
import time
import sqlite3
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from xml.etree import ElementTree
from lxml import etree
from appium.webdriver.common.appiumby import AppiumBy
import config
from my_log import logger
from girl_info import GirlInfo
import traceback
from selenium.common.exceptions import WebDriverException


class QianShou:
    def __init__(self):
        self.appium_options = UiAutomator2Options()
        self.driver = None
        self.like_count = 0  # 当前喜欢数量
        self.dislike_count = 0  # 当前不喜欢数量
        self.swiped_card_index = 0  # 当前资料页索引
        self.cur_girl_info = None  # 当前女孩信息
        self.start_time = None  # 开始时间
        self.check_speed = 0  # 检查速度
        self.conn = sqlite3.connect("./database/qianshou_girl_info.db", isolation_level=None)  # 数据库连接
        self.init()

    def set_appium_options(self):
        self.appium_options.platform_name = "Android"  # 平台名称
        self.appium_options.platform_version = "14"   # 安卓版本
        self.appium_options.device_name = "device"  # 设备名称（通过 adb devices 查看）
        self.appium_options.app_package = "com.tantan.x"  # 应用包名
        self.appium_options.app_activity = "com.tantan.x.main.MainAct"  # 启动的 Activity
        self.appium_options.no_reset = True  # 是否重置应用状态
        self.appium_options.automation_name = "UiAutomator2"  # 指定自动化引擎

    def link_to_appium_server(self):
        """
        连接到 Appium 服务器
        """
        # 配置超时时间
        client_config = ClientConfig(
            remote_server_addr=config.APPIUM_SERVER_ADDR, timeout=600)  # 设置超时时间为 600 秒
        remote_connection = RemoteConnection(
            config.APPIUM_SERVER_ADDR, client_config)
        # 连接到 Appium Server
        self.driver = webdriver.Remote(
            command_executor=remote_connection,
            options=self.appium_options,
        )

    def init(self):
        """
        初始化 Appium 连接
        """
        self.set_appium_options()
        self.link_to_appium_server()
        logger.info("连接Appium server成功")
        
    def reconnect_appium_server(self):
        logger.info("重新连接Appium server")
        if self.driver:
            self.driver.quit()
        self.init()
        self.prepare_work()
        logger.info("重新连接Appium server成功")
    

    def click_recommend_button(self):
        """
        点击推荐按钮
        """
        try:
            recommend_button = self.driver.find_element(
                By.XPATH, '//android.widget.TextView[@resource-id="com.tantan.x:id/main_tag_view_rec_tv"]')
            recommend_button.click()
            logger.info("点击推荐按钮完成")
        except Exception as e:
            logger.error(f"点击推荐按钮失败: {e}")
            self.process_click_failure()  # 处理点击失败的情况
            # 如果失败，重新获取推荐按钮并点击
            recommend_button = self.driver.find_element(
                By.XPATH, '//android.widget.TextView[@resource-id="com.tantan.x:id/main_tag_view_rec_tv"]')
            recommend_button.click()
            logger.info("重新点击推荐按钮完成")

    def click_profile_button(self):
        """
        点击资料按钮
        """
        try:
            profile_button = self.driver.find_element(
                By.XPATH, '//android.widget.ImageView[@resource-id="com.tantan.x:id/tagViewMe"]')
            profile_button.click()
            logger.info("点击个人主页按钮完成")
        except Exception as e:
            logger.error(f"点击个人主页按钮失败: {e}")
            self.process_click_failure()  # 处理点击失败的情况
        
    def click_like_button(self):
        """
        点击喜欢按钮
        """
        try:
            like_button = self.driver.find_element(By.XPATH, '(//android.widget.ImageView[@resource-id="com.tantan.x:id/smallFlowerIcon"])[2]')
            like_button.click()
            logger.info("点击喜欢按钮完成")
        except Exception as e:
            logger.error(f"点击喜欢按钮失败: {e}")
            self.process_click_failure()  # 处理点击失败的情况
 
        
    # 点击不喜欢按钮
    def click_dislike_button(self):
        try:
            dislike_button = self.driver.find_element(By.XPATH, '//android.widget.ImageView[@resource-id="com.tantan.x:id/recommend_anim_dislike_btn"]')
            dislike_button.click()
            logger.info("点击不喜欢按钮完成")
        except Exception as e:
            logger.error(f"点击不喜欢按钮失败: {e}")
            self.process_click_failure()  # 处理点击失败的情况
    
    def process_click_failure(self):
        """
        处理点击按钮失败的情况
        """
        if self.send_flower_option_exists():
            logger.info("检测到发送鲜花选项，点击关闭按钮")
            self.click_close_send_flower_button()
        if self.more_right_swipe_exists():
            logger.info("检测到更多右滑选项，点击关闭按钮")
            self.click_more_right_swipe_button()
        
    def more_right_swipe_exists(self):
        """
        判断是否存在更多右滑选项
        """
        # 获取页面中所有的 TextView 元素
        text_elements = self.driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
        # 提取每个元素的文本
        all_texts = [element.text for element in text_elements if element.text.strip()]
        for text in all_texts:
            if re.search(r"尝试多些右滑吧",text, re.I | re.M):
                logger.info("存在多些右滑选项")
                return True
        return False
    
    def click_more_right_swipe_button(self):
        """
        关闭多些右滑选项
        """
        try:
            close_button = self.driver.find_element(By.XPATH, config.CLOSE_MORE_RIGHT_SWIPE_BUTTON_XPATH)
            close_button.click()
            logger.info("点击 试试看 按钮完成")
        except Exception as e:  
            logger.error(f"点击 试试看 按钮失败: {e}")
            # 如果失败，重新获取关闭按钮并点击
            close_button = self.driver.find_element(By.XPATH, config.CLOSE_MORE_RIGHT_SWIPE_BUTTON_XPATH)
            close_button.click()
            logger.info("重新点击 试试看 按钮完成")
        
    
    def send_flower_option_exists(self):
        """
        判断是否存在发送鲜花选项
        """
        # 获取页面中所有的 TextView 元素
        text_elements = self.driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
        # 提取每个元素的文本
        all_texts = [element.text for element in text_elements if element.text.strip()]
        for text in all_texts:
            if re.search(r"送花表达",text, re.I | re.M):
                logger.info("存在发送鲜花选项")
                return True
            if re.search(r"立即送花",text, re.I | re.M):
                logger.info("存在发送鲜花选项")
                return True
        return False
    
    def click_close_send_flower_button(self):
        """
        点击关闭发送鲜花按钮
        """
        try:
            close_button = self.driver.find_element(By.XPATH, config.CLOSE_SEND_FLOWER_BUTTON_XPATH)
            close_button.click()
            logger.info("点击关闭发送鲜花按钮完成")
        except Exception as e:  
            logger.error(f"点击关闭发送鲜花按钮失败: {e}")
            # 如果失败，重新获取关闭按钮并点击
            close_button = self.driver.find_element(By.XPATH, config.CLOSE_SEND_FLOWER_BUTTON_XPATH)
            close_button.click()
            logger.info("重新点击关闭发送鲜花按钮完成")

    def get_cur_swiped_card_index(self):
        """
        获取当前显示的资料页的索引
        """
        swiprd_card_xpath = '//android.widget.FrameLayout[@resource-id="com.tantan.x:id/newSwipeCard"]/android.widget.FrameLayout'
        elements = self.driver.find_elements(By.XPATH, swiprd_card_xpath)
        for index, element in enumerate(elements):
            bounds = element.get_attribute("bounds")
            if re.search(r"^\[0,232\]", bounds):
                self.swiped_card_index = int(index) + 1
                break

    def get_all_texts_from_xpath(self, xpath):
        """
        获取指定 XPath 下所有子元素的文本
        :param driver: Appium WebDriver 实例
        :param xpath: XPath 表达式
        :return: 包含所有文本的列表
        """
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)  # 获取所有匹配的元素
            all_texts = list()
            for element in elements:
                text_view_elements = element.find_elements(
                    By.CLASS_NAME, "android.widget.TextView")
                for text_view_element in text_view_elements:
                    test = text_view_element.text.strip()
                    if test:
                        all_texts.append(test)
            return "".join(all_texts)  # 返回所有文本的连接字符串
        except Exception as e:
            logger.error(f"获取文本失败: {e}")
            return ""

    def get_age(self):
        """
        获取年龄信息
        """
        age_xpath = f'(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_1"])[{self.swiped_card_index}]'
        age_string = self.get_all_texts_from_xpath(age_xpath)
        if re.search(r"(\d+)岁", age_string):
            age = re.findall(r"(\d+)岁", age_string)[0]
            return int(age)
        logger.warning(f"未找到年龄信息: {age_string}")
        return 0

    def get_about_me(self):
        """
        获取关于我信息
        """
        about_me_xpath = f'(//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_about_me_first_item_root"])[{self.swiped_card_index}]'
        about_me_string = self.get_all_texts_from_xpath(about_me_xpath)
        return about_me_string

    def get_user_nickname(self):
        """
        获取用户昵称
        :return: 用户昵称
        """
        try:
            nickname = "NULL"
            parent_elements = self.driver.find_elements(
                By.XPATH, '(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_root_2"])')
            for ele in parent_elements:
                text_view = ele.find_element(
                    By.XPATH, './/android.widget.TextView')
                bounds = text_view.get_attribute("bounds")
                if re.search(r"^\[467,586\]", bounds):
                    nickname = text_view.text
                    break

            logger.info(f"用户昵称: {nickname}")
            return nickname
        except Exception as e:
            logger.error(f"获取用户昵称失败: {e}")
            return "NULL"

    def get_basic_info(self):
        """
        获取基本资料信息
        """
        self.scroll_to_basic_info()
        basic_info_xpath = f'//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_base_info_item_ll"]'
        child_elements = self.driver.find_elements(By.XPATH, basic_info_xpath)
        basic_info_list = list()
        for child_element in child_elements:
            text_view_elements = child_element.find_elements(
                By.CLASS_NAME, "android.widget.TextView")
            for text_view_element in text_view_elements:
                text = text_view_element.text.strip()
                basic_info_list.append(text)
        logger.info(f"基本资料：{basic_info_list}")
        return basic_info_list

    def is_basic_info_loaded(self):
        """
        判断当前屏幕是否加载了基本信息
        """
        flag = False
        basic_info_xpath = '//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_base_info_item_ll"]'
        elements = self.driver.find_elements(By.XPATH, basic_info_xpath)
        all_texts = list()
        for element in elements:
            all_texts.clear()
            text_view_elements = element.find_elements(
                By.CLASS_NAME, "android.widget.TextView")
            for text_view_element in text_view_elements:
                text = text_view_element.text.strip()
                all_texts.append(text)
            for text in all_texts:
                if re.search(r"现居地", text):
                    flag = True
                    break
            if flag:
                break
        if flag:
            return True
        return False

    def scroll_to_basic_info(self):
        """
        滑动屏幕到基本信息
        """
        scroll_count = 0
        while not self.is_basic_info_loaded():
            self.driver.swipe(start_x=500, start_y=1500,
                              end_x=500, end_y=700, duration=500)
            scroll_count += 1
            if scroll_count > 20:
                logger.info("滑动次数过多，可能是页面加载问题，点击下一个")
                # self.click_dislike_button()
                break

    def prepare_work(self):
        """
        准备工作
        """
        logger.info("准备工作……")
        self.click_recommend_button()
        self.click_profile_button()
        self.click_recommend_button()
        self.click_dislike_button()
        logger.info("准备工作完成")

    def is_like(self, girl_info):
        """
        判断是否喜欢
        """
        logger.info("判断是否喜欢")
        checks = [
            self.check_age(girl_info),
            self.check_height(girl_info),
            self.check_education(girl_info),
            self.check_work_info(girl_info),
            self.check_hometown(girl_info),
            self.check_current_location(girl_info),
            self.check_salary(girl_info),
            self.check_brife_introduction(girl_info),
        ]
        if all(checks):
            logger.info("❤❤❤符合要求，喜欢❤❤❤")
            return True
        logger.info("🤡🤡🤡不符合要求，不喜欢🤡🤡🤡")
        return False

    @staticmethod
    def check_age(girl_info):
        """
        判断年龄是否符合要求
        """
        if girl_info.age < 20 or girl_info.age > 29:
            logger.info(f"年龄不符合要求: {girl_info.age}岁")
            return False
        return True

    @staticmethod
    def check_height(girl_info):
        """
        判断身高是否满足要求
        """
        if girl_info.height < 150 or girl_info.height > 165:
            logger.info(f"身高不符合要求: {girl_info.height}cm")
            return False
        return True

    @staticmethod
    def check_education(girl_info):
        """
        判断学历是否满足要求
        """
        education_info = girl_info.education
        if re.search(r"大专|未知|非全日制|NULL|职业学院|职业技术|音乐", education_info, re.I | re.M):
            logger.info(f"学历不符合要求: {education_info}")
            return False
        return True

    @staticmethod
    def check_work_info(girl_info):
        """
        判断工作信息是否符合要求
        """
        work_info = girl_info.work_info
        if re.search(r"未知|无|待业|学生|在校|在读|自由职业|打杂|服务员|服务业|技师|客服|实习", work_info, re.I | re.M):
            logger.info(f"工作信息不符合要求: {work_info}")
            return False
        return True

    @staticmethod
    def check_hometown(girl_info):
        """
        判断家乡是否符合要求
        """
        home_town = girl_info.hometown
        if re.search(r"江西", home_town, re.I | re.M):
            logger.info(f"家乡不符合要求: {home_town}")
            return False
        return True
    
    @staticmethod
    def check_salary(girl_info):
        """
        判断薪资是否符合要求
        """
        salary = girl_info.salary
        if re.search(r"5万以下", salary, re.I | re.M):
            logger.info(f"薪资不符合要求: {salary}")
            return False
        return True

    @staticmethod
    def check_current_location(girl_info):
        """
        判断现居地是否符合要求
        """
        current_location = girl_info.current_location
        return True
    
    @staticmethod
    def check_brife_introduction(girl_info):
        """
        判断个人简介是否符合要求
        """
        brief_introduction = girl_info.brife_introduction
        if re.search(r"慢热|追星|喜欢旅游|离异", brief_introduction, re.I | re.M):
            logger.info(f"个人简介不符合要求: {brief_introduction}")
            return False
        return True
    
    def cal_check_speed(self):
        """
        计算速度
        """
        total_check_number = self.like_count + self.dislike_count
        if total_check_number > 0 and total_check_number % 10 == 0:
            logger.info(f"当前速度: {total_check_number / (time.time() - self.start_time) * 3600}次/小时")
            self.check_speed = total_check_number / (time.time() - self.start_time) * 3600
            logger.info(f"预计每天 {self.check_speed * 24} 个推荐")
            self.get_db_total_count()  # 获取数据库中总记录数

    def get_db_total_count(self):
        """
        获取数据库中总记录数
        """
        cursor = self.conn.execute("SELECT COUNT(*) FROM girls_info")
        count = cursor.fetchone()[0]
        like_count = self.get_db_total_like()
        dislike_count = self.get_db_total_dislike()
        logger.info(f"当前数据库中总记录数为： {count}")
        logger.info(f"喜欢总数为：{like_count}")
        logger.info(f"不喜欢总数为: {dislike_count}")
        
    def get_db_total_like(self):
        """
        从数据库中查询喜欢的总数
        """    
        cursor = self.conn.execute("SELECT COUNT(*) FROM girls_info WHERE is_like = 1")
        count = cursor.fetchone()[0]
        return count
        
    def get_db_total_dislike(self):
        """
        从数据库中查询不喜欢的总数
        """    
        cursor = self.conn.execute("SELECT COUNT(*) FROM girls_info WHERE is_like = 0")
        count = cursor.fetchone()[0]
        return count
    
    def run(self):
        """
        主运行函数
        """
        self.prepare_work()
        self.start_time = time.time()
        for loop_index in range(1, 5001):
            try:
                logger.info(f"**********第{self.like_count + self.dislike_count + 1}个推荐**********")
                logger.info(
                    f"当前喜欢数量: {self.like_count}, 当前不喜欢数量: {self.dislike_count}")
                self.cur_girl_info = GirlInfo()
                self.get_cur_swiped_card_index()
                self.cur_girl_info.nick_name = self.get_user_nickname()  # 要在界面没滑动前获取昵称
                self.cur_girl_info.age = self.get_age()
                self.cur_girl_info.brife_introduction = self.get_about_me()
                self.cur_girl_info.basic_info_list = self.get_basic_info()
                self.cur_girl_info.get_info_from_basic_info_list()  # 解析基本信息
                self.cur_girl_info.print_info()
                # 判断是否喜欢
                if self.is_like(self.cur_girl_info):
                    self.cur_girl_info.is_like = True
                    self.click_like_button()
                    self.like_count += 1
                else:
                    self.cur_girl_info.is_like = False
                    self.click_dislike_button()
                    self.dislike_count += 1
                self.cur_girl_info.write_to_db(self.conn)
                logger.info(f"##########第{self.like_count + self.dislike_count}个推荐结束##########")
                self.cal_check_speed()
            except WebDriverException as e:
                logger.error(f"WebDriver异常: {e}")
                logger.error(f"traceback 信息: \n{traceback.format_exc()}")
                self.reconnect_appium_server()  # 重连appium
                sleep(2)
                continue
            except Exception as e:
                logger.error(f"发生异常: {e}")
                logger.error(f"traceback 信息: \n{traceback.format_exc()}")
                # 处理异常，例如重新点击推荐按钮
                self.prepare_work()
                sleep(2)
                continue
        self.driver.quit()


if __name__ == "__main__":
    qianshou = QianShou()
    qianshou.run()