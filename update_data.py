import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://xyzrank.com/api"
# 单次请求条数上限，避免一次性拉取过大响应
PAGE_LIMIT = 100

# (API 路径片段, 输出文件名, data 下的列表键名)
ENDPOINT_CONFIG = [
    ("podcasts", "full.json", "podcasts"),
    ("episodes", "hot_episodes.json", "episodes"),
    ("new-episodes", "hot_episodes_new.json", "episodes"),
    ("new-podcasts", "new_podcasts.json", "podcasts"),
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://xyzrank.com/",
}


class XYZRankScraper:
    def __init__(self):
        self.log = []

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log.append(log_entry)

    def _get_json(self, path: str, offset: int, limit: int) -> dict:
        qs = urlencode({"offset": offset, "limit": limit})
        url = f"{API_BASE}/{path}?{qs}"
        req = Request(url, headers=DEFAULT_HEADERS, method="GET")
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} {url}") from e
        except URLError as e:
            raise RuntimeError(f"网络错误 {url}: {e.reason}") from e
        return json.loads(raw)

    def fetch_paged_items(self, path: str) -> list:
        """使用 offset/limit 分页拉取某一榜单的全部 items。"""
        items_all = []
        offset = 0
        total = None

        while True:
            self.log_message(f"GET {API_BASE}/{path} offset={offset} limit={PAGE_LIMIT}")
            body = self._get_json(path, offset, PAGE_LIMIT)

            chunk = body.get("items") or []
            if total is None:
                total = body.get("total")
                if total is not None:
                    self.log_message(f"{path} total={total}")

            items_all.extend(chunk)

            if not chunk:
                break
            offset += len(chunk)
            if total is not None and offset >= total:
                break
            if len(chunk) < PAGE_LIMIT:
                break

        self.log_message(f"{path} 共拉取 {len(items_all)} 条")
        return items_all

    def save_wrapped(self, items: list, list_key: str, filename: str):
        payload = {"data": {list_key: items}}
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.log_message(f"已保存: {filename}")

    def run(self):
        self.log_message(
            "开始从 xyzrank.com API 拉取数据 "
            f"(每页 {PAGE_LIMIT} 条)"
        )
        success = True
        for path, filename, list_key in ENDPOINT_CONFIG:
            try:
                items = self.fetch_paged_items(path)
                self.save_wrapped(items, list_key, filename)
            except Exception as e:
                self.log_message(f"失败 {path} -> {filename}: {e}")
                success = False
        return success


if __name__ == "__main__":
    scraper = XYZRankScraper()
    ok = scraper.run()
    if not ok:
        print("更新过程中出现错误，请查看上方日志。")
    else:
        print("全部 JSON 已更新完成。")
