# main.py

from communication import Communication
from gps_receiver import GPSReceiver
from navi_gui import NaviGUI

# Exit flag
exit_flag = [True]

if __name__ == "__main__":
    # GPS Receiver Thread
    gps_receiver = GPSReceiver()
    gps_receiver.start()

    # Communication Thread
    communication = Communication()
    communication.start()

    # GUI(Main) Thread
    gui = NaviGUI(gps_receiver.data_queue, gps_receiver, communication, exit_flag)
    gui.update_location()

    gui.mainloop()

    try:
        while exit_flag[0]:
            pass  
    except KeyboardInterrupt:
        gps_receiver.stop()
        print("프로그램 종료")
