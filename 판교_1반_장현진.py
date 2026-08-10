"""
작성자 : P023_장현진_Practice1 실습

코드 내용 : [심화 실습] 자료구조 집계 · 컴프리헨션 · 제너레이터

작성일 : 2026.08.03

"""

#================================================================
# 라이브러리 영역
import json
from collections import defaultdict
from collections import Counter
import sys
#================================================================

#================================================================
# 전역 변수 선언 영역
try:
    with open("Python_Practice1_Data.json", mode="r", encoding="utf-8") as file:
        data = json.load(file)

    sales = data

except FileNotFoundError:
    print("JSON 파일을 찾을 수 없습니다.")

except json.JSONDecodeError:
    print("JSON 파일 형식이 올바르지 않습니다.")
#================================================================

#================================================================
# 실습 문제 1 풀이

# 1) 전체 거래 중 금액이 1000 이상인 거래 목록 생성
amount_high_sale = [
    sale
    for sale in sales
    if sale["amount"] >= 1000
]

# 2) 전체 거래를 기준으로 지역별 총매출 계산
region_total = {
    region: sum(
        sale["amount"]
        for sale in sales
        if sale["region"] == region
    )
    for region in (sale["region"] for sale in sales)
}

# 3) 금액이 1000 이상인 거래만 대상으로 지역별 총매출 계산
amount_high_region = {
    region: sum(
        sale["amount"]
        for sale in sales
        if sale["region"] == region 
        and sale["amount"] >= 1000
    )
    for region in (sale["region"] for sale in sales)
}

# 실습문제 1 결과 출력
# print(f"{amount_high_sale}")      ## 전체 거래 중 금액이 1000 이상인 거래 목록
# print(f"{region_total}")          ## 전체 거래를 기준으로 지역별 총매출
# print(f"{amount_high_region}")    ## 1000 이상 거래 기준 지역별 총매출
#================================================================

#================================================================
# 실습 문제 2 풀이

# 1) Counter로 지역별 거래 건수
region_count = Counter(
    sale["region"]
    for sale in sales
)
region_count_common = region_count.most_common()

# 2) defalutdict로 카테고리별 amount 리스트
category_amount = defaultdict(list)
for sale in sales :
    category = sale["category"]
    amount = sale["amount"]

    category_amount[category].append(amount)
    
# 실습문제 2 결과 출력
# print(f"{region_count}")          ## 지역별 거래 건수
# print(f"{category_amount}")       ## 카테고리별 amount 목록
#================================================================

#================================================================
# 실습 문제 3

# 1) 제너레이터 함수, 리스트 컴프리헨션 작성하기
def iter_high_amount(sales_data, min_amount):
    for sale in sales_data:
        if sale["amount"] > min_amount:
            yield sale

sales_list = [
    sale
    for sale in sales
    if sale["amount"] > 1000
]

# 2) 리스트 버전과 제너레이터 버전 메모리 크기 비교
sales_gener = iter_high_amount(sales, 1000)

list_size = sys.getsizeof(sales_list)
gener_size = sys.getsizeof(sales_gener)

# 금액 기준 상위 3개 거래를 내림차순으로 정렬
top3_sales = sorted(sales, key=lambda sale: sale["amount"], reverse=True)[:3]

# 실습문제 3 결과 출력
# print(f"{list_size}")             ## 리스트의 메모리 크기
# print(f"{gener_size}")            ## 제너레이터의 메모리 크기
#================================================================

#================================================================
# 실습 문제 4

# 1) defalutdict 생성하기
month_category = defaultdict(lambda: defaultdict(int))

# 2) 월, 카테고리, 금액을 나눈 후 월과 카테고리 조합 합계에 거래 금액 누적
for sale in sales:
    month = sale["month"]
    category = sale["category"]
    amount = sale["amount"]

    month_category[month][category] += amount

# 3) 월과 카테고리 순으로 정렬하여 중첩 defaultdict를 일반 딕셔너리로 변환
month_category = {
    month: {
        category: category_total[category]
        for category in sorted(category_total)
    }
    for month, category_total in sorted (month_category.items())    
}

# 실습 문제 4 결과 출력
# 4) 월을 먼저 출력하고, 해당 월의 카테고리별 총매출을 천 단위 구분기호와 함께 출력
# for month, category_total in month_category.items():
#     print(f"{month}")                                       ## 월 출력
#     for category, total in category_total.items():      
#         print(f"{category}:{total:,}")                      ## 카테고리별 총매출 출력
#================================================================

#================================================================
# 결과 출력 모음
# 실습문제 1 결과 출력
print("[실습문제 1]")
print("1000 이상 거래 목록:", amount_high_sale)
print("전체 지역별 총매출:", region_total)
print("1000 이상 거래 기준 지역별 총매출:", amount_high_region)

# 실습문제 2 결과 출력
print("\n[실습문제 2]")
print("지역별 거래 건수:", region_count)
print("지역별 거래 건수 순위:", region_count_common)
print("카테고리별 amount 목록:", dict(category_amount))

# 실습문제 3 결과 출력
print("\n[실습문제 3]")
print("리스트 메모리 크기:", list_size)
print("제너레이터 메모리 크기:", gener_size)
print("제너레이터가 리스트보다 작은가:", gener_size < list_size)

# 실습문제 4 결과 출력
print("\n[실습문제 4]")
for month, category_total in month_category.items():
    print(month)
    for category, total in category_total.items():
        print(f"{category}: {total:,}")

# 체크포인트: 금액 상위 3개 내림차순
print("\n금액 상위 3개:", top3_sales)
#================================================================
