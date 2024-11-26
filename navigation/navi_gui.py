import customtkinter as ctk
import tkinter as tk
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

            ######################
            # route calculation -> API use(Google Map API, Naver Map API, etc..)
            self.calculate_route()
    """
    def calculate_route(self):
        ######################
        # route calculation -> API use(Google Map API, Naver Map API, etc..)
        if self.previous_coords and self.destination_coords:
            # current location -> destination location distance
            distance = geodesic(self.previous_coords, self.destination_coords).km
            print(f"현재 위치에서 목적지까지의 거리: {distance:.2f}km")

            # distance label update
            self.label_distance.configure(text=f"목적지까지의 거리: {distance:.2f} km")

            # fare calculation
            fare = int(distance * 1000)  # 1km당 1000원 요금
            print(f"예상 요금: {fare}원")
            self.label_fare.configure(text=f"예상 요금: {fare} 원")

            ######################
            if hasattr(self, 'path_line') and self.path_line:
                self.path_line.delete() 
            self.path_line = self.map_widget.set_path([self.previous_coords, self.destination_coords])
    """
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
        path: response.json()
        json안에서 path 데이터 parsing -> 경로 그리기
        """
        try:
            # 경로 좌표 추출
            route = path.get('route', {}).get('traoptimal', [])
            if not route:
                print("경로 데이터를 찾을 수 없습니다.")
                return

            # 경로를 그릴 좌표 리스트 생성
            path_coords = []
            for section in route[0]['path']:
                lat, lon = section  # 경로 좌표 (위도, 경도)
                path_coords.append((lat, lon))

            # 기존 경로 삭제 (지도에 경로가 이미 있을 경우)
            if hasattr(self, 'path_line') and self.path_line:
                self.path_line.delete()

            # 지도에 경로 그리기
            self.path_line = self.map_widget.set_path(path_coords)

            # 거리 계산 (단위: 미터 -> 킬로미터)
            total_distance = route[0]['summary']['distance'] / 1000  # 거리 (m -> km)
            print(f"목적지까지의 거리: {total_distance:.2f}km")
            self.label_distance.configure(text=f"목적지까지의 거리: {total_distance:.2f} km")

            # 요금 계산 (1km당 1000원 요금)
            fare = int(total_distance * 1000)
            print(f"예상 요금: {fare}원")
            self.label_fare.configure(text=f"예상 요금: {fare} 원")
    
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

    def update_location(self):
        # Main Gps data update function
        ## GPS data queue check
        if not self.data_queue.empty():
            lat, lon = self.data_queue.get()
            if lat is not None and lon is not None and self.setting_destination == False:
                if self.current_marker:
                    self.current_marker.delete()
                # position update, Marker update
                self.map_widget.set_position(lat, lon)
                self.current_marker = self.map_widget.set_marker(lat, lon, text="현재 위치")

                # route calculation
                self.previous_coords = (lat, lon)

                if self.destination_coords:
                    if hasattr(self, 'path_line') and self.path_line:
                        self.path_line.delete()
                    self.path_line = self.map_widget.set_path([self.previous_coords, self.destination_coords])

        if self.running:
            # update location every 500ms
            self.after(500, self.update_location)


    def close_window(self):
        self.running = False
        self.gps_receiver.stop()  # GPS receiver Thread stop
        self.quit()  # customtkinter exit
        self.destroy()  # customtkinter destroy
        self.exit_flag[0] = False  # exit flag update
