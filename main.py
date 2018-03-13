import requests
import os
import sys
import json
from lxml import etree
import re
import datetime
import threading
import hashlib
import time
from common_lib import MyArgParse, LogHandle, ThreadHandler
from sqlite_util import DBRowHuaBan, DBHandler, DBRow, DBItem

gstLogHandle = LogHandle('geo.log')


class DBRowGeo(DBRow):
    def do_init(self):
        self.item_list.append(DBItem('pageUrl', 'CHAR'))
        self.item_list.append(DBItem('title', 'CHAR'))
        self.item_list.append(DBItem('profileUrl', 'CHAR'))
        self.item_list.append(DBItem('altText', 'CHAR'))
        self.item_list.append(DBItem('url', 'CHAR'))
        self.item_list.append(DBItem('url_hash', 'CHAR', is_primary=True))
        self.item_list.append(DBItem('is_done', 'INT'))
        pass

    def generate_select_cmd_str(self, table_name):
        ret_str = ' select '
        for idx, item in enumerate(self.item_list):
            ret_str += table_name + '.' + item.name
            if idx != len(self.item_list)-1:
                ret_str += ' , '
        ret_str += ' from %s where %s.%s == 0' % (table_name, table_name, self.item_list[6].name)
        return ret_str
        pass


class GEOPicInfo:
    def __init__(self):
        self.log = gstLogHandle.log

        self.m_pageUrl = ''
        self.m_title = ''
        self.m_profileUrl = ''
        self.m_altText = ''
        self.url = ''
        pass

    def load_from_dict(self, dict_info):
        if dict_info.has_key('originalUrl'):
            self.url = 'http://yourshot.nationalgeographic.com' + dict_info['originalUrl']
        elif dict_info.has_key('url'):
            self.url = dict_info['url']
        else:
            self.log('Failed to find pic url')
            return False
        try:
            if dict_info.has_key('pageUrl'):
                self.m_pageUrl = dict_info['pageUrl']
            if dict_info.has_key('title'):
                self.m_title = dict_info['title']
            if dict_info.has_key('profileUrl'):
                self.m_profileUrl = dict_info['profileUrl']
            if dict_info.has_key('altText'):
                self.m_altText = dict_info['altText']
        except KeyError:
            self.log('Maybe missing some pic info')
            pass
        return True

        pass


class GETYourShotDownloadThreadMng(ThreadHandler):
    def do_init(self):
        self.m_set_work_thread_cnt = 10
        self.log = gstLogHandle.log


        self.m_succeed_done_task_list = list()
        self.m_falied_done_task_list = list()
        pass

    def work_thread(self):
        while True:
            if self.m_quit_flag:
                break
            row = self.get_one_task()
            if row is None:
                if self.m_load_task_done:
                    break
                time.sleep(3)
                continue
            # row = DBRowGeo()
            url = row.get_column_value('url')
            self.log(url)
            try:
                req = requests.request('GET', url, timeout=40)
            except requests.ConnectionError:
                self.log('Time out download pic')
            if 200 == req.status_code:
                m = hashlib.md5()
                m.update(url)
                file_name = m.hexdigest() + '.jpg'
                # file_name = os.path.basename(url)
                store_img(file_name, req.content)
                self.lock.acquire()
                self.m_succeed_done_task_list.append(row)
                self.lock.release()
                self.log('Done [%s]' % url)
            else:
                print 'Failed to parse url [%s]' % url
        pass

    def do_start(self):
        self.start_one_thread(self.load_task_thread)
        pass

    def load_task_thread(self):
        db_handler = DBHandler(DBRowGeo)
        db_handler.load('geo.db')
        db_handler.add_table('yourshot')
        while True:
            if self.m_quit_flag:
                break
            if len(self.m_task_list) >= 1:
                self.log('Task list len [%d]' % len(self.m_task_list))
                time.sleep(3)
                continue
            rows = db_handler.get_row(200)
            if not len(rows):
                break

            self.add_tasks(rows)
            while True:
                if len(self.m_succeed_done_task_list):
                    row = self.m_succeed_done_task_list.pop()
                    row.set_column_value('is_done', 1)
                    db_handler.update_row(row)
                else:
                    break

        self.m_load_task_done = True
        self.log('Load task Done')
        while True:
            if len(self.m_succeed_done_task_list):
                row = self.m_succeed_done_task_list.pop()
                row.set_column_value('is_done', 1)
                db_handler.update_row(row)
            elif self.m_quit_flag:
                break
            time.sleep(3)
        pass


class GEOYourShotScrap:
    def __init__(self):
        self.db_handler = DBHandler(DBRowGeo)
        self.db_handler.load('geo.db')
        self.db_handler.add_table('yourshot')

        self.log = gstLogHandle.log
        pass

    def do_init(self):
        pass

    def store_urls(self, pic_info_dict):
        pic_info = GEOPicInfo()
        if not pic_info.load_from_dict(pic_info_dict):
            return False
        db_row = DBRowGeo()

        # self.item_list.append(DBItem('pageUrl', 'CHAR'))
        # db_row.item_list[0].value = pic_info.m_pageUrl
        # self.item_list.append(DBItem('title', 'CHAR'))
        # db_row.item_list[1].value = pic_info.m_title
        # self.item_list.append(DBItem('profileUrl', 'CHAR'))
        # db_row.item_list[2].value = pic_info.m_profileUrl
        # self.item_list.append(DBItem('altText', 'CHAR'))
        # db_row.item_list[3].value = pic_info.m_altText
        # self.item_list.append(DBItem('url', 'CHAR'))
        # db_row.item_list[4].value = pic_info.url
        # self.item_list.append(DBItem('url_hash', 'INT', is_primary=True))
        # m = hashlib.md5()
        # m.update(pic_info.url)
        # db_row.item_list[5].value = m.hexdigest()
        # self.item_list.append(DBItem('is_done', 'INT'))
        # db_row.item_list[6].value = 0
        m = hashlib.md5()
        m.update(pic_info.url)
        db_row.load((pic_info.m_pageUrl, pic_info.m_title, pic_info.m_profileUrl, pic_info.m_altText, pic_info.url, m.hexdigest(), 0))

        self.db_handler.insert_row(db_row)
        pass

    def parse_urls(self, date_str):
        url = 'http://www.nationalgeographic.com/photography/photo-of-the-day/_jcr_content/.gallery.%s.json' % date_str
        head = {'Host': 'www.nationalgeographic.com',
                'Usr-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:54.0) Gecko/20100101 Firefox/54.0',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'X-NewRelic-ID': 'Uw4AWVVACgsJVVlWAwM=',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'http://www.nationalgeographic.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Cache-Control': 'Cache-Control'}
        req = requests.request('GET', url, headers=head)
        print req.status_code
        write_content(req.content, 'page.json')
        if 200 == req.status_code:
            json_root = json.loads(req.content)
            print 'Total cnt [%d]' % len(json_root['items'])
            for item in json_root['items']:
                self.store_urls(item)
            pass
        pass
        pass

    def parse_all(self):
        year = 2016
        month = 1
        cur_date = datetime.datetime.now()
        while True:
            date_str = '%d-%02d' % (year, month)
            self.log('Start to get %s' % date_str)
            self.parse_urls(date_str)
            month += 1
            if month > 12:
                month = 1
                year += 1
            if year >= cur_date.year and month > cur_date.month:
                break
        self.log('All Done')
        pass

    def store_pic_file(self):
        pass

    def do_download(self, url):
        pass

    def do_get_pics(self):
        download_handler = GETYourShotDownloadThreadMng()
        download_handler.start()
        while True:
            time.sleep(10)
            if download_handler.m_quit_flag:
                self.log('Main All quit')
                break
        pass




def write_content(content, file_name='default.content'):
    with open(file_name, 'w+') as fd:
        fd.write(content)


def test():
    url = 'http://www.nationalgeographic.com/'
    req = requests.request('GET', url)
    write_content(req.content)
    parse_front_page(req.content)
    pass


def parse_json_from_script(content):
    ret_json_url = None
    pattern = '\"endpoint\":\"(?P<json_url>\S+.json)\"'
    m = re.search(pattern, content)
    if m:
        ret_json_url = m.group('json_url')[:]
        #print m.group('json_url')
    else:
        #print 'Not found [%s]' % content
        pass
    return ret_json_url
    pass


def parse_front_page(content):
    root = etree.HTML(content)
    nodes = root.xpath('//div/script')
    print len(nodes)
    for script_node in nodes:
        if script_node.text:
            json_url = parse_json_from_script(script_node.text)
            if json_url:
                parse_page_url_from_json_url(json_url)

    pass


def parse_page_url_from_json_url(json_url):
    print 'Json-Url: [%s]' % json_url
    tmp_json_file_name = 'json.content'
    req = requests.request('GET', json_url)
    write_content(req.content, tmp_json_file_name)
    json_root = json.loads(req.content)
    if json_root.has_key('cards'):
        for card in json_root['cards']:
            print card['link']['url']
    pass


def try_get_json_pre():
    with open('https.json', 'r') as fd:
        json_root = json.load(fd)
        for item in json_root['data']:
            print item['attributes']['uri']
    return
    url = 'https://relay.nationalgeographic.com/proxy/distribution/feed/v1?format=jsonapi&content_type=featured_image&fields=image,uri&collection=fd5444cc-4777-4438-b9d4-5085c0564b44&publication_datetime__from=2009-01-01T18:30:02Z&page=1&limit=48'
    url = 'https://relay.nationalgeographic.com/proxy/distribution/feed/v1?format=jsonapi&content_type=featured_image&fields=image,uri&collection=fd5444cc-4777-4438-b9d4-5085c0564b44&publication_datetime__from=2009-01-01T18:30:02Z&page=2&limit=48'
    head = {'Host':'relay.nationalgeographic.com',
            'Usr-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept':'*/*',
            'apiauth-apikey':'9fa5d22ad7b354fe0f9be5597bcf153df56e2ca5',
            'apiauth-apiuser':'pod_archive',
            'Referer':'http://www.nationalgeographic.com/photography/photo-of-the-day/archive/',
            'Accept-Language':'en-US,en;q=0.5',
            'Accept-Encoding':'gzip, deflate, br',
            'Access-Control-Request-Method':'GET',
            'Access-Control-Reuqest-Headers':'apiauth-apikey,apiauth-apiuser',
            'Origin':'http://www.nationalgeographic.com',
            'DNT':'1',
            'Connection':'keep-alive',
            'Cache-Control':'Cache-Control'}
    req = requests.request('GET', url, headers=head)
    print req.status_code
    write_content(req.content, 'https.json')


def try_get_json():
    url = 'https://relay.nationalgeographic.com/proxy/distribution/feed/v1?format=jsonapi&content_type=featured_image&fields=image,uri&collection=fd5444cc-4777-4438-b9d4-5085c0564b44&publication_datetime__from=2009-01-01T18:30:02Z&page=1&limit=48'
    head = {'Host':'relay.nationalgeographic.com',
            'Usr-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language':'en-US,en;q=0.5',
            'Accept-Encoding':'gzip, deflate, br',
            'Access-Control-Request-Method':'GET',
            'Access-Control-Reuqest-Headers':'apiauth-apikey,apiauth-apiuser',
            'Origin':'http://www.nationalgeographic.com',
            'DNT':'1',
            'Connection':'keep-alive',
            'Cache-Control':'Cache-Control'}
    url = 'https://relay.nationalgeographic.com/proxy/distribution/feed/v1?format=jsonapi&content_type=featured_image&fields=image,uri&collection=fd5444cc-4777-4438-b9d4-5085c0564b44&publication_datetime__from=2009-01-01T18:30:02Z&page=2&limit=48'
    req = requests.request('GET', url, headers=head)
    print req.status_code
    write_content(req.content, 'https.json')

    pass

gInfoStoreFile = 'Urls.txt'
gInfoStoreFd = None


def store_info(str_info):
    global gInfoStoreFile
    global gInfoStoreFd
    if not gInfoStoreFd:
        if os.path.exists(gInfoStoreFile):
            gInfoStoreFd = open(gInfoStoreFile, 'w')
        else:
            gInfoStoreFd = open(gInfoStoreFile, 'w+')
    gInfoStoreFd.write(str_info)
    gInfoStoreFd.write('\n')


def get_page_json(relic_id, date_str):
    #url = 'http://www.nationalgeographic.com/photography/photo-of-the-day/_jcr_content/.gallery.2017-05.json'
    url = 'http://www.nationalgeographic.com/photography/photo-of-the-day/_jcr_content/.gallery.%s.json' % date_str
    head = {'Host':'www.nationalgeographic.com',
            'Usr-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Accept':'application/json, text/javascript, */*; q=0.01',
            'Accept-Language':'en-US,en;q=0.5',
            'Accept-Encoding':'gzip, deflate',
            'X-NewRelic-ID':'Uw4AWVVACgsJVVlWAwM=',
            'X-Requested-With':'XMLHttpRequest',
            'Origin':'http://www.nationalgeographic.com',
            'DNT':'1',
            'Connection':'keep-alive',
            'Cache-Control':'Cache-Control'}
    req = requests.request('GET', url, headers=head)
    print req.status_code
    write_content(req.content, 'page.json')
    if 200 == req.status_code:
        json_root = json.loads(req.content)
        print 'Total cnt [%d]' % len(json_root['items'])
        for item in json_root['items']:
            if item.has_key('originalUrl'):
                full_url = 'http://yourshot.nationalgeographic.com' + item['originalUrl']
            else:
                full_url = item['url']
            store_info(full_url)
        pass
    pass


def store_img(name, content):
    folder = 'img'
    if not os.path.exists(folder):
        os.mkdir(folder)
    full_path = os.path.join(folder, name)
    if os.path.exists(full_path):
        print 'Warning: alread exist [%s]' % full_path
    with open(full_path, 'wb+') as fd:
        fd.write(content)


def thread_get_img(url_list):
    global gAllQuit
    global gRunningThreadCnt
    gRunningThreadCnt += 1
    succeed_list = list()
    failed_list = list()
    for url in url_list:
        if gAllQuit:
            break
        print 'Parse [%s]' % url
        req = requests.request('GET', url, timeout=20)
        if 200 == req.status_code:
            m = hashlib.md5()
            m.update(url)
            file_name = m.hexdigest() + '.jpg'
            # file_name = os.path.basename(url)
            store_img(file_name, req.content)
            succeed_list.append(url)
        else:
            print 'Failed to parse url [%s]' % url
            failed_list.append(url)
    update_task((succeed_list, failed_list))
    gRunningThreadCnt -= 1
    return

gAllQuit = False
gRunningThreadCnt = 0
gSucceedUrlList = list()


def update_task(task_info_tup):
    (succeed_list, failed_list) = task_info_tup
    gSucceedUrlList.extend(succeed_list)
    pass


def update_url_config():
    print 'Update txt'
    pass


def split_task(task_list):
    global gAllQuit
    global gRunningThreadCnt

    set_max_thread = 20
    child_process_list = list()

    filper = 1
    if len(task_list) >= set_max_thread:
        filper = len(task_list) // set_max_thread
        idx = 0
        while (idx+filper-1) < len(task_list):
            try:
                pro = threading.Thread(target=thread_get_img, args=(task_list[idx:idx+filper-1], ))
                pro.setDaemon(False)
                pro.start()
                child_process_list.append(pro)
                idx += filper
            except :
                print ('something err when start thread')
                continue
    tail = len(task_list) % filper
    if tail:
        pro = threading.Thread(target=thread_get_img, args=(task_list[len(task_list)-tail:len(task_list)-1], ))
        pro.setDaemon(False)
        pro.start()
        child_process_list.append (pro)
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            gAllQuit = True
            print 'KeyBoard Except quit now'
            while gRunningThreadCnt > 0:
                time.sleep(1)
            update_url_config()
            print 'Quit!'
            return

    pass


def start_get_all_img():
    url_list = list()
    with open(gInfoStoreFile, 'r') as fd:
        while True:
            line = fd.readline()
            if line:
                url_list.append(line)
            else:
                break
    split_task(url_list)
    pass


def search_new_relic_id_from_content(content):
    # loader_config={xpid:"Uw4AWVVACgsJVVlWAwM="}
    pattern = 'loader_config={xpid:"(?P<relic_id>\S+)"}'
    m = re.search(pattern, content)
    if m:
        print m.group('relic_id')
        return m.group('relic_id')
    else:
        print 'Not Found'
    return None
    pass

def init_arg_handler():
    arg_parse = MyArgParse()
    arg_parse.add_option('-parse', 0, 'do parse')
    arg_parse.add_option('-download', [0], 'specific dir to scan')
    arg_parse.add_option('-d', 1, 'set store folder')
    arg_parse.add_option('-time', 1, 'set parse time 2016-01')
    arg_parse.add_option('-h', 0, 'print default scan folder and des folder')
    return arg_parse


def test_2():
    your_shot_handler = GEOYourShotScrap()
    #your_shot_handler.parse_all()
    your_shot_handler.do_get_pics()

if __name__ == '__main__':
    your_shot_handler = GEOYourShotScrap()
    arg_handler = init_arg_handler()
    arg_handler.parse(sys.argv)
    if arg_handler.check_option('-h'):
        print arg_handler
        exit(0)
    if arg_handler.check_option('-parse'):
        your_shot_handler.parse_all()
    elif arg_handler.check_option('-download'):
        your_shot_handler.do_get_pics()

    exit()
    with open('tmp/photo-of-day-main.html', 'r') as fd:
        buf = fd.read()
        search_new_relic_id_from_content(buf)
    #try_get_json_pre()
    #try_get_json()
    exit(0)
    test()
