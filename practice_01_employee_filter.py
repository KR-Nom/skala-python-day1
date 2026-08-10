"""직원 데이터를 필터링하고 정렬하며 부서별 평균 급여를 계산합니다."""

from collections import defaultdict


employees = [
    {"name": "Alice", "department": "Engineering", "age": 30, "salary": 85000},
    {"name": "Bob", "department": "Marketing", "age": 25, "salary": 60000},
    {"name": "Charlie", "department": "Engineering", "age": 35, "salary": 95000},
    {"name": "David", "department": "HR", "age": 40, "salary": 70000},
    {"name": "Eve", "department": "Marketing", "age": 28, "salary": 78000},
]


# 문제1. Engineering 부서이며 급여가 80,000 이상인 직원명을 추출합니다.
engineering_high_salary = [
    employee["name"]
    for employee in employees
    if employee["department"] == "Engineering"
    and employee["salary"] >= 80000
]


# 문제2. 30세 이상 직원의 이름과 부서를 튜플로 구성합니다.
employees_over_30 = [
    (employee["name"], employee["department"])
    for employee in employees
    if employee["age"] >= 30
]


# 문제3. 급여를 기준으로 내림차순 정렬합니다.
sorted_employees = sorted(
    employees,
    key=lambda employee: employee["salary"],
    reverse=True,
)

# 문제3. 상위 세 명의 이름과 급여를 추출합니다.
top_three = [
    (employee["name"], employee["salary"])
    for employee in sorted_employees[:3]
]


# 문제4. 부서별 급여 목록을 생성합니다.
department_salaries = defaultdict(list)

for employee in employees:
    department_salaries[employee["department"]].append(employee["salary"])

# 문제4. 부서별 평균 급여를 계산합니다.
department_averages = {
    department: sum(salaries) / len(salaries)
    for department, salaries in department_salaries.items()
}


print("고액 급여 엔지니어:", engineering_high_salary)
print("30세 이상:", employees_over_30)
print("급여 상위 3명:", top_three)
print("부서별 평균 급여:", department_averages)