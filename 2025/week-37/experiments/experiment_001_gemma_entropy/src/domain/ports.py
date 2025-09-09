"""
Порт(ы) домейна для абстракции доступа к языковой модели.

Вы должны реализовать весь интерфейс ModelPort.

Предлагаю вам дропнуть весь код, и оставить только подсказки TODO, что нужно реализовать 🤗
"""

# Стандартная библиотека
from typing import Any, Dict, Protocol


class ModelPort(Protocol):
    """
    Description:
    ---------------
        Контракт доступа к модели и токенизатору, необходимый приложению
        для анализа вероятностей и генерации.

    Notes:
    ---------------
        Это интерфейс (Protocol). Инфраструктурная реализация должна обеспечить
        фактическую работу с библиотекой transformers.
    """

    def load_model(self) -> None:
        """Загружает модель и токенизатор согласно конфигурации."""

    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает информацию о модели и окружении."""

    def tokenize(self, text: str, *, max_length: int) -> Dict[str, Any]:
        """Возвращает входы модели (тензоры) для текста."""

    def forward(self, **inputs: Any) -> Any:
        """Выполняет прямой проход и возвращает outputs с полем logits."""

    def convert_ids_to_tokens(self, ids_tensor: Any) -> Any:
        """Преобразует ids в строковые токены."""

    def decode_token(self, token_id_tensor: Any) -> str:
        """Декодирует один токен в текст (без спецсимволов)."""

    def decode_sequence(self, token_ids: Any) -> str:
        """Декодирует последовательность токенов в строку (без спецсимволов)."""

    def eos_token_id(self) -> int:
        """Возвращает ID токена конца последовательности (EOS)."""

    def context_length(self) -> int:
        """Возвращает максимально допустимую длину контекста из конфигурации."""

    @property
    def device(self) -> Any:
        """Возвращает устройство выполнения (cpu/cuda/mps)."""
