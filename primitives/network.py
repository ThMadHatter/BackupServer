import requests
from typing import Any, Dict
from primitives.base import Primitive

class HttpGet(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        url = self.options.get("url")
        headers = self.options.get("headers", {})
        timeout = self.options.get("timeout", 30)

        self.logger.info("Executing HTTP GET", url=url)
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        if self.options.get("extract_json", True):
            return response.json()
        return response.text

class HttpPost(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        url = self.options.get("url")
        headers = self.options.get("headers", {})
        json_data = self.options.get("json")
        data = self.options.get("data")
        timeout = self.options.get("timeout", 30)

        self.logger.info("Executing HTTP POST", url=url)
        response = requests.post(url, headers=headers, json=json_data, data=data, timeout=timeout)
        response.raise_for_status()

        if self.options.get("extract_json", True):
            return response.json()
        return response.text

class HttpDownload(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        url = self.options.get("url")
        headers = self.options.get("headers", {})
        dest_path = self.options.get("dest_path")
        timeout = self.options.get("timeout", 300)

        if not dest_path:
            raise ValueError("dest_path is required for HttpDownload")

        self.logger.info("Executing HTTP Download", url=url, dest=dest_path)
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return dest_path
