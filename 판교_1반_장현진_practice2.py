"""
====================================================================
 작성자 : P023_장현진_Practice2 실습
 작성일 : 2026.08.03
--------------------------------------------------------------------
 프로그램 설명
   sales_input.csv 파일을 매출 데이터로 사용합니다.
   먼저 Pydantic의 SalesRecord 클래스로 매출 한 건의 형식과
   검증 조건을 정합니다. month와 region은 빈 값이 될 수 없고,
   amount는 0보다 커야 하며, 비어 있는 category는 None으로 바꿉니다.

   safe_load_csv()  -    함수에서는 CSV 파일을 딕셔너리 목록으로 읽습니다.
                        파일이 없거나 인코딩·CSV·운영체제 오류가 발생하면 오류 로그를 남기고
                        None을 반환합니다. 파일을 읽었는지와 관계없이 finally에서 로딩 종료를 기록합니다.

   validate_sales() -   함수에서는 CSV의 각 행을 SalesRecord로 검증합니다.
                        검증에 성공한 행은 valid 목록에 저장하고, 실패한 행은 프로그램 전체를
                        중단하지 않고 행 번호·원본 데이터·오류 내용을 errors 목록에 저장합니다.

   save_valid_records() -   함수에서는 정상 SalesRecord를 model_dump()로
                            딕셔너리로 변환한 뒤 valid_sales.csv 파일로 저장합니다.
   
   save_errors()    -       함수에서는 errors 목록을 한글이 보존되는 errors.json 파일로 저장합니다.

   마지막으로 main() 함수에서 CSV 읽기, 행별 검증, 정상·오류 파일 저장,
   정상 CSV 재로딩 순서로 전체 작업을 실행합니다.
   정상 4건, 오류 3건, 재로딩 4건인지 assert로 확인하여
   데이터가 저장 과정에서 누락되지 않았는지 검증합니다.
====================================================================
"""

#================================================================
# 라이브러리 영역
import csv
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
#================================================================

#================================================================
# 로깅 영역
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s |%(levelname)s |%(message)s",
)
logger = logging.getLogger(__name__)
#================================================================

#================================================================
# 실습 문제 2 풀이

# 1) Pydantic 데이터 검증 모델
class SalesRecord(BaseModel):
    """매출 데이터 한 건의 형식과 검증 조건을 정의합니다."""

    # 문자열 앞뒤 공백을 제거한 뒤 필드 제약 조건을 검사합니다.
    model_config = ConfigDict(str_strip_whitespace=True)

    # 월과 지역은 비어 있지 않은 문자열이어야 합니다.
    month: str = Field(min_length=1)
    region: str = Field(min_length=1)

    # amount는 정수로 변환되며 0보다 큰 값만 허용합니다.
    amount: int = Field(gt=0)

    # category는 생략할 수 있고, 빈 값은 아래 검증기에서 None으로 변환합니다.
    category: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def empty_category_to_none(cls, value: Any) -> Any:
        """빈 카테고리를 선택값인 None으로 변환합니다."""
        if isinstance(value, str) and not value.strip():
            return None
        return value
#================================================================

#================================================================
# 2) CSV 파일 안전 읽기
def safe_load_csv(file_path: str | Path) -> list[dict[str, str]] | None:
    """CSV 파일을 안전하게 읽어 행 목록을 반환합니다."""
    path = Path(file_path)
    raw_data: list[dict[str, str]] = []

    try:
        # utf-8-sig는 BOM이 있거나 없는 UTF-8 CSV를 읽을 수 있습니다.
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            raw_data = list(reader)

        logger.info("CSV 읽기 성공:%s,%d건", path, len(raw_data))
        return raw_data

    except FileNotFoundError:
        logger.error("CSV 파일을 찾을 수 없습니다:%s", path)
        return None
    except UnicodeDecodeError as error:
        logger.error("CSV 인코딩을 해석할 수 없습니다:%s", error)
        return None
    except csv.Error as error:
        logger.error("CSV 형식이 올바르지 않습니다:%s", error)
        return None
    except OSError as error:
        logger.error("CSV 파일을 읽는 중 운영체제 오류가 발생했습니다:%s", error)
        return None
    finally:
        logger.info("로딩 종료:%s", path)
#================================================================

#================================================================
# 3) Pydantic을 이용한 행별 데이터 검증
def validate_sales(
    raw_data: list[dict[str, str]],
) -> tuple[list[SalesRecord], list[dict[str, Any]]]:
    """원본 행을 검증하여 정상 목록과 오류 목록으로 분리합니다."""
    valid: list[SalesRecord] = []
    errors: list[dict[str, Any]] = []

    for row_number, row in enumerate(raw_data, start=2):
        try:
            # 딕셔너리를 SalesRecord로 검증하고 자료형을 변환합니다.
            record = SalesRecord.model_validate(row)
            valid.append(record)
        except ValidationError as error:
            # 한 행의 실패가 전체 검증을 중단하지 않도록 오류를 저장합니다.
            error_item = {
                "row": row_number,
                "data": row,
                "error": error.errors(),
            }
            errors.append(error_item)
            logger.error("%d행 검증 실패:%s", row_number, error)

    logger.info("검증 완료: 정상%d건, 오류%d건", len(valid), len(errors))
    return valid, errors
#================================================================

#================================================================
# 4) 검증을 통과한 정상 데이터 CSV 저장
def save_valid_records(
    records: list[SalesRecord],
    file_path: str | Path,
) -> None:
    """검증을 통과한 매출 데이터를 CSV 파일로 저장합니다."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["month", "region", "category", "amount"]

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            # Pydantic v2 모델을 저장 가능한 딕셔너리로 변환합니다.
            writer.writerow(record.model_dump())

    logger.info("정상 데이터 저장 완료:%s,%d건", path, len(records))
#================================================================

#================================================================
# 5) 검증에 실패한 오류 데이터 JSON 저장
def save_errors(
    errors: list[dict[str, Any]],
    file_path: str | Path,
) -> None:
    """검증 오류를 한글이 보존되는 JSON 파일로 저장합니다."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(errors, file, ensure_ascii=False, indent=2)

    logger.info("오류 데이터 저장 완료:%s,%d건", path, len(errors))
#================================================================

#================================================================
# 6) 파일 읽기부터 재검증까지 전체 파이프라인 실행
def main() -> None:
    """파일 읽기부터 재로딩 검증까지 전체 파이프라인을 실행합니다."""
    input_path = Path("sales_input.csv")
    valid_path = Path("output/valid_sales.csv")
    error_path = Path("output/errors.json")

    # 1) 원본 CSV를 안전하게 읽습니다.
    raw_data = safe_load_csv(input_path)
    if raw_data is None:
        logger.error("입력 파일을 읽지 못해 파이프라인을 종료합니다.")
        return

    # 2) 정상 데이터와 오류 데이터를 분리합니다.
    valid, errors = validate_sales(raw_data)

    # 3) 정상 데이터는 CSV, 오류 데이터는 JSON으로 저장합니다.
    save_valid_records(valid, valid_path)
    save_errors(errors, error_path)

    # 4) 저장된 정상 CSV를 다시 읽어 건수를 검증합니다.
    reloaded = safe_load_csv(valid_path)
    assert reloaded is not None
    assert len(valid) == 4
    assert len(errors) == 3
    assert len(reloaded) == len(valid)

    logger.info(
        "파이프라인 완료: 입력%d건, 정상%d건, 오류%d건, 재로딩%d건",
        len(raw_data),
        len(valid),
        len(errors),
        len(reloaded),
    )
#================================================================


if __name__ == "__main__":
    main()
#================================================================
'''
출력 내용
2026-08-03 16:45:08,760 |INFO |CSV 읽기 성공:sales_input.csv,7건
2026-08-03 16:45:08,760 |INFO |로딩 종료:sales_input.csv
2026-08-03 16:45:08,760 |ERROR |6행 검증 실패:1 validation error for SalesRecord
'''
#================================================================