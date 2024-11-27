# communication.py

import threading
import requests
import queue
from dotenv import load_dotenv
import os

# .env file load
load_dotenv()

# communication Thread(API, Server)
class Communication(threading.Thread):
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("API_KEY")  
        self.server_url = os.getenv("SERVER_URL")
        self.task_queue = queue.Queue()  # 통신 Task Queue
        self.running = True
    
    def run(self):
        while self.running:
            try:
                task = self.task_queue.get()
                if task:
                    if task['type'] == 'route':
                        # 경로 요청
                        path = self.request_route(task['start_coords'], task['end_coords'])
                        if path:
                            task['callback'](path)
                    elif task['type'] == 'send':
                        # 서버로 데이터 전송
                        response = self.send_to_server(task['data'])
                        if response:
                            task['callback'](response)
            except queue.Empty:
                continue

    # 경로 지정은 목적지를 정한 순간 한번만 호출, 현재 위치마다 호출 시 api 호출량 초과
    # 경로 요청을 받고 tkintermap에서 경로를 그림 -> 경로에 따라 현재 위치 갱신
    # json안에서 path 데이터만 파싱해서 경로 그리기
    def request_route(self, start_coords, end_coords):
        
        # 네이버 지도 API를 이용해 경로 데이터를 요청
        # param start_coords: 시작 좌표 (위도, 경도)
        # param end_coords: 목적지 좌표 (위도, 경도)
        # return: 경로 데이터
        
        try:
            url = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
            headers = {"X-NCP-APIGW-API-KEY-ID": self.api_key}
            params = {
                "start": f"{start_coords[1]},{start_coords[0]}",
                "goal": f"{end_coords[1]},{end_coords[0]}",
                "option": "traoptimal",
            }
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"경로 요청 오류: {e}")
            return None

    # 서버로 데이터 전송(현재 위치 정보), navi_gui.py에서 update_location()안에서 호출될 예정
    # update_location()에서 통신 함수를 호출하면 GUI 지연 발생 가능 -> 플래그를 세워놓고 통신 함수를 호출하도록 함
    def send_to_server(self, data):
        """
        서버로 데이터를 전송
        :param data: 전송할 데이터
        :return: 서버 응답
        """
        try:
            response = requests.post(self.server_url, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"서버 통신 오류: {e}")
            return None

