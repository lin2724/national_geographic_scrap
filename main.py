import requests
import os
import sys
import json
from lxml import etree
import re
import datetime


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
    url = 'https://relay.nationalgeographic.com/proxy/distribution/feed/v1?format=jsonapi&content_type=featured_image&fields=image,uri&collection=fd5444cc-4777-4438-b9d4-5085c0564b44&publication_datetime__from=2009-01-01T18:30:02Z&page=2&limit=48'
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
            if item.has_key('url'):
                full_url = item['url']
            else:
                full_url = 'http://yourshot.nationalgeographic.com' + item['originalUrl']
            store_info(full_url)
            #print 'http://yourshot.nationalgeographic.com' + item['originalUrl']
        pass

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


if __name__ == '__main__':
    start_date = datetime.date(year=2016, month=1, day=1)
    end_date = datetime.date(year=2017, month=7, day=1)
    cur_date = start_date
    while cur_date < end_date:
        date_str = '%s-%2d' % (cur_date.year, cur_date.month)
        print date_str
        

    get_page_json('', '')
    exit()
    with open('tmp/photo-of-day-main.html', 'r') as fd:
        buf = fd.read()
        search_new_relic_id_from_content(buf)
    #try_get_json_pre()
    #try_get_json()
    exit(0)
    test()