import cProfile
import pstats
import io
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import main

def profile_startup():
    # Patch main to exit after a few seconds
    app = QApplication.instance() or QApplication(sys.argv)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    window = main.VideoDownloaderApp()
    window.show()
    
    # Close after 5 seconds
    QTimer.singleShot(5000, lambda: QApplication.quit())
    
    app.exec()
    
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(50)
    
    with open("profile_results.txt", "w", encoding="utf-8") as f:
        f.write(s.getvalue())
    
    print("Profiling complete. Results saved to profile_results.txt")

if __name__ == "__main__":
    profile_startup()
