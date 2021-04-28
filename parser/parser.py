import requests
from bs4 import BeautifulSoup
import re
import cyrtranslit
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from json import dumps

class GooglePlayParser(object):
    BASE_URL = 'https://play.google.com'
    FETCH_NEXT = '_/PlayStoreUi/data/batchexecute?rpcids=qnKhOb&bl=boq_playuiserver_20210428.04_p0&authuser=0&soc-app=121&soc-platform=1&soc-device=1'
    REQ_BODY = 'f.req=%5B%5B%5B%22qnKhOb%22%2C%22%5B%5Bnull%2C%5B%5B10%2C%5B10%2C50%5D%5D%2Ctrue%2Cnull%2C%5B96%2C27%2C4%2C8%2C57%2C30%2C110%2C79%2C11%2C16%2C49%2C1%2C3%2C9%2C12%2C104%2C55%2C56%2C51%2C10%2C34%2C77%5D%5D%2Cnull%2C%5C%22{token}%5C%22%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D'

    apps = {}
    
    def __init__(self, keyword):
        self.keyword = keyword
        self.kwdict = {'ru': cyrtranslit.to_cyrillic(keyword, 'ru'),
                       'en': cyrtranslit.to_latin(keyword, 'ru')}
        self.app_links = {}
        self.app_list = []
    
    def fetch_first_chunk(self):
        response = requests.get(f'https://play.google.com/store/search?q={self.keyword}&c=apps')
        html = BeautifulSoup(response.text, 'lxml')
        app_links = set([self.BASE_URL + obj['href'] for obj in html.select('c-wiz > div > div > div > div > div > a') if obj['href'].startswith('/store/apps/details')])
        token = [obj for obj in html.select('div > div > c-wiz > div > div > div > c-wiz > c-wiz > c-wiz > c-data')][0]['jsdata'].split(';')[3]
        self.app_links[token] = app_links
        return token

    def fetch_next_chunk(self, token):
        headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
        response = requests.post(self.BASE_URL + '/' + self.FETCH_NEXT, data=self.REQ_BODY.format(token=token), headers=headers)
        apps = re.findall(r'/store/apps/details\?[\\.A-Za-z0-9]*', response.text)
        while token in self.app_links:
            token += '1'
        self.app_links[token] = set([self.BASE_URL + app.replace('\\\\u003d', '=').replace('\\', '') for app in apps])
        token = re.search(r'null,\[null,\\"([A-Za-z0-9-]*)((?!store|google).)*generic', response.text)
        if token:
            return token.group(1)
        else:
            return None

    def get_app_links(self):
        self.app_list = []
        self.app_links = {}
        token = self.fetch_first_chunk()
        while token is not None:
            token = self.fetch_next_chunk(token)
        for token in self.app_links:
            self.app_list += list(self.app_links[token])

    def safe_select(self, html, selector, id):
        res = html.select(selector)
        if len(res) <= id:
            return None
        else:
            return res[id].text

    def parse_app_helper(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            html = BeautifulSoup(content, 'lxml')
            id = url[url.find('=') + 1:]
            name = self.safe_select(html, 'h1.AHFaub > span', 0)
            description = self.safe_select(html, 'div.DWPxHb > span > div', 0)
            name_re = re.search(f'{self.kwdict["ru"]}|{self.kwdict["en"]}', name, re.IGNORECASE)
            desc_re = re.search(f'{self.kwdict["ru"]}|{self.kwdict["en"]}', description, re.IGNORECASE)
            if name_re is None and desc_re is None:
                return
            developer = self.safe_select(html, 'span.T32cc.UAO9ie > a', 0)
            category = self.safe_select(html, 'a.hrTbp.R8zArc', 0)
            rating = self.safe_select(html, 'div.BHMmbe', 0)
            reviews_count = self.safe_select(html, 'span.EymY4b > span', 1)
            last_update = self.safe_select(html, 'span.htlgb', 0)
            self.apps[id] = {'name': name,
                             'url': url,
                             'developer': developer,
                             'category': category,
                             'description': description,
                             'rating': rating,
                             'reviews_count': reviews_count,
                             'last_update': last_update}

    def parse_apps(self):
        self.get_app_links()
        pool = ThreadPool(processes=cpu_count() * 10)
        pool.map(self.parse_app_helper, self.app_list)
        pool.close()
        pool.join()
        return dumps(self.apps, indent=4)


if __name__ == '__main__':
    
    keyword = input('Keyword: ')
    parser = GooglePlayParser(keyword)
    json_data = parser.parse_apps()
    print(json_data)