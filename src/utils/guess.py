import asyncio
import aiohttp
import logging

from src.app_types.common import FormatInfo, Deltas

log = logging.getLogger(__name__)


class Default_Class:
    def __init__(self, format_info:FormatInfo, session: aiohttp.ClientSession|None, distance:int=10000):
        self.format_info = format_info
        self.session = session
        self.distance = distance # 當前值與最小檢查值範圍
        
        self.old_value:int | None = None #階段值，上一輪的值或是最小值
        self.new_value:int #當前值
        self.record_values:set = set() # 儲存已經檢查過的檔案段

        # 初始化步進值與猜測值
        self.step_init()
        self.guess_init()

    def step_init(self, split_times:int=10):
        """初始化步進值，必須為正整數"""
        self.split_times = split_times
        
    def guess_init(self, async_limit:int = 300):
        """初始化常見的檔案段差值"""
        # 自動對比常見的檔案段差值
        self.common_deltas = []
        for delta in Deltas:
            if self.format_info.space in delta.value:
                self.common_deltas = delta.value
                log.debug(f"使用常見的檔案段差值：{self.common_deltas}")
                break
        if not self.common_deltas:
            self.common_deltas = [self.format_info.space]
        self.async_limit = min(async_limit, self.format_info.space)  # 限制異步檢查的數量不超過空間大小

    async def check_status(self, value:int) -> int | None:
        """檢查網址是否有效"""
        url = self.format_info.url.format(num=str(value).zfill(self.format_info.fill))
        try:
            if not self.session:
                log.warning("未提供 aiohttp.ClientSession，無法檢查網址有效性")
                return None
            async with self.session.get(url) as response:
                if response.status == 200:
                    log.debug(f"檢查網址有效：{url}")
                    return value
                log.debug(f"檢查網址無效：{url} - {response.status}")
                return None
        except aiohttp.ClientError as e:
            log.warning(f"檢查網址無效：{url} - {str(e)}")
            return None
        except Exception as e:
            log.warning(f"檢查網址無效：{url} - {str(e)}")
            return None

class StepFinder(Default_Class):
    async def step_round_test(self, value:int, space:int=10000) -> int | None:
        """
        將當前值到距離的距離，切成split_times個節點，檢查全部節點取得最小值
        :param value: 當前值
        :param space: 距離，默認為10000
        :return: 最小值或None
        """
        tasks = [asyncio.create_task(self.check_status(num)) for num in range(max(0, value - space), value, space // self.split_times)]
        min_value = None
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    min_value = result if min_value is None else min(min_value, result)
            except Exception as e:
                log.warning(f"檢查網址失敗：{str(e)}")
        return min_value

    async def step_search(self, value:int):
        """
        每次將當前值到self.distance的距離，切成self.split_times個節點，檢查全部節點取得最小值
        取得最小值後，縮減範圍至最小值到下一個節點，並重複切片檢查，直到最小值為0或是檢查範圍為1
        """
        now_distance = self.distance # 當前距離
        while True:
            min_value = await self.step_round_test(value, now_distance)
            if min_value is not None:
                value = min(min_value, value)  # 更新當前值為最小值
            now_distance //= self.split_times # 每次將距離縮短為最小值與下一個節點的距離
            log.info(f"此輪測試間距：{now_distance}，當前最小值：{value}")
            if now_distance == 1: # 當前距離為1，則表示已經到達最小值
                break
        if min_value is not None:
            if min_value <= self.new_value - self.distance:
                value = await self.step_search(min_value)
        return value

    async def step_main(self):
        """
        若是沒有最小值，則從當前值開始逐步減少檢查範圍，直到找到最小的有效值
        若是有最小值，則直接產生階段值與當前值的序號列表
        """
        if self.old_value is None:
            # 如果沒有最小值，則搜尋最小值
            log.info("開始步進搜尋最小有效值")
            start_number = await self.step_search(self.new_value)
            self.old_value = start_number
        else:
            # 如果有最小值，則直接產生階段值與當前值的序號列表
            start_number = self.old_value + 1  # 確保步進值至少為1
        if not start_number:
            raise Exception("未能找到有效的步進值或當前值")
        if start_number <= self.new_value:
            log.info(f"步進搜尋完成，添加下載檔案範圍：{start_number} ~ {self.new_value}")
            return list(range(start_number, self.new_value + 1))

class GuessFinder(Default_Class):
    async def guess_create_tasks(self, round:list):
        tasks = [asyncio.create_task(self.check_status(num)) for num in round]
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:
                    # 取消其他尚未完成的任務
                    log.info(f"找到有效值：{result}")
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    return result
            except Exception as e:
                # 如果有例外也忽略，繼續等其他任務
                pass
        return None
    
    async def find_valid_segment(self, start_num:int) -> int | None:
        """從起始編號開始檢查有效的檔案段"""
        space = self.format_info.space * 3 // 2
        for n in range(max(0, start_num - space), start_num, self.async_limit):
            # 檢查從 start_num 到 start_num - self.distance 的檔案段
            limit_value = max(0, self.old_value) if self.old_value else -1
            # 生成檢查序號範圍
            round_list = [n + i for i in range(self.async_limit) if n + i < start_num and n + i > limit_value]
            log.info(f"檢查序號範圍：{round_list[0]} ~ {round_list[-1]}")
            result = await self.guess_create_tasks(round_list)
            if result:
                return result
        return None

    # 回溯檢查序號
    async def guess_search(self) -> list:
        """從起始編號開始尋找有效的檔案段"""
        valid_nums = []
        current_num = self.new_value
        found = None
        while True:
            # 遍歷常見的delta值
            classic_round = [current_num - delta for delta in self.common_deltas if current_num - delta > 0]
            found = await self.guess_create_tasks(classic_round)
            if not found:
                # 如果沒有找到有效檔案，使用異步檢查
                found = await self.find_valid_segment(current_num)
                if found and (current_num - found) not in self.common_deltas:
                    self.common_deltas.append(current_num - found)
                else:
                    log.warning(f"未找到有效檔案段，當前值：{current_num}")
                    break  # 沒有任何成功就停止
            valid_nums.append(found)
            current_num = found
            found = None  # 重置找到的值
        return sorted(valid_nums)

class Finder(StepFinder, GuessFinder):
    async def main(self, new_value: int) -> list:
        """使用步進法尋找最小有效值"""
        self.new_value = new_value
        valid_segments = []
        self.guess_type = None

        if self.format_info.space == 1:
            log.info("序號連貫，使用步進法尋找有效檔案段")
            valid_segments = await self.step_main()
        elif self.format_info.space > 1:
            log.info("序號不連貫，使用猜測法尋找有效檔案段")
            valid_segments = await self.guess_search()
        else:
            raise ValueError(f"未知的猜測類型：{self.guess_type}")
        if valid_segments:
            self.old_value = self.new_value
            self.record_values.update(valid_segments)
            return valid_segments
        else:
            log.warning("未找到任何有效的檔案段")
            return []