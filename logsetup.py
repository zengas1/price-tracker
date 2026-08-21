"""Çıktıyı log dosyasına yönlendirir.

pythonw.exe ile (konsol penceresi açmadan) çalıştırıldığında sys.stdout/stderr
yoktur; bu yüzden print() çağrılarının çökmemesi için ikisini de bir dosyaya
yönlendiriyoruz. Aynı zamanda konsollu çalıştırmalarda da (python.exe) sorunsuz
çalışır.
"""

import sys
from pathlib import Path


def redirect_output(log_path: Path) -> None:
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file
