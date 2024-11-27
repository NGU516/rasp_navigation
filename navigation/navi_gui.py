# navi_gui.py

import customtkinter as ctk
import tkinter as tk
import datetime
import subprocess
from tkintermapview import TkinterMapView
from geopy.distance import geodesic


class NaviGUI(ctk.CTk):
    def __init__(self, data_queue, gps_receiver, communication,exit_flag):
        super().__init__()
        self.data_queue = data_queue
        self.gps_receiver = gps_receiver
        self.communication = communication
        self.exit_flag = exit_flag
        self.running = True

        # marker setting
        self.setting_destination = False
        self.destination_marker = None
        self.current_marker = None

        # Route path
        self.previous_coords = None    
        self.destination_coords = None

        # send server data
        self.update_cnt = 0
        self.mac_address = self.get_mac_address()  # MAC 주소 추출
        self.email = "cdm1111"
        self.fare = 0

        # GUI init
        self.init_gui()

    def init_gui(self):
        self.title("GPS Tracker")
        
        # set fullscreen(800*480)
        self.attributes('-fullscreen', True)
        # Esc key bind to exit fullscreen
        self.bind('<Escape>', self.exit_fullscreen)

        # Grid configuration
        self.grid_columnconfigure(0, weight=3)  # Map
        self.grid_rowconfigure(0, weight=1)     # Map
        self.grid_columnconfigure(1, weight=1)  # Sidebar

        # background color
        self.configure(fg_color="lightblue", bg_color="white")

        # Sidebar Frame
        # grid : row, column, padx, pady, sticky
        # sticky="nswe" : north, south, west, east
        # padx, pady : padding x, y
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="lightblue")
        self.sidebar_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nswe") 

        # destination setting label, button
        self.label_info = ctk.CTkLabel(self.sidebar_frame, text="목적지를 설정해주세요.", font=("Arial", 16))
        self.label_info.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        destination_button = ctk.CTkButton(self.sidebar_frame, text="목적지 설정", command=self.start_destination_setting, font=("Arial", 18), width=200, height=40)
        destination_button.grid(row=1, column=0, padx=10, pady=10, sticky="nesw")
        show_destination_button = ctk.CTkButton(self.sidebar_frame, text="목적지 표시", command=self.show_destination, font=("Arial", 18), width=200, height=40)
        show_destination_button.grid(row=2, column=0, padx=10, pady=10, sticky="nesw")

        # distance, fare label
        self.label_distance = ctk.CTkLabel(self.sidebar_frame, text="거리: -- km", font=("Arial", 14))
        self.label_distance.grid(row=3, column=0, padx=10, pady=10, sticky="nesw")
        self.label_fare = ctk.CTkLabel(self.sidebar_frame, text="예상 요금: -- 원", font=("Arial", 14))
        self.label_fare.grid(row=4, column=0, padx=10, pady=10, sticky="nesw")

        # exit button
        close_button = ctk.CTkButton(self.sidebar_frame, text="종료", command=self.close_window, font=("Arial", 18), width=200, height=40)
        close_button.grid(row=8, column=0, padx=10, pady=10, sticky="nesw")

        # map widget
        self.map_widget = TkinterMapView(self, width=600, height=480)
        self.map_widget.grid(row=0, column=0, padx=0, pady=0, sticky="nswe")
        self.map_widget.add_left_click_map_command(self.map_click_event)

        # close window event
        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def exit_fullscreen(self, event=None):
        self.attributes('-fullscreen', False)
        self.state('normal')

    # 라즈베리 파이 환경에서 MAC 주소를 추출
    def get_mac_address(self):
        try:
            result = subprocess.check_output(['cat', '/sys/class/net/eth0/address'])
            print(result.strip().decode('utf-8')) # debug
            return result.strip().decode('utf-8')
        except Exception as e:
            print(f"MAC 주소 추출 오류: {e}")
            return "UNKNOWN"  # 오류 시 기본값 - UNKNOWN 문자열

    def start_destination_setting(self):
        self.setting_destination = True
        self.label_info.configure(text="지도를 클릭하여 목적지를 설정하세요.")

    def map_click_event(self, coordinate_mouse_pos):
        if self.destination_marker:
            self.destination_marker.delete()

        if self.setting_destination:
            lat, lon = coordinate_mouse_pos  # Mouse click position -> tuple(lat, lon)
            self.destination_coords = (lat, lon)
            self.destination_marker = self.map_widget.set_marker(lat, lon, text="목적지")
            self.setting_destination = False
            self.label_info.configure(text="목적지가 설정되었습니다.")  # label update

            self.calculate_route()

    def calculate_route(self):
        """
        Communcation Thread -> request_route() call(task queue)
        """
        if self.previous_coords and self.destination_coords:
            # 통신 쓰레드에 경로 요청 작업 추가
            task = {
                "type": "route",
                "start_coords": self.previous_coords,
                "end_coords": self.destination_coords,
                "callback": self.update_route_on_map  # 경로 업데이트 콜백, return response.json()
            }
            self.communication.add_task(task)

    def update_route_on_map(self, path):
        """
        경로 좌표를 받아서 지도 위에 그리는 함수
        """
        try:
            # 경로 데이터에서 좌표 추출
            route = path.get('route', {}).get('traoptimal', [])
            if not route:
                print("경로 데이터를 찾을 수 없습니다.")
                return

            path_coords = []
            for section in route[0]['path']:
                try:
                    lon, lat = section  # 경도, 위도를 바꿔줍니다.
                    path_coords.append((lat, lon))  # (위도, 경도)로 저장
                except Exception as e:
                    print(f"좌표 처리 오류: {e}")

            # 중복 좌표 제거
            path_coords = list(dict.fromkeys(path_coords))

            if len(path_coords) < 2:
                print("경로가 너무 짧아 그릴 수 없습니다.")
                return

            print("path_coords 데이터 확인:", path_coords)

            # 기존 경로 삭제
            if hasattr(self, 'path_line') and self.path_line:
                print("기존 경로 삭제")
                self.path_line.delete()

            # 경로 그리기
            print("경로 그리기 시작")
            for i in range(len(path_coords) - 1):
                # 두 좌표를 하나의 튜플로 묶어서 경로 그리기
                self.path_line = self.map_widget.set_path([path_coords[i], path_coords[i + 1]])
                print(f"경로 {i}와 {i + 1} 연결됨: {path_coords[i]} -> {path_coords[i + 1]}")

            print("경로 그리기 완료")
        except Exception as e:
            print(f"경로 업데이트 오류: {e}")

    def show_destination(self):
        # Refresh destination marker
        if self.destination_coords:
            lat, lon = self.destination_coords
            # Delete previous destination marker
            if self.destination_marker:
                self.destination_marker.delete()
            self.destination_marker = self.map_widget.set_marker(lat, lon, text="목적지")
            # position update
            self.map_widget.set_position(lat, lon)

    def send_data(self, lat=0, lon=0):
        # current_time = datetime.now().isoformat()   # 현시각을 ISO 형식의 문자열로 변환
        
        data = {
            "type" : "send",
            "email": self.email,        # 기본 이메일
            "mac": self.mac_address,    # get_mac_address에서 추출
            "latitude": lat,       # previous_coords[0]
            "longitude": lon,     # previous_coords[1]
            "fare": self.fare,          # calculate_route에서 계산
            # "timestamp": current_time,  # send_data 내부에서 계산
        }
            
        self.communication.add_task(data)
        # print(data)

    def update_location(self):
        # Main Gps data update function
        ## GPS data queue check
        if not self.data_queue.empty():
            lat, lon = self.data_queue.get()

            if lat is not None and lon is not None and self.setting_destination == False:
                if self.update_cnt % 5 == 0:
                    self.send_data(lat, lon)
                if self.current_marker:
                    self.current_marker.delete()
                # position update, Marker update
                self.map_widget.set_position(lat, lon)
                self.current_marker = self.map_widget.set_marker(lat, lon, text="현재 위치")

                # route calculation
                self.previous_coords = (lat, lon)

        if self.running:
            # update location every 500ms
            self.after(500, self.update_location)
            self.update_cnt += 1


    def close_window(self):
        self.running = False
        self.gps_receiver.stop()  # GPS receiver Thread stop
        self.quit()  # customtkinter exit
        self.destroy()  # customtkinter destroy
        self.exit_flag[0] = False  # exit flag update
