import os
import time
import pyfiglet


# 清屏（可选）
os.system('cls' if os.name == 'nt' else 'clear')

# 标题大字
big_text = pyfiglet.figlet_format("VisoMaster-V5", font="slant")

# 构建展示块
banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
{big_text.rstrip()}
╠══════════════════════════════════════════════════════════════════════════════╣

    📦 项目名称：VisoMaster-V5                                               
    🧠 功能定位：图片换脸  视频换脸                         

    👑 当前版本：V5｜  构建环境：PyTorch 2.8 + CUDA 12.8 + TensorRT   
    📂 启动路径：{os.getcwd()}                                                  

╠══════════════════════════════════════════════════════════════════════════════╣
    🎬 油管：王知风    ｜  📺 B站：AI王知风                                    
    💬 AI工具QQ2群：773608333                                                
    🧾 官网：wangzhifeng.vip   ｜ 作者：王知风                                 
╚══════════════════════════════════════════════════════════════════════════════╝
"""

print()
print(banner)
print("\n" + "═" * 80 + "\n")
time.sleep(5)

from app.ui import main_ui
from PySide6 import QtWidgets 
import sys

try:
    import qdarktheme
except Exception:
    qdarktheme = None
from app.ui.core.proxy_style import ProxyStyle

if __name__=="__main__":

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(ProxyStyle())
    with open("app/ui/styles/dark_styles.qss", "r") as f:
        _style = f.read()
        if qdarktheme:
            _style = qdarktheme.load_stylesheet(custom_colors={"primary": "#4facc9"})+'\n'+_style
        app.setStyleSheet(_style)
    window = main_ui.MainWindow()
    window.show()
    app.exec()