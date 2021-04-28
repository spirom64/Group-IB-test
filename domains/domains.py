from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from itertools import combinations
from dns import resolver

class DomainSearcher(object):

    homoglyphs = {
        'o': ('0',),
        '0': ('o',),
        'i': ('1', 'l'),
        'l': ('1', 'i'),
        '1': ('i', 'l')
    }

    found_ips = {}

    def __init__(self, keywords_file, domains_file):
        self.keywords_file = keywords_file
        self.domains_file = domains_file

    def combinations_all(self, iterable):
        res = []
        for i in range(1, len(iterable) + 1):
            res.extend(combinations(iterable, i))
        return res

    def find_all(self, word, sym):
        res = []
        for i, tmp_sym in enumerate(word):
            if tmp_sym == sym:
                res.append(i)
        return res

    def apply_replacement(self, word, sym_list):
        res = []
        if len(sym_list) == 0:
            return [word]
        sym_index = sym_list[0]
        for sym in self.homoglyphs[word[sym_index]]:
            new_word = word[:sym_index] + sym + word[sym_index + 1:]
            res.extend(self.apply_replacement(new_word, sym_list[1:]))
        return res

    def generate_replacements(self, keyword):
        sym_to_replace = []
        for sym in self.homoglyphs:
            sym_to_replace.extend(self.find_all(keyword, sym))
        res = []
        for comb in self.combinations_all(sym_to_replace):
            res.extend(self.apply_replacement(keyword, comb))
        return res

    def generate_additions(self, keyword):
        res = []
        for sym in '0123456789abcdefghijklmnopqrstuvwxyz':
            res.append(keyword + sym)
        return res

    def generate_deletions(self, keyword):
        res = []
        for i in range(0, len(keyword)):
            res.append(keyword[:i] + keyword[i + 1:])
        return res

    def generate_subdomains(self, keyword):
        res = []
        for i in range(0, len(keyword) - 1):
            if (keyword[i] not in '.~-_')\
            and (keyword[i + 1] not in '.~-_'):
                res.append(keyword[:i + 1] + '.' + keyword[i + 1:])
        return res

    def dns_lookup(self, url):
        try:
            res = resolver.resolve(url, 'A')
            if len(res) > 0:
                self.found_ips[url] = res
        except:
            pass

    def lookup_domains(self):
        domains = list(filter(''.__ne__, self.domains_file.read().split('\n')))
        for line in self.keywords_file:
            keyword = line.strip().lower()
            words = [keyword]
            words += self.generate_replacements(keyword)
            words += self.generate_additions(keyword)
            words += self.generate_deletions(keyword)
            words += self.generate_subdomains(keyword)
            urls = [word + '.' + domain for domain in domains for word in words]
            pool = ThreadPool(processes=cpu_count() * 10)
            pool.map(self.dns_lookup, urls)
            pool.close()
            pool.join()
        return self.found_ips


if __name__ == '__main__':

    with open('keywords', 'r') as keywords_file,\
        open('domains', 'r') as domains_file:
        ds = DomainSearcher(keywords_file, domains_file)
        found_ips = ds.lookup_domains()
        for url, ips in found_ips.items():
            for ip in ips:
                print(f'{url} {ip}')