from ipaddress import IPv4Network
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
import socket
from requests import head

class PortScanner(object):

    open_ports = {}

    def __init__(self, ips_file, ports_file):
        self.ips_file = ips_file
        self.ports_file = ports_file
        ports = ports_file.read().split('\n')
        self.ports = list(map(int, filter(''.__ne__, ports)))
        temp_ips = ips_file.read().split('\n')
        temp_ips = map(IPv4Network, filter(''.__ne__, temp_ips))
        self.ips = []
        for ip_range in temp_ips:
            self.ips += map(str, ip_range)

    def check_ports(self, ip):
        for port in self.ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket.setdefaulttimeout(0.1) 
            result = sock.connect_ex((ip, port))
            if result == 0:
                self.open_ports[(ip, port)] = 1
                if port in (80, 443):
                    try:
                        response = head(f'http://{ip}:{port}')
                        if 'Server' in response.headers:
                            self.open_ports[(ip, port)] = response.headers['Server']
                    except:
                        pass

    def scan(self):
        pool = ThreadPool(processes=cpu_count() * 10)
        pool.map(self.check_ports, self.ips)
        pool.close()
        pool.join()
        return self.open_ports


if __name__ == '__main__':

    with open('ports', 'r') as ports_file,\
        open('ips', 'r') as ips_file:
        scanner = PortScanner(ips_file, ports_file)
        open_ports = scanner.scan()
        for open_port in open_ports:
            if open_ports[open_port] == 1:
                print(f'{open_port[0]} {open_port[1]} OPEN')
            else:
                print(f'{open_port[0]} {open_port[1]} OPEN Server: {open_ports[open_port]}')