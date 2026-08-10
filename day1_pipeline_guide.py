"""
====================================================================
 작성자 : P023_장현진_Day1 종합 실습
 작성일 : 2026.08.03
 GitHub : https://github.com/KR-Nom/SKALA
 버전   : v1.0.0
--------------------------------------------------------------------
 변경사항
   v1.0.0 (2026.08.03)
   - asyncio.gather()를 사용하여 날씨·국가·IP API 동시 수집
   - Pydantic v2 모델을 이용한 응답 데이터 타입·범위 검증
   - HTTP·스키마·파이프라인·파일 처리 오류에 대한 예외 처리
   - 검증된 날씨 데이터를 CSV와 Parquet 두 형식으로 저장
   - CSV와 Parquet의 읽기·쓰기 실행 시간 측정 및 비교
--------------------------------------------------------------------
 프로그램 설명
   날씨·국가·IP API의 JSON 데이터를 비동기로 동시에 수집합니다.
   수집한 응답에서 필요한 필드를 추출한 뒤 Pydantic v2 모델로
   데이터의 자료형과 허용 범위를 검증합니다.

   async_timer()       - 비동기 함수의 실행 시간을 측정하고 기록합니다.

   fetch_json()        - API를 호출하고 HTTP 상태와 JSON 객체 여부를
                         확인한 뒤 정상 응답을 반환합니다.

   collect_all()       - asyncio.gather()로 세 API를 동시에 호출합니다.

   validate_weather() - 시간대별 날씨 데이터의 길이·타입·범위를 검증합니다.

   validate_country() - 국가 응답에서 이름·수도·지역·인구를 추출합니다.

   validate_ip()      - IP API 성공 여부와 위치 정보 범위를 검증합니다.

   save_and_compare() - 날씨 데이터를 CSV와 Parquet으로 저장하고 다시
                        읽어 데이터 건수와 읽기·쓰기 시간을 비교합니다.

   마지막으로 main() 함수에서 환경변수의 출력 경로를 확인하고 데이터
   수집, 검증, 저장, 성능 비교 순서로 전체 파이프라인을 실행합니다.
   실행 중 오류가 발생하면 오류 유형별 로그를 남기고 안전하게 종료합니다.
--------------------------------------------------------------------
 실행 및 검사
   python3 day1_pipeline_guide.py
   python3 -m pytest -v
   python3 -m ruff check .
====================================================================
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from pydantic import BaseModel, Field, ValidationError


WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia%2FSeoul"
)
COUNTRY_URL = "https://countries.dev/alpha/KOR"
IP_URL = "http://ip-api.com/json/8.8.8.8"


class PipelineError(RuntimeError):
    """수집 또는 데이터 구조가 파이프라인 규칙을 위반할 때 발생합니다."""


#================================================================
# 1) 비동기 함수 실행 시간 측정 데코레이터
def async_timer(function):
    """비동기 함수의 실행 시간을 로그로 기록합니다."""

    @wraps(function)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()

        try:
            # 비동기 함수의 실행이 끝날 때까지 기다린 뒤 결과를 그대로 반환합니다.
            return await function(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logging.info("%s 실행 시간:%.6f초", function.__name__, elapsed)

    return wrapper
#================================================================


#================================================================
# 2) API 데이터 검증 모델
class WeatherRecord(BaseModel):
    """시간대별 서울 날씨 한 건."""

    time: datetime
    temperature_2m: float = Field(ge=-100, le=60)
    precipitation_probability: int = Field(ge=0, le=100)


class CountryRecord(BaseModel):
    """한국 국가 정보 중 필요한 값."""

    name: str = Field(min_length=1)
    capital: str = Field(min_length=1)
    region: str = Field(min_length=1)
    population: int = Field(gt=0)


class IpRecord(BaseModel):
    """IP 기반 지역 정보 중 필요한 값."""

    query: str = Field(min_length=1)
    country: str = Field(min_length=1)
    city: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
#================================================================


#================================================================
# 3) API JSON 데이터 안전 수집
async def fetch_json(
    client: httpx.AsyncClient,
    api_name: str,
    url: str,
) -> dict[str, Any]:
    """API 하나를 호출하여 JSON 객체를 반환합니다."""
    response = await client.get(url)
    response.raise_for_status()
    logging.info("%s API 요청 성공:상태 코드 %d", api_name, response.status_code)

    payload = response.json()
    if not isinstance(payload, dict):
        raise PipelineError(f"{api_name} API 응답이 JSON 객체가 아닙니다")
    return payload
#================================================================


#================================================================
# 4) 세 API 비동기 동시 수집
@async_timer
async def collect_all() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """세 API를 동시에 호출합니다."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        weather, country, ip = await asyncio.gather(
            fetch_json(client, "날씨", WEATHER_URL),
            fetch_json(client, "국가", COUNTRY_URL),
            fetch_json(client, "IP", IP_URL),
        )
    return weather, country, ip
#================================================================


#================================================================
# 5) 날씨 데이터 검증
def validate_weather(payload: dict[str, Any]) -> list[WeatherRecord]:
    """날씨 응답을 시간대별 모델 목록으로 검증합니다."""
    try:
        hourly = payload["hourly"]
        times = hourly["time"]
        temperatures = hourly["temperature_2m"]
        precipitation = hourly["precipitation_probability"]
    except (KeyError, TypeError) as error:
        raise PipelineError("날씨 응답 구조가 올바르지 않습니다") from error

    if not all(isinstance(values, list) for values in (times, temperatures, precipitation)):
        raise PipelineError("날씨 시간대 데이터가 리스트가 아닙니다")
    if len({len(times), len(temperatures), len(precipitation)}) != 1:
        raise PipelineError("날씨 데이터 길이가 일치하지 않습니다")

    return [
        WeatherRecord(
            time=time_value,
            temperature_2m=temperature,
            precipitation_probability=probability,
        )
        for time_value, temperature, probability in zip(
            times, temperatures, precipitation, strict=True
        )
    ]
#================================================================


#================================================================
# 6) 국가 데이터 검증
def validate_country(payload: dict[str, Any]) -> CountryRecord:
    """국가 응답에서 필요한 필드를 추출하고 검증합니다."""
    name_value = payload.get("name")
    if isinstance(name_value, dict):
        name_value = name_value.get("common") or name_value.get("official")

    capital_value = payload.get("capital")
    if isinstance(capital_value, list):
        capital_value = capital_value[0] if capital_value else None

    try:
        return CountryRecord(
            name=name_value,
            capital=capital_value,
            region=payload["region"],
            population=payload["population"],
        )
    except KeyError as error:
        raise PipelineError("국가 응답 구조가 올바르지 않습니다") from error
#================================================================


#================================================================
# 7) IP 지역 데이터 검증
def validate_ip(payload: dict[str, Any]) -> IpRecord:
    """IP 응답에서 필요한 필드를 추출하고 검증합니다."""
    if payload.get("status") != "success":
        message = payload.get("message", "알 수 없는 오류")
        raise PipelineError(f"IP API 응답 실패:{message}")
    return IpRecord.model_validate(payload)
#================================================================


#================================================================
# 8) 일반 함수 실행 시간 측정
def measure_operation(name, operation):
    """일반 함수 한 번의 실행 시간과 반환값을 돌려줍니다."""
    start = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - start
    logging.info("%s 실행 시간:%.6f초", name, elapsed)
    return result, elapsed
#================================================================


#================================================================
# 9) CSV/Parquet 저장 및 성능 비교
def save_and_compare(records: list[WeatherRecord], output_dir: Path) -> dict[str, float]:
    """검증된 날씨 데이터를 CSV/Parquet으로 저장하고 성능을 비교합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "weather.csv"
    parquet_path = output_dir / "weather.parquet"

    dataframe = pd.DataFrame(
        [record.model_dump(mode="json") for record in records]
    )

    _, csv_write = measure_operation(
        "CSV 저장", lambda: dataframe.to_csv(csv_path, index=False)
    )
    csv_data, csv_read = measure_operation("CSV 읽기", lambda: pd.read_csv(csv_path))
    _, parquet_write = measure_operation(
        "Parquet 저장", lambda: dataframe.to_parquet(parquet_path, index=False)
    )
    parquet_data, parquet_read = measure_operation(
        "Parquet 읽기", lambda: pd.read_parquet(parquet_path)
    )

    if len(csv_data) != len(records) or len(parquet_data) != len(records):
        raise PipelineError("저장 후 다시 읽은 날씨 데이터 건수가 일치하지 않습니다")

    return {
        "csv_write": csv_write,
        "csv_read": csv_read,
        "parquet_write": parquet_write,
        "parquet_read": parquet_read,
    }
#================================================================


#================================================================
# 10) 전체 파이프라인 실행
@async_timer
async def run_pipeline(
    output_dir: Path,
) -> tuple[list[WeatherRecord], CountryRecord, IpRecord, dict[str, float]]:
    """수집, 검증, 저장을 순서대로 실행합니다."""
    weather_payload, country_payload, ip_payload = await collect_all()
    weather_records = validate_weather(weather_payload)
    country_record = validate_country(country_payload)
    ip_record = validate_ip(ip_payload)
    timings = save_and_compare(weather_records, output_dir)

    logging.info("날씨 데이터 저장 완료:%d건", len(weather_records))
    return weather_records, country_record, ip_record, timings
#================================================================


#================================================================
# 11) 환경변수 출력 경로를 이용한 프로그램 실행
async def main() -> None:
    """환경변수에서 출력 경로를 읽고 파이프라인을 실행합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # 모범 답안처럼 환경변수를 지원하되 기본값을 제공합니다.
    output_dir = Path(os.getenv("OUTPUT_DIR", "data"))

    try:
        weather, country, ip, timings = await run_pipeline(output_dir)
        print(f"국가 정보:{country.model_dump()}")
        print(f"IP 정보:{ip.model_dump()}")
        print(f"날씨 데이터:{len(weather)}건")
        print(f"CSV 저장 시간:{timings['csv_write']:.6f}초")
        print(f"CSV 읽기 시간:{timings['csv_read']:.6f}초")
        print(f"Parquet 저장 시간:{timings['parquet_write']:.6f}초")
        print(f"Parquet 읽기 시간:{timings['parquet_read']:.6f}초")
    except httpx.HTTPError as error:
        logging.error("API 요청 오류: %s", error)
    except ValidationError as error:
        logging.error("스키마 검증 오류:\n%s", error)
    except PipelineError as error:
        logging.error("파이프라인 데이터 오류: %s", error)
    except OSError:
        logging.exception("파일 처리 중 운영체제 오류 발생")


if __name__ == "__main__":
    asyncio.run(main())
#================================================================
