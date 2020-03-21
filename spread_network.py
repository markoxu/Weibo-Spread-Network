# -*- coding: UTF-8 -*-

import os
import sys
import time
import random
import traceback
import requests
from lxml import etree

import networkx as nx
import matplotlib.pyplot as plt


class Weibo(object):
    def __init__(self, config):
        """Weibo类初始化"""
        self.header = config['header']
        self.weibo = config['weibo']
        self.cookies = {'Cookie': config['cookie']}
        self.cur_page = 0
        self.total_page = 0
        self.requesttimes = 0

    def handle_html(self, url):
        """处理html"""
        try:
            self.requesttimes += 1
            html = requests.get(url, cookies=self.cookies).content
            selector = etree.HTML(html)
            if self.requesttimes % 100 == 0:
                time.sleep(60)
            else:
                time.sleep(random.random() * 10)
            return selector
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_user_id_and_name(self, selector):
        """获取用户的id和昵称"""
        try:
            print('获取用户的id和昵称')
            hrefs = selector.xpath("//div[@class='c' and @id='M_']//a//@href")
            user_id, user_nickname = None, None
            for href in hrefs:
                if 'fuid' in href:
                    hrefs = href.split('&')[1]
                    user_id = hrefs[hrefs.find('=') + 1:]
                    break
            user_nickname = '@' + selector.xpath("//div[@class='c' and @id='M_']/div/a/text()")[0]
            return (user_id, user_nickname)
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_total_retweet_page(self, selector):
        """获取微博总页数"""
        try:
            print('获取微博总页数')
            if selector.xpath("//input[@name='mp']") == []:
                page_num = 1
            else:
                page_num = (int)(
                    selector.xpath("//input[@name='mp']")[0].attrib['value'])
            return page_num
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_retweet_weibo(self, start_page):
        """获取所有转发微博"""
        try:
            print('获取所有转发微博')
            file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + '{0}.txt'.format(
                self.weibo)
            f = open(file_dir, 'w')
            s = self.handle_html(self.header + self.weibo)
            user_id, user_nickname = self.get_user_id_and_name(s)
            self.total_page = self.get_total_retweet_page(s)
            print(user_id, user_nickname, self.total_page)
            f.write(user_id + ' ' + user_nickname + ' ' + str(self.total_page) + '\n')
            for page in range(start_page, self.total_page):
                print(str(page + 1) + '=' * 50)
                url = self.header + self.weibo + '?page={0}'.format(page + 1)
                selector = self.handle_html(url)
                retweet_len = len(selector.xpath("//div[@class='c']"))
                for i in range(retweet_len):
                    retweet_users = selector.xpath("//div[@class='c'][{0}]/a/text()".format(i + 1))
                    retweet_content = selector.xpath("//div[@class='c'][{0}]/text()".format(i + 1))
                    # 如果转发内容里面存在"：回复"应该也要算的，因为其实是快转
                    retweet_content = [content for content in retweet_content if '//' != content]
                    retweet_users = [retweet_users[i] for i in range(len(retweet_content)) if
                                     retweet_content[i].startswith(':') and i < len(retweet_users)]
                    if len(retweet_users) == 0:
                        continue
                    retweet_users[0] = '@' + retweet_users[0]
                    if len(retweet_users) == 1:
                        print(user_nickname, retweet_users[0])
                        f.write(user_nickname + ' ' + retweet_users[0] + '\n')
                    else:
                        print(user_nickname, retweet_users[-1])
                        f.write(user_nickname + ' ' + retweet_users[-1] + '\n')
                        for j in range(len(retweet_users) - 1, 0, -1):
                            print(retweet_users[j], retweet_users[j - 1])
                            f.write(retweet_users[j] + ' ' + retweet_users[j - 1] + '\n')
                self.cur_page = page
            f.close()
        except Exception as e:
            f.close()
            print('Error: ', e)
            traceback.print_exc()

    def creat_retweet_network(self, weibo):
        """生成转发网络"""
        try:
            import pygraphviz
            from networkx.drawing.nx_agraph import graphviz_layout
        except ImportError:
            try:
                import pydot
                from networkx.drawing.nx_pydot import graphviz_layout
            except ImportError:
                raise ImportError("This example needs Graphviz and either PyGraphviz or pydot")
        print('生成转发网络')
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep
        f = open(file_dir + '{0}.txt'.format(weibo))
        headline = f.readline()
        lines = f.readlines()
        root_node = lines[0].split()[0]
        f.close()
        graph = nx.DiGraph()
        for line in lines:
            pairs = line.split()
            if not pairs[0].startswith('@') or pairs[0] == pairs[1]:
                continue
            graph.add_edge(pairs[0], pairs[1])
        plt.figure(figsize=(8, 8))
        pos = graphviz_layout(graph, prog='twopi', root=root_node)
        nx.draw(graph, pos,
                node_size=[i[1] * 2 for i in graph.degree(graph)],
                width=0.5, alpha=1,
                node_color="b",
                edge_color="k",
                arrowstyle="->", arrowsize=10, with_labels=False)
        plt.axis('equal')
        plt.savefig(file_dir + weibo + '.png', bbox_inches='tight')


def main():
    """运行爬虫"""
    try:
        config = {
            "header": "https://weibo.cn/repost/",
            "weibo": "weibo uuid",
            "cookie": "your cookie"
        }
        wb = Weibo(config)
        wb.get_retweet_weibo(start_page=0)
        wb.creat_retweet_network(config['weibo'])
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc()


if __name__ == '__main__':
    main()
