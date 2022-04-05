import requests
from bs4 import BeautifulSoup
# !pip install lxml
import smtplib
from email.mime.text import MIMEText
import schedule
import time
from loguru import logger
from configparser import ConfigParser
import os
import json


class ArxivReList():
    def __init__(self):
        self.url = {}
        self.title = ''
        self.authors = []
        self.abstract = ''
        self.submitted_date = ''


# 配置信息
class Configure():

    def __init__(self):
        self.mail_host = ''
        self.mail_user = ''
        self.mail_password = ''
        self.mail_receivers = []
        self.mail_subjects = []
        self.paper_keywords = {}
        config_path = 'paperConfig.ini'
        if not os.path.exists(config_path):
            raise FileNotFoundError('config file not Exist')
        self.config = ConfigParser()
        self.config.read(config_path, encoding='utf-8')

    def get_mail_config(self):
        mail = {}
        try:
            mail['host'] = self.config['mail']['host']
            mail['user'] = self.config['mail']['user']
            mail['password'] = self.config['mail']['pass']
            mail['receivers'] = self.config['mail']['receivers']
        except Exception as e:
            print(f'Exception: {e} --- {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
        finally:
            pass
        return mail

    def get_paper_config(self):
        paper = {}
        try:
            keywords = json.loads(self.config['paper']['keywords'])
            paper['keywords'] = keywords
        except Exception as e:
            print(f'Exception: {e} --- {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
        finally:
            pass
        return paper


# 分析每 arxiv 一个结果
def result_context_analyse(find_result):
    result = ArxivReList()
    # get links of paper
    urls = find_result.find(class_='list-title').find_all('a')
    for i in urls:
        result.url[i.string] = i.get('href')

    # get title
    title = find_result.find(class_='title')
    result.title = ''.join([i.strip() for i in list(title.strings)])

    # get authors
    authors_context = find_result.find(class_='authors')
    author_list = [name.strip() for name in list(authors_context.strings)]
    author_list = list(set(author_list))
    author_list.remove('')
    try:
        author_list.remove(',')
    except Exception as e:
        print(f'author_list error: {e} --- {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    finally:
        pass
    author_list.remove('Authors:')
    result.authors = author_list

    # get abstract
    abstract_context = find_result.find(class_='abstract-full')
    abstract_list =[con for con in abstract_context.strings]
    abstract_list.pop()
    abstract_list.pop()
    ab_result_list = []
    for ab in abstract_list:
        ab_result_list.append(ab.replace('\n',''))
    result.abstract = ''.join(ab_result_list)

    # get submitted date
    date_context = find_result.find(class_='is-size-7', name='p')
    date_list = [d for d in date_context.strings]
    result.submitted_date = date_list[1].replace(';', '')
    return result


# 指定关键字获取 arxiv 最新的论文
def get_new_paper_from_arxiv(key_words):
    url = f'https://arxiv.org/search/?query={"+".join(key_words)}&searchtype=all&source=header'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    find_results = soup.findAll(class_='arxiv-result')
    results = []
    for find_result in find_results:
        results.append(result_context_analyse(find_result))
    return results


def send_mail(content, subject='无主题'):
    mail_config = config.get_mail_config()
    # 设置服务器信息
    mail_host = mail_config['host']
    mail_user = mail_config['user']
    mail_pass = mail_config['password']
    sender = mail_user
    # receivers = config.get('mail', 'receivers').split(',')
    receivers = mail_config['receivers'].split(',')

    # 设置 emil 信息
    # 邮件内容设置
    text = content
    message = MIMEText(text, 'plain', 'utf-8')
    # 邮件主题
    message['Subject'] = subject
    # 发送方信息
    message['From'] = sender
    # 接收方信息
    try:
        for receiver in receivers:
            message['To'] = receiver
            print('-------receiver----------', receiver)
            smtpObj = smtplib.SMTP_SSL(mail_host, 465)
            # 登录
            smtpObj.login(mail_user, mail_pass)
            # 发送
            smtpObj.sendmail(
                sender, receiver, message.as_string()
            )
            print('邮件发送成功')
            logger.info(f' 发送邮件成功 -- {receiver} -- {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    except smtplib.SMTPException as e:
        print(f'send mail err: {e} -- {receiver} --{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
        logger.info(f'send mail err: {e} -- {receiver} --{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    finally:
        # 退出
        smtpObj.quit()
        print('邮件登出')
        logger.info(f'邮件登出 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')


def arxiv_main():
    # key_words = config.get('paper', 'keywords').split(',')
    paper_config = config.get_paper_config()
    key_words = paper_config['keywords']['arxiv']
    for words in key_words:
        result = get_new_paper_from_arxiv(words)
        content = []
        index = 0
        for i in result:
            index += 1
            urls = [':'.join(list(url)) for url in i.url.items()]
            temp = f'第 {index} 篇\n' + '标题： ' + i.title + '\n' + '作者： ' + ';'.join(i.authors) + '\n' +'摘要： '+ i.abstract + '\n' +'日期： '+ i.submitted_date + '\n'+ '链接： ' + ' -- '.join(urls) + '\n' +'-----------------------\n'
            content.append(temp)

        mail_subject = f'每日订阅(arxiv) -- {" ".join(words)}'
        send_mail(''.join(content), mail_subject)


if __name__ == '__main__' :
    logger.add('paperRecommending.log')
    logger.info(f'邮件服务启动 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    config = Configure()
    # print('mail_host: ', test_config.mail_host)
    # print('mail_host: ', test_config.mail_host)
    schedule.every().day.at('22:00').do(arxiv_main)
    # schedule.every().minute.do(arxiv_main)

    while True:
        schedule.run_pending()
        time.sleep(5)
