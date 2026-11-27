from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    test_id: str
    device_id: str
    operation: str
    request: Any
    outcome: Any
    response: Any
    logs: List[str]
    operation_not_supported_ack: Optional[Dict[str, str]] = None


@dataclass
class TestSuite:
    test_result_list: List[TestResult]
    suite_name: str
