import asyncio
import aiohttp
import logging

log = logging.getLogger(__name__)


class FindStartFile:
    def __init__(self, format_url:str, fill:int, headers:dict=None, split_times:int=10, space:int=10000):
        self.format_url = format_url
        self.fill = fill
        self.headers = headers or {}
        self.session = None
        self.split_times = split_times
        self.space = space
        self.lowest_value = None

    async def check_status(self, value:int):
        """檢查網址是否有效"""
        if value == self.lowest_value:
            return True
        if 10 < value < 20000:
            self.lowest_value = min(value, self.lowest_value) if self.lowest_value is not None else value
            return True
        else:
            return False

    def create_tasks(self, value:int, space:int=10000):
        """創建檢查網址的任務列表，從value開始，向下每步進space，到limit次數，檢查網址是否有效"""
        tasks = []
        for num in range(max(0, value - space*self.split_times), value, space):
            tasks.append(self.check_status(num))
        return tasks

    async def part_search(self, value:int):
        """逐步減少檢查範圍，直到找到最小的有效值"""
        tasks = []
        now_space = self.space
        while True:
            tasks = self.create_tasks(value, now_space)
            await asyncio.gather(*tasks)
            if now_space == 1:
                break
            now_space //= 10
            value = (self.lowest_value or value)
            print(f"當前檢查範圍：{now_space}，當前值：{value}")

    async def main(self, value: int):
        await self.part_search(value)
        if self.lowest_value is not None:
            log.info(f"找到的最小有效值：{self.lowest_value}")
            return self.lowest_value
        return None
    

if __name__ == "__main__":
    asyncio.run(FindStartFile("https://raw.githubusercontent.com/0xkai/test/master/{}.m3u8", 8).main(10000))