# -*- coding: UTF-8 -*-

import os
import sys
import json
import traceback
import requests
from lxml import etree
import re
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import random
import datetime as dt

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    filename=r'logging.log')


class Mail(object):
    def __init__(self):
        """初始化邮件参数"""
        self.mail_host = "smtp.qq.com"
        self.mail_password = ""
        self.sender = ''
        self.receivers = ['']

    def send(self, content):
        """发送邮件"""
        try:
            message = MIMEText('', 'plain', 'utf-8')
            message['Subject'] = Header(content, 'utf-8')
            message['From'] = Header("微博助手", 'utf-8')
            message['To'] = Header("订阅者", 'utf-8')
            smtpObj = smtplib.SMTP_SSL(self.mail_host, 465)
            smtpObj.login(self.sender, self.mail_password)
            smtpObj.sendmail(self.sender, self.receivers, message.as_string())
            smtpObj.quit()
            logging.info('send email to: {0}'.format(self.receivers))
        except Exception as e:
            logging.error('邮件发送错误')


class Weibo(object):
    def __init__(self, config):
        """初始化配置文件"""
        self.users_id_list = config['user_id_list']
        self.cookie = {'Cookie': config['cookie']}
        self.filter = config['filter']
        self.since_date = config['since_date']
        self.write_mode = ['write_mode']
        self.picture_download = config['pic_download']
        self.video_download = config['video_download']
        self.user_info = None
        self.request_times = 0

    def request_html(self, url):
        """获取响应文件"""
        try:
            print(url)
            response = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(response)
            self.request_times += 1
            if self.request_times % 20 == 0:
                time.sleep(random.randint(3, 5))
            return selector
        except Exception as e:
            traceback.print_exc()
            logging.error(traceback.format_exc())

    def save_user_info(self, weibo_info):
        weibo_info_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + weibo_info['user_id'] + '.json'
        with open(weibo_info_path, 'w', encoding="utf-8") as f:
            json.dump(weibo_info, f, ensure_ascii=False)

    def get_user_info(self, user_id):
        """获取微博信息"""
        url = 'https://weibo.cn/{0}'.format(user_id)
        info_selector = self.request_html(url)
        user_name = info_selector.xpath('//title/text()')[0][:-3]
        if user_name == u'登录 - 新':
            logging.error('cookie已失效')
            sys.exit(u'cookie已失效')
        information = info_selector.xpath("//div[@class='u']/div[@class='tip2']//text()")
        user_info = dict()
        user_info['user_name'] = user_name
        user_info['user_id'] = user_id
        user_info['weibo_number'] = int(re.findall(r"\d+", information[0])[0])
        user_info['followee_number'] = int(re.findall(r"\d+", information[2])[0])
        user_info['follower_number'] = int(re.findall(r"\d+", information[4])[0])
        user_info['page_number'] = 1
        if len(info_selector.xpath("//input[@name='mp']")) != 0:
            user_info['page_number'] = (int)(info_selector.xpath("//input[@name='mp']")[0].attrib['value'])
        self.user_info = user_info
        self.save_user_info(user_info)

    def get_publish_time_tool(self, one_weibo_selector):
        """获取发布时间和发布工具"""
        publish_time_tool = str(one_weibo_selector.xpath("div/span[@class='ct']/text()")[0])
        publish_time, publish_tool = publish_time_tool.split('\xa0来自')
        if u'刚刚' in publish_time:
            publish_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
        elif u'前' in publish_time:
            delta_minute = int(re.findall(r"\d+", publish_time)[0])
            publish_time = (dt.datetime.now() - dt.timedelta(minutes=delta_minute)).strftime('%Y-%m-%d %H:%M')
        elif u'今天' in publish_time:
            publish_time = dt.datetime.now().strftime('%Y-%m-%d') + ' ' + publish_time[3:]
        elif u'月' in publish_time:
            publish_time = dt.datetime.now().strftime('%Y') + '-' \
                           + publish_time[0:2] + '-' \
                           + publish_time[3:5] + ' ' \
                           + publish_time[7:12]
        else:
            publish_time = publish_time[:16]
        return publish_time, publish_tool

    def get_weibo_info(self, one_weibo_selector):
        """获取一条微博基本信息"""
        weibo_footer = one_weibo_selector.xpath('div')[-1].xpath('./a/text()')[-4:]
        weibo_footer = re.findall(r'\d+', str(weibo_footer))
        weibo_info = dict()
        weibo_info['weibo_id'] = one_weibo_selector.xpath('@id')[0][2:]
        weibo_info['like_number'] = int(weibo_footer[0])
        weibo_info['retweet_number'] = int(weibo_footer[1])
        weibo_info['comment_number'] = int(weibo_footer[2])
        publish_time, publish_tool = self.get_publish_time_tool(one_weibo_selector)
        weibo_info['publish_time'] = publish_time
        weibo_info['publish_tool'] = publish_tool
        return weibo_info

        # def get_publish_time(self, info):
        #     """获取微博发布时间"""

        #
        # def get_publish_tool(self, info):
        #     """获取微博发布工具"""
        #     try:
        #         str_time = info.xpath("div/span[@class='ct']")
        #         str_time = self.handle_garbled(str_time[0])
        #         if len(str_time.split(u'来自')) > 1:
        #             publish_tool = str_time.split(u'来自')[1]
        #         else:
        #             publish_tool = u'无'
        #         return publish_tool
        #     except Exception as e:
        #         print('Error: ', e)
        #         traceback.print_exc()

    def is_original_weibo(self, one_weibo_selector):
        """判断是否为原创微博"""
        elements_cmt = one_weibo_selector.xpath("div/span[@class='cmt']")
        return True if len(elements_cmt) <= 3 else False

    def is_long_weibo(self, one_weibo_selector):
        """判断是否为长篇微博"""
        elements_text = one_weibo_selector.xpath("div//a/text()")
        return True if u'全文' in elements_text else False

    def get_one_weibo(self, one_weibo_selector):
        """处理一条微博"""
        # 获取微博基本信息，是否转发，发布位置，发布时间，发布工具，点赞数，转发数，评论数
        # 获取微博正文，判断是否转发，长文
        # 获取微博中的图片和视频，包括链接和数据
        # 获取微博信息

        is_original = self.is_original_weibo(one_weibo_selector)
        is_long = self.is_long_weibo(one_weibo_selector)
        weibo_info = self.get_weibo_info(one_weibo_selector)
        print(weibo_info)
        # 最红都是获取微博的信息保存，区分在于长短微博(重新打开)，应该不是是否转发（直接读取）

        # if is_long:
        #     # 长微博处理，打开网页
        #     url = 'https://weibo.cn/comment/{0}'.format()
        #
        #     weibo_link = 'https://weibo.cn/comment/' + weibo_id
        #     wb_content = self.get_long_weibo(weibo_link)
        #     if wb_content:
        #         weibo_content = wb_content
        #
        # for i in range(5):
        #     selector = self.handle_html(weibo_link)
        #     if selector is not None:
        #         info = selector.xpath("//div[@class='c']")[1]
        #         wb_content = self.handle_garbled(info)
        #         wb_time = info.xpath("//span[@class='ct']/text()")[0]
        #         weibo_content = wb_content[wb_content.find(':') +
        #                                    1:wb_content.rfind(wb_time)]
        #         if weibo_content is not None:
        #             return weibo_content
        #     sleep(random.randint(6, 10))
        #
        #
        #
        #
        # else:
        #     # 短微博处理，直接处理
        #     pass

    def get_one_page_weibo(self, weibo_id, page):
        """处理一页微博"""
        try:
            url = 'https://weibo.cn/{0}?page={1}'.format(weibo_id, page)
            one_page_selector = self.request_html(url)
            one_page_selector = one_page_selector.xpath("//div[@class='c']")
            for i in range(len(one_page_selector) - 2):
                self.get_one_weibo(one_page_selector[i])
        except Exception as e:
            traceback.print_exc()

    def get_all_weibo(self, weibo_id):
        """处理所有微博"""
        for page in range(1, self.user_info['page_number'] + 1):
            self.get_one_page_weibo(weibo_id, page)
            # break

    def start(self):
        """运行爬虫"""
        for i in range(len(self.users_id_list)):
            user_id = self.users_id_list[i]
            self.get_user_info(user_id)
            print(self.user_info)
            self.get_all_weibo(user_id)


def main():
    """主程序"""
    config_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'config.json'
    if not os.path.isfile(config_path):
        logging.error('配置文件{0}不存在'.format(config_path))
        sys.exit()
    with open(config_path) as fp:
        config = json.load(fp)
    weibo = Weibo(config)
    selector = weibo.start()
    return selector


if __name__ == '__main__':
    selector = main()
