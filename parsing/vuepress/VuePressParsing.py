from parsing.BaseParsing import BaseWebParser
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
import time
from typing import Dict, Set, Optional


class VuePressParser(BaseWebParser):
    """VuePress网站解析器"""

    def __init__(self, base_url: str, output_dir: str = "output_markdown"):
        super().__init__(output_dir=output_dir)
        self.base_url = base_url.rstrip('/')

    def is_valid_url(self, url: str) -> bool:
        """检查URL是否属于目标VuePress网站"""
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return url_domain == base_domain

    def fetch_content(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            response.encoding = response.apparent_encoding
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"获取页面失败 {url}: {str(e)}")
            return None

    def extract_links(self, content: str, base_url: str) -> Set[str]:
        """从VuePress页面提取链接"""
        soup = BeautifulSoup(content, 'html.parser')
        links = set()

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('#'):
                continue

            full_url = urljoin(base_url, href)
            normalized_url = self.normalize_identifier(full_url)

            if self.is_valid_url(normalized_url):
                links.add(normalized_url)

        return links

    def get_identifiers(self) -> Set[str]:
        """获取所有需要处理的URL"""
        all_urls = set()
        urls_to_process = {self.base_url}

        while urls_to_process:
            url = urls_to_process.pop()
            normalized_url = self.normalize_identifier(url)

            if normalized_url in all_urls:
                continue

            print(f"发现URL: {url}")
            content = self.fetch_content(url)

            if content:
                all_urls.add(normalized_url)
                new_links = self.extract_links(content, url)
                urls_to_process.update(new_links - all_urls)
                # time.sleep(1)  # 避免请求过快

        return all_urls

    def process_content(self, content: str, metadata: Dict) -> bool:
        """处理VuePress页面内容"""
        soup = BeautifulSoup(content, 'html.parser')

        # 获取页面标题
        title = soup.find('title')
        title_text = title.text.strip() if title else metadata['identifier']

        # 查找主要内容区域
        content_div = (
            soup.find('div', class_='theme-default-content') or  # VuePress v2
            soup.find('div', class_='content') or                # VuePress v1
            soup.find('main', class_='page') or                 # 备选
            soup.find('article')                                # 备选
        )

        if not content_div:
            return False

        # 移除不需要的元素
        for element in content_div.select('script, .page-nav, .page-edit'):
            element.decompose()

        # 更新元数据
        metadata.update({
            'title': title_text,
            'url': metadata['identifier'],
            'site_type': 'vuepress'
        })

        # 使用内容分割器处理内容
        return self.content_splitter.process_content(content_div, metadata)


def create_vuepress_parser(base_url: str, output_dir: str = "output_markdown") -> VuePressParser:
    """创建VuePress解析器的工厂函数"""
    return VuePressParser(base_url, output_dir)


if __name__ == '__main__':
    parser = create_vuepress_parser("https://mhb.icu")
    success = parser.collect_and_save_contents()
    print(f"处理{'成功' if success else '失败'}")
