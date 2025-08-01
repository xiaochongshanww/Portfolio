from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from time import sleep
from PIL import Image
import pytesseract
import os
import re
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from xml.etree import ElementTree
from lxml import etree
from appium.webdriver.common.appiumby import AppiumBy

# 配置 Desired Capabilities
options = UiAutomator2Options()
options.platform_name = "Android"  # 平台名称
options.platform_version = "14"   # 安卓版本
options.device_name = "device"  # 设备名称（通过 adb devices 查看）
options.app_package = "com.tantan.x"  # 应用包名
options.app_activity = "com.tantan.x.main.MainAct"  # 启动的 Activity
options.no_reset = True  # 是否重置应用状态
options.automation_name = "UiAutomator2"  # 指定自动化引擎


# 配置超时时间
client_config = ClientConfig(remote_server_addr="http://127.0.0.1:4723", timeout=600)  # 设置超时时间为 600 秒
remote_connection = RemoteConnection("http://127.0.0.1:4723", client_config)
# 连接到 Appium Server
driver = webdriver.Remote(
    # command_executor="http://127.0.0.1:4723",
    command_executor=remote_connection,
    options=options
)
# driver.command_executor.set_timeout(600)

# 当前资料页索引
swiped_card_index = 0

# 显式指定 Tesseract 的路径
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 示例操作：等待并点击按钮
print("开始等待...")
# sleep(5)
print("等待完成")

# 定位并点击推荐按钮
# print("开始定位并点击推荐按钮...")
# recommend_button = driver.find_element(By.XPATH, '//android.widget.TextView[@resource-id="com.tantan.x:id/main_tag_view_rec_tv"]')
# recommend_button.click()
# print("点击推荐按钮完成")

# 截图
# driver.save_screenshot("screenshot.png")

# 获取页面源代码
# page_source = driver.page_source
# print("页面源代码：")

# 获取页面中所有的 TextView 元素
text_elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")

# 提取每个元素的文本
all_texts = [element.text for element in text_elements if element.text.strip()]
print("页面中的所有文本:", all_texts)

# 截图保存路径
screenshot_dir = "screenshots"
os.makedirs(screenshot_dir, exist_ok=True)

# 点击推荐按钮
def click_recommend_button(driver):
    try:
        recommend_button = driver.find_element(By.XPATH, '//android.widget.TextView[@resource-id="com.tantan.x:id/main_tag_view_rec_tv"]')
        recommend_button.click()
        print("点击推荐按钮完成")
    except Exception as e:
        print(f"点击推荐按钮失败: {e}")
        # 如果失败，重新获取推荐按钮并点击
        recommend_button = driver.find_element(By.XPATH, '//android.widget.TextView[@resource-id="com.tantan.x:id/main_tag_view_rec_tv"]')
        recommend_button.click()
        print("重新点击推荐按钮完成")
    
# 点击个人主页按钮
def click_profile_button(driver):
    profile_button = driver.find_element(By.XPATH, '//android.widget.ImageView[@resource-id="com.tantan.x:id/tagViewMe"]')
    profile_button.click()
    print("点击个人主页按钮完成")
    
    
# 获取当前显示的资料页的索引
def get_cur_swiped_card_index(driver):
    global swiped_card_index  # 声明为全局变量
    swiprd_card_xpath = '//android.widget.FrameLayout[@resource-id="com.tantan.x:id/newSwipeCard"]/android.widget.FrameLayout'
    elements = driver.find_elements(By.XPATH, swiprd_card_xpath)
    for index, element in enumerate(elements):
        bounds = element.get_attribute("bounds")
        if re.search(r"^\[0,232\]", bounds):
            swiped_card_index = int(index) + 1  # 直接修改全局变量的值
            print(f"当前显示的资料页索引: {swiped_card_index}")
            break
        


# 从给定xpath读取文本
def get_all_texts_from_xpath(driver, xpath):
    """
    获取指定 XPath 下所有子元素的文本
    :param driver: Appium WebDriver 实例
    :param xpath: XPath 表达式
    :return: 包含所有文本的列表
    """
    try:
        elements = driver.find_elements(By.XPATH, xpath)  # 获取所有匹配的元素
        all_texts = list()
        for element in elements:
            text_view_elements = element.find_elements(By.CLASS_NAME, "android.widget.TextView")
            for text_view_element in text_view_elements:
                test = text_view_element.text.strip()
                if test:
                    all_texts.append(test)
        # all_texts = [element.text for element in elements if element.text.strip()]  # 提取非空文本
        print(f"从 {xpath} 获取的所有文本: {all_texts}")
        return "".join(all_texts)  # 返回所有文本的连接字符串
    except Exception as e:
        print(f"获取文本失败: {e}")
        return ""
    
# 获取年龄
def get_age(driver):
    # age_xpath = '(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_1"])[1]'
    age_xpath = f'(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_1"])[{swiped_card_index}]'
    
    age_string = get_all_texts_from_xpath(driver, age_xpath)
    if re.search(r"(\d+)岁", age_string):
        age = re.findall(r"(\d+)岁", age_string)[0]
        print(f"年龄: {age}岁")
        return int(age)
    print("未找到年龄信息")
    return 100

# 获取 关于我 描述
def get_about_me(driver):
    about_me_xpath = f'(//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_about_me_first_item_root"])[{swiped_card_index}]'
    about_me_string = get_all_texts_from_xpath(driver, about_me_xpath)
    # about_me_string = "未知"
    # about_me_xpath = '(//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_about_me_first_item_root"])'
    # parent_elements = driver.find_elements(By.XPATH, about_me_xpath)
    # for ele in parent_elements:
    #     text_view = ele.find_element(By.XPATH, './/android.widget.TextView')
    #     bounds= text_view.get_attribute("bounds")
    #     if re.search(r"^\[467,586\]", bounds):
    #         nickname = text_view.text
    #         break
    
    # print(f"用户昵称: {nickname}")
    # return nickname
    
    return about_me_string

# 获取基本信息
def get_basic_info(driver):
    scroll_to_basic_info(driver)
    # 当前页面大节点
    basic_info_parent_xpath = f'//android.widget.FrameLayout[@resource-id="com.tantan.x:id/newSwipeCard"]/android.widget.FrameLayout[{swiped_card_index}]'
    big_node = driver.find_element(By.XPATH, basic_info_parent_xpath)
    # 在大节点下查找小节点
    basic_info_xpath = f'//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_base_info_item_ll"]'
    child_elements = driver.find_elements(By.XPATH, basic_info_xpath)
    # 获取小节点下的所有 TextView 元素
    basic_info_list = list()
    for child_element in child_elements:
        text_view_elements = child_element.find_elements(By.CLASS_NAME, "android.widget.TextView")
        for text_view_element in text_view_elements:
            text = text_view_element.text.strip()
            print(text)
            basic_info_list.append(text)
    print(f"基本资料：{basic_info_list}")
    return basic_info_list
    basic_info_xpath = '//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_base_info_item_ll"]'
    elements = driver.find_elements(By.XPATH, basic_info_xpath)
    for element in elements:
        pass
        # text_view_elements = element.find_elements(By.CLASS_NAME, "android.widget.TextView")
        # for text_view_element in text_view_elements:
        #     text = text_view_element.text.strip()
        #     print(text)
    pass

# 判断当前屏幕是否加载了基本信息
def is_basic_info_loaded(driver):
    flag = False
    basic_info_xpath = '//android.widget.LinearLayout[@resource-id="com.tantan.x:id/new_profile_base_info_item_ll"]'
    elements = driver.find_elements(By.XPATH, basic_info_xpath)
    all_texts = list()
    for element in elements:
        all_texts.clear()
        text_view_elements = element.find_elements(By.CLASS_NAME, "android.widget.TextView")
        for text_view_element in text_view_elements:
            text = text_view_element.text.strip()
            # print(text)
            all_texts.append(text)
        for text in all_texts:
            if re.search(r"现居地", text):
                flag = True
                break
        if flag:
            break

    # if len(elements) == 2:
    #     flag = True
    
    if flag:
        return True
    return False
    if not elements:
        print("基本信息未加载")
        return False
    print("基本信息已加载")
    return True

# 滑动屏幕到基本信息
def scroll_to_basic_info(driver):
    # 滚动到包含特定文本的元素
    # driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().resourceId("com.tantan.x:id/new_profile_base_info_item_ll").instance(0)')    
    while not is_basic_info_loaded(driver):
        driver.swipe(start_x=500, start_y=1500, end_x=500, end_y=1000, duration=800)
        # sleep(1)
    print("已滑动到基本信息")

# 获取身高
def get_girl_height(driver):
    height_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])'
    elsements = driver.find_elements(By.XPATH, height_xpath)
    for element in elsements:
        text_view_elements = element.find_elements(By.CLASS_NAME, "android.widget.TextView")
        for text_view_element in text_view_elements:
            text = text_view_element.text.strip()
            print(text)
    
    
    height_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[1]'
    height_string = get_all_texts_from_xpath(driver, height_xpath)
    if re.search(r"(\d+)cm", height_string):
        height = re.findall(r"(\d+)cm", height_string)[0]
        print(f"身高: {height}cm")
        return int(height)
    print("未找到身高信息")
    return 200
    
# 获取星座
def get_constellation(driver):
    constellation_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[2]'
    constellation_string = get_all_texts_from_xpath(driver, constellation_xpath)
    if re.search(r"(\w+座)", constellation_string):
        constellation = re.findall(r"(\w+座)", constellation_string)[0]
        print(f"星座: {constellation}")
        return constellation
    print("未找到星座信息")
    return "未知星座"

# 获取学历
def get_education(driver):
    education_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[3]'
    education_string = get_all_texts_from_xpath(driver, education_xpath)
    if re.search(r"大学|学院|学校", education_string, re.I | re.M):
        print(f"学历: {education_string}")
        return education_string
    print("未找到学历信息")
    return "未知学历"

# 获取工作信息
def get_work_info(driver):
    work_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[4]'
    work_string = get_all_texts_from_xpath(driver, work_xpath)
    return work_string

# 获取年薪
def get_salary(driver):
    salary_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[5]'
    salary_string = get_all_texts_from_xpath(driver, salary_xpath)
    if re.search(r"(.*万)", salary_string):
        return salary_string
    print("未找到年薪信息")
    return "未知"

# 获取家乡信息
def get_hometown_info(driver):
    hometown_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[6]'
    hometown_string = get_all_texts_from_xpath(driver, hometown_xpath)
    if re.search(r"家乡|家乡在", hometown_string):
        return hometown_string
    print("未找到家乡信息")
    return "未知"

# 获取现居地
def get_current_location(driver):
    location_xpath = '(//android.view.ViewGroup[@resource-id="com.tantan.x:id/profile_base_info_item_root"])[7]'
    location_string = get_all_texts_from_xpath(driver, location_xpath)
    if re.search(r"现居地|现居", location_string):
        return location_string
    print("未找到现居地信息")
    return "未知"

# 获取恋爱目标
def get_love_target(driver):
    target_xpath = '//android.widget.TextView[@resource-id="com.tantan.x:id/goode_profile_love_purpose_item_content"]'
    target_string = get_all_texts_from_xpath(driver, target_xpath)
    return target_string

# 是否实名
def is_real_name(driver):
    try:
        real_name_xpath = '//android.widget.TextView[@resource-id="com.tantan.x:id/profile_verify_item_title_new"]'
        real_name_string = get_all_texts_from_xpath(driver, real_name_xpath)
        if re.search(r"已完成", real_name_string) and re.search(r"认证", real_name_string):
            print("该用户已实名")
            return True
        print("该用户未实名")
        return False
    except Exception as e:
        print(f"获取实名信息失败: {e}")
        return False
    
# 获取用户昵称
def get_user_nickname(driver):
    """
    获取用户昵称
    :param driver: Appium WebDriver 实例
    :return: 用户昵称
    """
    try:
        # 定位父元素
        # parent_element = driver.find_element(By.XPATH, '(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_root_2"])[1]/android.widget.LinearLayout')
        # name = get_user_nickname_from_source(driver, '(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_root_2"])')
        nickname = "未知昵称"
        parent_elements = driver.find_elements(By.XPATH, '(//androidx.appcompat.widget.LinearLayoutCompat[@resource-id="com.tantan.x:id/new_profile_avatar_item_info_root_2"])')
        for ele in parent_elements:
            text_view = ele.find_element(By.XPATH, './/android.widget.TextView')
            bounds= text_view.get_attribute("bounds")
            if re.search(r"^\[467,586\]", bounds):
                nickname = text_view.text
                break
        
        print(f"用户昵称: {nickname}")
        return nickname
    except Exception as e:
        print(f"获取用户昵称失败: {e}")
        return None
    
# 从页面源代码获取用户昵称
def get_user_nickname_from_source(driver, xpath):
    """
    从页面源代码获取用户昵称
    :param driver: Appium WebDriver 实例
    :return: 用户昵称
    """
    try:
        # 获取页面源代码
        page_source = driver.page_source
        
        # 将字符串转换为字节
        page_source_bytes = page_source.encode("utf-8")
        
        # 解析 XML
        root = etree.fromstring(page_source_bytes)
        
        # 根据 XPath 查找目标元素
        elements = root.xpath(xpath)
        for element in elements:
            # 在定位到的元素下查找 TextView 子元素
            text_view_element = element.find(".//android.widget.TextView")
            print(text_view_element.attrib.get("text"))
            if text_view_element.attrib.get("index") == "0":
                nickname = text_view_element.attrib.get("text")
                print(f"用户昵称: {nickname}")
                return nickname
    except Exception as e:
        print(f"获取用户昵称失败: {e}")
        return "未获取到用户名"

def save_user_avatar(driver, save_path="user_avatar.png"):
    """
    保存用户头像
    :param driver: Appium WebDriver 实例
    :param save_path: 保存头像的文件路径
    """
    try:
        # 定位头像元素
        avatar_element = driver.find_element(By.XPATH, '//android.widget.ImageView[@resource-id="com.tantan.x:id/pic"]')
        
        # 截取头像并保存
        avatar_element.screenshot(save_path)
        print(f"用户头像已保存到: {save_path}")
    except Exception as e:
        print(f"保存用户头像失败: {e}")

# 滑动并截图
def capture_full_page(driver):
    screenshots = []
    previous_page_source = ""
    capture_count = 0
    while True:
        # 截取当前屏幕
        screenshot_path = os.path.join(screenshot_dir, f"screenshot_{len(screenshots)}.png")
        driver.save_screenshot(screenshot_path)
        screenshots.append(screenshot_path)
        capture_count += 1
        if capture_count >= 5:
            break

        # 滑动页面
        driver.swipe(start_x=500, start_y=1500, end_x=500, end_y=500, duration=800)

        # 检查是否滑动到底部（通过页面源代码是否重复判断）
        current_page_source = driver.page_source
        if current_page_source == previous_page_source:
            break
        previous_page_source = current_page_source

    return screenshots

# 拼接截图
def stitch_screenshots(screenshots):
    images = [Image.open(screenshot) for screenshot in screenshots]
    total_height = sum(image.height for image in images)
    max_width = max(image.width for image in images)

    # 创建一个空白图片用于拼接
    stitched_image = Image.new("RGB", (max_width, total_height))
    y_offset = 0
    for image in images:
        stitched_image.paste(image, (0, y_offset))
        y_offset += image.height

    stitched_image_path = "full_screenshot.png"
    stitched_image.save(stitched_image_path)
    return stitched_image_path

# 使用 OCR 提取文字
def extract_text_from_image(image_path):
    text = pytesseract.image_to_string(Image.open(image_path), lang="chi_sim")  # 使用中文 OCR
    return text

# 点击喜欢按钮
def click_like_button(driver):
    like_button = driver.find_element(By.XPATH, '(//android.widget.ImageView[@resource-id="com.tantan.x:id/smallFlowerIcon"])[2]')
    like_button.click()
    print("点击喜欢按钮完成")
    
# 点击不喜欢按钮
def click_dislike_button(driver):
    dislike_button = driver.find_element(By.XPATH, '//android.widget.ImageView[@resource-id="com.tantan.x:id/recommend_anim_dislike_btn"]')
    dislike_button.click()
    print("点击不喜欢按钮完成")
    
# 获取身高信息
def get_height(info_str):
    if re.search(r"\d+cm", info_str):
        height = re.findall(r"(\d+)cm", info_str)[0]
        return int(height)
    return 200

# 获取学历信息
def get_school_info(info_str):
    if re.search(r"大学|学院|学校", info_str, re.I | re.M):
        school = re.findall(r"(^.*(?:大专|本科|研究生|博士))", info_str, re.I | re.M)[0]
        if re.search(r"^余.*", school):
            school = re.sub(r"^余", "", school)
        return school
    return "未知"

# 获取家乡信息
def get_hometown(info_str):
    if re.search(r"家乡|家乡在", info_str):
        hometown = re.findall(r"家乡在.(.+?)$", info_str, re.I | re.M)
        return hometown[0] if hometown else "未知"
    return "未知"
    
# 判断是否喜欢
def is_like(girl_info):
    like_flag = True
    print("判断是否喜欢")
    if re.search(r"大专|未知|非全日制", girl_info.get('education'), re.I | re.M):
        print(f"学历不符合要求: {girl_info.get('education')}")
        like_flag = False
    else:
        print(f"学历符合要求: {girl_info.get('education')}")
    if girl_info.get('height') < 150 or girl_info.get('height') > 160:
        print("身高不符合要求")
        like_flag = False
    if re.search(r"江西", girl_info.get('hometown'), re.I | re.M):
        print("家乡不符合要求")
        like_flag = False
    if like_flag:
        print("喜欢!!!")
        return True
    print("不喜欢!!!")
    return False

# 准备工作
def prepare_work(driver):
    click_recommend_button(driver)
    # sleep(2)
    click_profile_button(driver)
    # sleep(2)
    click_recommend_button(driver)
    click_dislike_button(driver)
    
# 通过读取的基本资料列表获取个人资料
def get_girl_profile_by_list(driver, basic_info_list):
    combine_info = "".join(basic_info_list)
    # 是否填有星座
    if re.search(r"座", basic_info_list[2], re.I | re.M):
        height = int(basic_info_list[1].split("cm")[0])
        constellation = basic_info_list[2]
        education = basic_info_list[3]
        work_info = basic_info_list[4]
        salary = basic_info_list[5]
        hometown = basic_info_list[6]
        current_location = basic_info_list[7]
    else:
        height = int(basic_info_list[1].split("cm")[0])
        constellation = "未填写"
        education = basic_info_list[2]
        work_info = basic_info_list[3]
        salary = basic_info_list[4]
        hometown = basic_info_list[5]
        current_location = basic_info_list[6]
    print(f"读取基本资料：")
    print(f"身高: {height}cm")
    print(f"星座: {constellation}")
    print(f"学历: {education}")
    print(f"工作: {work_info}")
    print(f"年薪: {salary}")
    print(f"家乡: {hometown}")
    print(f"现居地: {current_location}")
    return {
        "height": height,
        "constellation": constellation,
        "education": education,
        "work_info": work_info,
        "salary": salary,
        "hometown": hometown,
        "current_location": current_location,
    }

# 通过xpth获取个人资料
def get_girl_profile_by_xpath(driver):
    nick_name = get_user_nickname(driver)
    age = get_age(driver)
    about_me = get_about_me(driver)
    height = get_girl_height(driver)
    constellation = get_constellation(driver)
    education = get_education(driver)
    work_info = get_work_info(driver)
    salary = get_salary(driver)
    hometown = get_hometown_info(driver)
    current_location = get_current_location(driver)
    love_target = get_love_target(driver)
    real_name = is_real_name(driver)
    print(f"读取到个人信息：")
    print(f"昵称: {nick_name}")
    print(f"年龄: {age}岁")
    print(f"关于我: {about_me}")
    print(f"身高: {height}cm")
    print(f"星座: {constellation}")
    print(f"学历: {education}")
    print(f"工作: {work_info}")
    print(f"年薪: {salary}")
    print(f"家乡: {hometown}")
    print(f"现居地: {current_location}")
    print(f"恋爱目标: {love_target}")
    print(f"实名: {real_name}")
    return {
        "nickname": nick_name,
        "age": age,
        "about_me": about_me,
        "height": height,
        "constellation": constellation,
        "education": education,
        "work_info": work_info,
        "salary": salary,
        "hometown": hometown,
        "current_location": current_location,
        "love_target": love_target,
        "real_name": real_name
    }

# 通过OCR获取个人资料
def get_girl_profile_by_ocr(driver):
    # 执行完整截图和 OCR
    screenshots = capture_full_page(driver)
    stitched_image_path = stitch_screenshots(screenshots)
    extracted_text = extract_text_from_image(stitched_image_path)
    extracted_text = extracted_text.replace(" ", "")  # 清理文本

    # 打印提取的文字
    print("提取的文字内容：")
    print(extracted_text)

    # 清理截图文件
    for screenshot in screenshots:
        os.remove(screenshot)
    return extracted_text
    
# 主程序
def main(driver):
    prepare_work(driver)
    sleep(2)
    like_count = 0
    dislike_count = 0
    for i in range(1, 2001):
        try:
            print(f"第{i}个推荐")
            print(f"当前喜欢数量: {like_count}, 当前不喜欢数量: {dislike_count}")
            get_cur_swiped_card_index(driver)
            basic_info_list = get_basic_info(driver)
            # save_user_avatar(driver)
            # 获取个人主页信息
            girl_profile = get_girl_profile_by_list(driver, basic_info_list)
            # girl_profile = get_girl_profile_by_xpath(driver)
            # girl_profile = get_girl_profile_by_ocr(driver)
            # 判断是否喜欢
            if is_like(girl_profile):
                click_like_button(driver)
                like_count += 1
            else:
                click_dislike_button(driver)
                dislike_count += 1
        except Exception as e:
            print(f"发生异常: {e}")
            # 处理异常，例如重新点击推荐按钮
            prepare_work(driver)
            sleep(2)
            continue

main(driver)
# 退出
driver.quit()