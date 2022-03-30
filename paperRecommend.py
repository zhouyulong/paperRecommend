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


class ArxivReList():
    def __init__(self):
        self.url = {}
        self.title = ''
        self.authors = []
        self.abstract = ''
        self.submitted_date = ''


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
    except Exception:
        pass
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


def send_mail(content):
    # 设置服务器信息
    mail_host = config.get('mail', 'host')
    mail_user = config.get('mail', 'user')
    mail_pass = config.get('mail', 'pass')
    sender = mail_user
    receivers = config.get('mail', 'receivers').split(',')
    print(receivers)

    # 设置 emil 信息
    # 邮件内容设置
    text = content
    message = MIMEText(text, 'plain', 'utf-8')
    # 邮件主题
    message['Subject'] = config.get('mail','arxiv_subject')
    # 发送方信息
    message['From'] = sender
    # 接收方信息
    for receiver in receivers:
        print(receiver)
        message['To'] = receiver
        logger.info(f'正在给 {receiver} 发送邮件…… {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')

        # 登录发送
        try:
            # smtpObj = smtplib.SMTP()
            # # 连接服务器
            # smtpObj.connect(mail_host, 587)
            # qq 邮箱需要使用 smtp_ssl
            smtpObj = smtplib.SMTP_SSL(mail_host,465)
            # 登录
            smtpObj.login(mail_user, mail_pass)
            # 发送
            smtpObj.sendmail(
                sender,receiver,message.as_string()
            )
            # 退出
            smtpObj.quit()
            print('邮件发送成功')
            logger.info(f' 发送邮件成功 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
        except smtplib.SMTPException as e:
            print('error: ', e)
            logger.info(f' 发送邮件失败 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')


def arxiv_main():
    key_words = config.get('paper', 'keywords').split(',')
    result = get_new_paper_from_arxiv(key_words)
    content = []
    index = 0
    for i in result:
        index += 1
        urls = [':'.join(list(url)) for url in i.url.items()]
        temp = f'第 {index} 篇\n'+ '标题： ' + i.title + '\n' +'作者： '+ ';'.join(i.authors) + '\n' +'摘要： '+ i.abstract + '\n' +'日期： '+ i.submitted_date + '\n'+ '链接： ' + ' -- '.join(urls) + '\n' +'-----------------------\n'
        content.append(temp)

    send_mail(''.join(content))


if __name__ == '__main__' :
    logger.add('paperRecommending.log')
    logger.info(f'邮件服务启动 {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')

    config_path = 'paperConfig.ini'
    if not os.path.exists(config_path):
        raise FileNotFoundError('config file not Exist')
    config = ConfigParser()
    config.read(config_path, encoding='utf-8')
    schedule.every().day.at('22:00').do(arxiv_main)
    # schedule.every().minute.do(arxiv_main)

    while True:
        schedule.run_pending()
        time.sleep(5)
