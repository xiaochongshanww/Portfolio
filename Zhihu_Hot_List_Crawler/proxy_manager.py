import requests


class ProxyManager:
    def __init__(self, proxy_url):
        self.proxy_url = proxy_url
        self.proxies = []

    def fetch_proxies(self):
        try:
            response = requests.get(self.proxy_url)
            response.raise_for_status()
            self.proxies = response.text.splitlines()
        except requests.RequestException as e:
            print(f"Error fetching proxies: {e}")
            self.proxies = []

    def get_random_proxy(self):
        if not self.proxies:
            self.fetch_proxies()
        if self.proxies:
            return {'http': self.proxies[0], 'https': self.proxies[0]}
        return None