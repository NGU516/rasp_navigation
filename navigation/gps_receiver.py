# gps_receiver.py

import serial
import threading
import queue

# GPS Receiver Thread
class GPSReceiver(threading.Thread):
    # Air530 Sensor with Raspberry Pi, Serial Port: /dev/ttyS0, Baud Rate: 9600
    # data_queue: GPS sensor data queue (lat, lon)
    def __init__(self, port="/dev/ttyS0", baud_rate=9600, max_queue_size=5):
        super().__init__()
        self.gps = serial.Serial(port, baud_rate)
        self.data_queue = queue.Queue(max_queue_size)
        self.running = True

    def run(self):
        while self.running:
            try:
                line = self.gps.readline().decode('ascii', errors='ignore')
                # sensor data slicing
                if "$GNGGA" in line:
                    parts = line.split(",")
                    if len(parts) >= 6 and parts[2] and parts[4]:
                        lat = float(parts[2][:2]) + float(parts[2][2:]) / 60
                        lon = float(parts[4][:3]) + float(parts[4][3:]) / 60
                        if parts[3] == 'S': lat = -lat
                        if parts[5] == 'W': lon = -lon
                        # data_queue put (lat, lon)
                        self.data_queue.put((lat, lon))
                        print(f"GPS Data: {lat}, {lon}")
                        # print(self.data_queue.qsize())
                    else:
                        self.data_queue.put((None, None))
                        print("GPS Data: None, None")
            except Exception as e:
                print(f"GPS Read Error: {e}")

    def stop(self):
        self.running = False
        self.join()
