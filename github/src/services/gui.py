import tkinter as tk
from tkinter import ttk, messagebox

def show_config_interface(params):
    def execute_and_close():
        # 蒐集所有設定值
        for param, widget in widgets.items():
            if isinstance(widget, tk.Entry):
                config[param] = widget.get()
            elif isinstance(widget, tk.BooleanVar):
                config[param] = True if widget.get() else False
        
        root.destroy()  # 關閉視窗
        return config
    
    def on_execute():
        nonlocal config
        config = execute_and_close()

    config = {}
    # 建立主視窗
    root = tk.Tk()
    root.title("設定介面")
    root.geometry("1000x800")
    root.resizable(True, True)
    
    # 滾動區域
    canvas = tk.Canvas(root)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)

    scroll_frame = ttk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * int(e.delta / 120), "units"))
    
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # 儲存 widget 與參數名稱的對應
    widgets = {}
    
    # 設定左右框架的比例 2:1
    scroll_frame.rowconfigure(0, weight=1)
    scroll_frame.columnconfigure(0, weight=4)  # 左框架
    scroll_frame.columnconfigure(1, weight=1)  # 右框架
    
    # 左右框架
    left_frame = ttk.Frame(scroll_frame)
    right_frame = ttk.Frame(scroll_frame)
    
    left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    # 生成介面
    for param in params:
        if param["type"] == "bool":
            # 布林值選項在右側
            var = tk.BooleanVar(value=param["default"])
            tk.Label(right_frame, text=param["help"], wraplength=200, font=("msyh", 11),justify="left").pack(anchor="w", padx=10, pady=5)
            check = tk.Checkbutton(right_frame, variable=var, text="啟用")
            check.pack(anchor="w", padx=10, pady=5)
            widgets[param["environment"]] = var
        else:
            # 其他類型選項在左側
            tk.Label(left_frame, text=param["help"], wraplength=600, font=("msyh", 11), justify="left").pack(anchor="w", padx=10, pady=5)
            entry = tk.Entry(left_frame)
            entry.insert(0, str(param["default"]))
            entry.pack(fill="x", padx=10, pady=5)
            widgets[param["environment"]] = entry
    
    # 執行按鈕
    tk.Button(root, text="執行", command=on_execute, bg="green", fg="white", font=("msyh", 12)).pack(pady=20)
    
    # 主迴圈
    root.mainloop()
    for param in params:
        if param["type"] == "int":
            config[param["environment"]] = int(config[param["environment"]])
        if config[param["environment"]] == "None":
            config[param["environment"]] = None
    config["url"] = (config.get("url") or "https://www.google.com")
    if "skip_ticket_url" in config:
        config["skip_ticket_url"] = config["skip_ticket_url"].split(",")
    return config

# 询问用户是否下载给定的链接
def ask_download(link):
    """
    弹出窗口，询问用户是否下载给定的链接。
    
    :param link: 要下载的链接
    :return: 如果用户点击"是"，返回True；否则返回False。
    """
    # 创建根窗口（不显示）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    # 弹出消息框
    response = messagebox.askyesno("M3U8 發見！", f"是否要下載此連結：\n{link}")
    # 返回布尔值，True表示用户点击"是"，False表示用户点击"否"
    return response

# 询问用户是否下载给定的链接
def ask_skip(link):
    """
    弹出窗口，询问用户是否下载给定的链接。
    
    :param link: 要下载的链接
    :return: 如果用户点击"是"，返回True；否则返回False。
    """
    # 创建根窗口（不显示）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    # 弹出消息框
    response = messagebox.askyesno("直播間尚未開始", f"是否要跳過此直播間：\n{link}")
    # 返回布尔值，True表示用户点击"是"，False表示用户点击"否"
    return response


# 測試呼叫
if __name__ == "__main__":
    pass
