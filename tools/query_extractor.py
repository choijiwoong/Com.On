import sys
import urllib.parse

def extract_user_queries_from_log(file_path, output_path="output_queries.txt"):
    queries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "query=" in line:
                start = line.find("query=") + len("query=")
                query_raw = line[start:]

                # 'HTTP' 이후 제거
                if 'HTTP' in query_raw:
                    query_raw = query_raw.split('HTTP')[0]

                # URL 디코딩
                query_decoded = urllib.parse.unquote_plus(query_raw).strip()

                # 너무 짧은 쿼리 제외 & 중복 제거
                if len(query_decoded) > 5 and query_decoded not in queries:
                    queries.append(query_decoded)

    # 파일로 저장
    with open(output_path, 'w', encoding='utf-8') as out_f:
        for q in queries:
            out_f.write(f"{q}\n\n")  # 줄 바꿈 두 번 (가독성 위해)

    print(f"✅ 총 {len(queries)}개의 쿼리를 '{output_path}'에 저장했습니다.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ 로그 파일명을 인자로 입력해주세요.")
        print("예시: python extract_queries.py log.txt")
        sys.exit(1)

    file_path = sys.argv[1]
    extract_user_queries_from_log(file_path)

