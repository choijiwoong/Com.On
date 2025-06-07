# Python 설치된 가벼운 리눅스
FROM python:3.10-slim      

# 작업 디렉토리 설정
WORKDIR /app               

# 필요한 패키지 목록 복사
COPY requirements.txt ./   

# 패키지 설치
RUN pip install -r requirements.txt   

# 나머지 코드 복사
COPY . .                   

# Flask 기본 포트
EXPOSE 5000                

# 실행 명령어
CMD ["flask", "run", "--host=0.0.0.0"]  

