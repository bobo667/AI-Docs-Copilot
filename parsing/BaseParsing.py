from abc import ABC, abstractmethod
from typing import Dict, Set, Optional
from bs4 import BeautifulSoup
import re
import os
from markdownify import markdownify as md
from urllib.parse import urlparse

class BaseContentSplitter:
    """内容分割器基类"""
    
    def __init__(self, output_dir: str = "output_markdown"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def clean_filename(self, url: str) -> str:
        """生成合适的文件名"""
        # 移除基础URL和查询参数
        path = urlparse(url).path.strip('/')
        if not path:
            path = 'index'
        
        # 替换非法字符
        filename = re.sub(r'[\\/:*?"<>|]', '_', path)
        return f"{filename}.md"

    def process_content(self, content_div: BeautifulSoup, metadata: Dict) -> bool:
        """将HTML内容转换为Markdown格式并保存到文件"""
        try:
            # 移除所有内部链接的href属性
            for a in content_div.find_all('a', href=True):
                if a.get('href', '').startswith('#'):
                    del a['href']
            
            # 保留代码块的原始格式
            for pre in content_div.find_all('pre'):
                # 为代码块添加额外的换行符
                if pre.string:
                    pre.string = '\n' + pre.string.strip() + '\n'
            
            # 将HTML转换为Markdown
            markdown_text = md(str(content_div))
            
            # 清理markdown内容
            # 1. 移除转义字符
            markdown_text = markdown_text.replace('\\-', '-')
            markdown_text = markdown_text.replace('\\.', '.')
            markdown_text = re.sub(r'\\([^\\])', r'\1', markdown_text)
            
            # 2. 修复标题格式
            markdown_text = re.sub(r'\[\#\]\((.*?)\)\s*([#]+.*)', r'\2', markdown_text)
            
            # 3. 清理多余的空行，但保留代码块中的换行
            markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
            
            # 4. 修复代码块格式
            markdown_text = re.sub(r'```\s*(\w+)?\s*\n\s*', r'```\1\n', markdown_text)
            markdown_text = re.sub(r'\n\s*```', r'\n```', markdown_text)

            # 添加来源URL
            source_url = metadata.get('url', '')
            if source_url:
                markdown_text = f"Source: {source_url}\n\n{markdown_text}"

            # 生成文件名并保存
            filename = self.clean_filename(metadata.get('url', ''))
            filepath = os.path.join(self.output_dir, filename)
            
            # 使用UTF-8编码写入文件
            with open(filepath, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(markdown_text)
            
            print(f"已保存: {filepath}")
            return True
            
        except Exception as e:
            print(f"处理内容失败: {str(e)}")
            return False

class BaseParser(ABC):
    """文档解析器基类"""

    def __init__(self, output_dir: str = "output_markdown"):
        self.processed_items = set()  # 用于存储已处理的项目标识符
        self.output_dir = output_dir

    @abstractmethod
    def fetch_content(self, identifier: str) -> Optional[str]:
        """获取内容"""
        pass

    @abstractmethod
    def process_content(self, content: str, metadata: Dict) -> bool:
        """处理内容并保存为Markdown文件"""
        pass

    @abstractmethod
    def get_identifiers(self) -> Set[str]:
        """获取所有需要处理的内容标识符"""
        pass

    def normalize_identifier(self, identifier: str) -> str:
        """标准化标识符"""
        return identifier

    def collect_and_save_contents(self) -> bool:
        """收集所有内容并保存为Markdown文件"""
        success = True
        identifiers = self.get_identifiers()

        for identifier in identifiers:
            normalized_id = self.normalize_identifier(identifier)

            if normalized_id in self.processed_items:
                continue

            content = self.fetch_content(identifier)
            if content:
                metadata = {'identifier': normalized_id}
                if not self.process_content(content, metadata):
                    success = False
                self.processed_items.add(normalized_id)

        return success

class BaseWebParser(BaseParser):
    """网页解析器基类"""

    def __init__(self, headers: Dict = None, output_dir: str = "output_markdown"):
        super().__init__(output_dir)
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.content_splitter = BaseContentSplitter(output_dir)

    def normalize_identifier(self, url: str) -> str:
        """标准化URL"""
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        return normalized

    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        pass

    @abstractmethod
    def extract_links(self, content: str, base_url: str) -> Set[str]:
        """从内容中提取链接"""
        pass
