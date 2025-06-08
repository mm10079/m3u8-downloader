import logging

log = logging.getLogger(__name__)

# 查找 ts 值有效範圍
def find_files_range(check, start=0, end=1000000):
    """
    :param check: 檢查函數，返回是否在範圍內
    :param start: 起始值
    :param end: 結束值
    """
    if start < 0 or end < 0:
        raise ValueError("起始值和結束值必須大於等於 0")

    log.info(f"開始媒體檔案有效範圍測試，起始值：{start}, 結束值：{end}")

    def find_boundary(start_tmp, end_tmp, find_max):
        """ 使用二分搜尋找到邊界 """
        result = None
        while start_tmp <= end_tmp:
            mid = (start_tmp + end_tmp) // 2
            if check(mid):
                result = mid
                if find_max:
                    start_tmp = mid + 1  # 向上搜尋
                else:
                    end_tmp = mid - 1  # 向下搜尋
            else:
                if find_max:
                    end_tmp = mid - 1  # 過大，縮小範圍
                else:
                    start_tmp = mid + 1  # 過小，擴大範圍
        return result

    def find_step(start_tmp, end_tmp):
        """
        透過等距測試尋找有效範圍內的數值，逐步減少步進，最終以步長 1 確保範圍邊界
        """
        step_size = (end_tmp - start_tmp) // 4 or 1  # 初始步長，至少為 1
        already_checked = set()

        while step_size >= 1:
            for value in range(start_tmp, end_tmp + 1, step_size):
                if value in already_checked:
                    continue
                if check(value):
                    log.debug(f"找到符合條件的值：{value}（步進大小 {step_size}）")
                    return value
                already_checked.add(value)

            # 每輪測試完後，減小步長，提高精度
            step_size //= 2

        return None  # 找不到符合條件的值

    # 確認開始與結束是否有效
    check_start = check(start)
    check_end = check(end)

    if check_start and check_end:
        log.debug("起始值和結束值都在範圍內")
        return {"start": start, "end": end}
    elif check_start:
        log.debug("起始值有效，結束值無效，尋找最大範圍")
        return {"start": start, "end": find_boundary(start, end, True)}
    elif check_end:
        log.debug("起始值無效，結束值有效，尋找最小範圍")
        return {"start": find_boundary(start, end, False), "end": end}
    else:
        log.debug("起始值與結束值都無效，使用等距搜尋找可能範圍")
        tmp = find_step(start, end)
        if tmp:
            return {
                "start": find_boundary(start, tmp, False),
                "end": find_boundary(tmp, end, True),
            }
        else:
            log.error("未找到符合條件的值")
            raise ValueError("無法找到有效的值")