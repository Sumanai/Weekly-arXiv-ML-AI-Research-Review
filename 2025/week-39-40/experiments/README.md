# 🤖 Qwen3 0.6B MoE - Mixture-of-Experts Transformer

> Полная реализация архитектуры Mixture-of-Experts Transformer с нуля на PyTorch

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)
[![Tests](https://img.shields.io/badge/Tests-70%2B%20passing-success.svg)]()
[![Progress](https://img.shields.io/badge/Progress-60%25-yellow.svg)]()

---

## 📋 Описание проекта

Данный проект представляет собой **образовательную реализацию** архитектуры Mixture-of-Experts (MoE) Transformer, основанную на модели Qwen3, но адаптированную для меньшего размера (0.6B параметров).

### Ключевые особенности:

- ✅ **Полная реализация с нуля** - все компоненты написаны вручную
- ✅ **Детально протестировано** - 70+ unit тестов (все проходят)
- ✅ **Подробная документация** - каждый компонент с примерами
- ✅ **Учебная направленность** - TODO-шаблоны и вопросы для размышления
- ✅ **DDD архитектура** - чистая организация кода

---

## 🎯 Архитектура модели

### Конфигурация Qwen3 0.6B MoE

```
Model Size:        0.6B параметров
Num Experts:       8 (вместо 128 в Qwen3-30B)
Active Experts:    2 per token (вместо 8 в Qwen3-30B)
Activation:        25% экспертов (vs 6.25% в 30B)
Hidden Size:       512
Intermediate Size: 2048 (4 × hidden_size)
Attention:         Grouped-Query Attention (GQA)
Normalization:     RMSNorm
Position Encoding: RoPE (Rotary Position Embedding)
Activation:        SwiGLU
```

### Основные компоненты

```
Qwen3 MoE Model
│
├── Embedding Layer
│
├── N × MoE Transformer Blocks
│   ├── RMSNorm
│   ├── Grouped-Query Attention (GQA)
│   │   ├── Query projection (8 groups)
│   │   ├── Key/Value projection (shared)
│   │   └── RoPE position encoding
│   ├── RMSNorm
│   └── MoE Feed-Forward Layer
│       ├── MoE Router (Top-K gating)
│       ├── 8 × Expert Networks (SwiGLU)
│       └── Load Balancing Loss
│
└── LM Head (Output projection)
```

---

## 📊 Прогресс реализации

### ✅ Фаза 1: Базовая архитектура (100%)

| Компонент | Статус | Тесты | Файл |
|-----------|--------|-------|------|
| RMSNorm | ✅ Завершено | ✅ Все | `experiments/domain/normalization/rmsnorm.py` |
| RoPE | ✅ Завершено | ✅ Все | `experiments/domain/positional_encoding/rope.py` |
| SwiGLU | ✅ Завершено | ✅ Все | `experiments/domain/activations/swiglu.py` |
| GQA | ✅ Завершено | ✅ 12/12 | `experiments/domain/attention/gqa.py` |
| TransformerBlock | ✅ Завершено | ✅ 14/14 | `experiments/domain/transformer/transformer_block.py` |

### 🟡 Фаза 2: MoE компоненты (85%)

| Компонент | Статус | Тесты | Файл |
|-----------|--------|-------|------|
| MoE Router | ✅ Завершено | ✅ 15/15 | `experiments/domain/moe/router.py` |
| Expert Network | ✅ Завершено | ✅ 15/15 | `experiments/domain/moe/expert.py` |
| MoE Layer | 🔄 В процессе | ⏳ 0/12 | `experiments/domain/moe/moe_layer.py` |
| MoE TransformerBlock | ⏳ Ожидание | - | - |

### ⏳ Фаза 3: Полная модель (0%)

- ⏳ Конфигурация модели 0.6B
- ⏳ Embedding слой
- ⏳ Сборка N × MoE Transformer Blocks
- ⏳ LM Head
- ⏳ Utilities для генерации

---

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install torch pytest
```

### Запуск тестов

```bash
# Все тесты
pytest experiments/ -v

# Отдельные компоненты
pytest experiments/domain/moe/test/test_router.py -v
pytest experiments/domain/moe/test/test_expert.py -v
pytest experiments/domain/attention/test/test_gqa.py -v
```

### Интерактивное тестирование MoE

```bash
python3 experiments/domain/moe/test_integration.py
```

### Использование компонентов

```python
import torch
from experiments.domain.moe.router import MoERouter
from experiments.domain.moe.expert import Expert

# Создание Router для модели 0.6B
router = MoERouter(
    hidden_size=512,
    num_experts=8,
    top_k=2
)

# Создание Expert Network
expert = Expert(
    hidden_size=512,
    intermediate_size=2048
)

# Forward pass
x = torch.randn(2, 10, 512)  # (batch, seq, hidden)
routing_weights, selected_experts, balance_loss = router(x)
```

---

## 📁 Структура проекта

```
experiments/
├── domain/
│   ├── normalization/
│   │   ├── rmsnorm.py              # RMS Normalization
│   │   └── test/
│   ├── positional_encoding/
│   │   ├── rope.py                 # Rotary Position Embedding
│   │   └── test/
│   ├── activations/
│   │   ├── swiglu.py              # SwiGLU Activation
│   │   ├── SwiGLU.md              # Документация
│   │   └── test/
│   ├── attention/
│   │   ├── gqa.py                 # Grouped-Query Attention
│   │   ├── GQA.md                 # Документация
│   │   ├── GQA_Forward_Explained.md
│   │   └── test/
│   ├── transformer/
│   │   ├── transformer_block.py   # Transformer Block
│   │   └── test/
│   └── moe/
│       ├── router.py              # MoE Router (Top-K gating)
│       ├── expert.py              # Expert Network
│       ├── moe_layer.py           # MoE Layer (интеграция)
│       ├── MoE_Router_Gate_Initialization.md     # Документация (885 строк)
│       ├── MoE_Router_Load_Balancing_Loss.md     # Документация (1067 строк)
│       ├── test_integration.py    # Интерактивное тестирование
│       └── test/
│
└── memory/
    ├── memory-bank/               # Банк памяти проекта
    │   ├── projectbrief.md
    │   ├── activeContext.md
    │   ├── progress.md
    │   ├── techContext.md
    │   └── systemPatterns.md
    └── rules/
        └── memory-bank.mdc        # Выученные паттерны
```

---

## 🧪 Тестирование

### Статистика тестов

```
Всего тестов: 70+
Успешно:      70+ (100%)
Покрытие:     Все ключевые компоненты

Breakdown:
├── RMSNorm:          ✅ Все тесты
├── RoPE:             ✅ Все тесты
├── SwiGLU:           ✅ Все тесты
├── GQA:              ✅ 12/12
├── TransformerBlock: ✅ 14/14
├── MoE Router:       ✅ 15/15
└── Expert Network:   ✅ 15/15
```

### Типы тестов

- ✅ **Инициализация**: валидация параметров, корректность атрибутов
- ✅ **Forward pass**: размерности тензоров, корректность вычислений
- ✅ **Gradient flow**: распространение градиентов
- ✅ **Численная стабильность**: большие/маленькие значения
- ✅ **Детерминизм**: воспроизводимость результатов
- ✅ **Интеграция**: взаимодействие компонентов

---

## 📚 Документация

### Подробные гайды

- **[SwiGLU.md](experiments/domain/activations/SwiGLU.md)** - Активационная функция с примерами
- **[GQA.md](experiments/domain/attention/GQA.md)** - Grouped-Query Attention архитектура
- **[GQA_Forward_Explained.md](experiments/domain/attention/GQA_Forward_Explained.md)** - Построчное объяснение forward pass
- **[MoE_Router_Gate_Initialization.md](experiments/domain/moe/MoE_Router_Gate_Initialization.md)** - Инициализация gate layer (885 строк)
- **[MoE_Router_Load_Balancing_Loss.md](experiments/domain/moe/MoE_Router_Load_Balancing_Loss.md)** - Load balancing loss (1067 строк)

### Ключевые концепции

#### Grouped-Query Attention (GQA)
Снижает размер KV cache за счёт группировки запросов:
```
Query:  8 групп × 64 dim = 512 параметров
Key+Value: 16 голов × 64 dim × 2 = 2048 параметров
Соотношение KV/Q = 4.0x
```

#### Load Balancing Loss
Предотвращает "коллапс экспертов":
```python
L = α * N * Σ(f_i * P_i)
где:
  f_i = frequency (как часто эксперт выбирается)
  P_i = mean probability (средняя уверенность модели)
  α = balance_loss_coef (0.01)
  N = num_experts (8)
```

---

## 🎓 Образовательная ценность

### Для кого этот проект

- 📚 **Студенты ML/DL** - изучение архитектуры Transformer и MoE с нуля
- 🔬 **Исследователи** - экспериментирование с MoE компонентами
- 👨‍💻 **ML инженеры** - понимание внутреннего устройства LLM
- 🏫 **Преподаватели** - учебный материал с TODO-шаблонами

### Педагогический подход

- ✅ **TODO-driven development** - пошаговая реализация
- ✅ **Вопросы для размышления** - развитие понимания
- ✅ **Подробные комментарии** - объяснение каждой строки
- ✅ **Математические формулы** - теория + практика
- ✅ **Визуализации** - ASCII-art диаграммы процессов

---

## 🔍 Ключевые особенности реализации

### 1. RMSNorm vs LayerNorm
```python
# RMSNorm: x / sqrt(mean(x²) + eps) * weight
# Преимущества:
# - Нет центрирования (не вычитает среднее)
# - Лучшая численная стабильность
# - Меньше вычислений
# - Используется в LLaMA, Qwen
```

### 2. RoPE Position Encoding
```python
# Rotary Position Embedding
# - Вращение в комплексной плоскости
# - Относительное позиционное кодирование
# - Хорошо экстраполируется на длинные последовательности
```

### 3. SwiGLU Activation
```python
# SwiGLU(x, W1, W2) = Swish(W1·x) ⊙ (W2·x)
# Используется в PaLM, LLaMA, Qwen3
# Лучше чем ReLU/GELU в глубоких моделях
```

### 4. MoE Router
```python
# Top-K gating с load balancing
# 1. Gate projection: logits = Linear(hidden_states)
# 2. Softmax: probabilities = softmax(logits)
# 3. Top-K: выбор K лучших экспертов
# 4. Re-normalization: normalize(selected weights)
# 5. Balance loss: предотвращение коллапса экспертов
```

---

## 🤝 Вклад в проект

Этот проект создан в образовательных целях. Если вы хотите внести вклад:

1. 🐛 **Найдена ошибка?** Откройте issue с подробным описанием
2. 💡 **Идея улучшения?** Предложите в discussions
3. 📝 **Улучшение документации?** Pull request приветствуется
4. ✨ **Новый компонент?** Следуйте стилю проекта

---

## 📖 Обучающие материалы

### Рекомендуемый порядок изучения

1. **Базовые компоненты**:
   - RMSNorm → RoPE → SwiGLU
   - Grouped-Query Attention
   - TransformerBlock

2. **MoE компоненты**:
   - MoE Router (gating mechanism)
   - Expert Network (feed-forward)
   - MoE Layer (интеграция)

3. **Полная модель**:
   - Конфигурация
   - Embedding + N×Blocks + LM Head
   - Генерация текста

### Интерактивное обучение

```bash
# Запустите интерактивное тестирование
python3 experiments/domain/moe/test_integration.py

# Вы увидите:
# - Как Router выбирает экспертов
# - Распределение токенов по экспертам
# - Визуализацию load balancing
# - Требования для MoE Layer
```

---

## 📈 Метрики и статистика

### Прогресс проекта
```
Общий прогресс:    60%
Строк кода:        ~3500+ (реализация)
Строк тестов:      ~2500+
Документация:      ~6000+ строк в .md файлах
Комментарии:       Подробные в каждом файле
```

### Производительность
```
Размер модели:     0.6B параметров
Активных параметров: ~0.15-0.2B (25-33%)
Память:            Оптимизировано через GQA
Тесты:             Все проходят за ~5 секунд
```

---

## 🔗 Ссылки и ресурсы

### Архитектура
- [Qwen3 Technical Report](https://arxiv.org/abs/2409.12186)
- [Mixture-of-Experts with Expert Choice Routing](https://arxiv.org/abs/2202.09368)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [GQA: Training Generalized Multi-Query Transformer Models](https://arxiv.org/abs/2305.13245)

### Реализации
- [Hugging Face Transformers](https://github.com/huggingface/transformers)
- [PyTorch](https://pytorch.org/)

---

## 📝 Лицензия

Этот проект создан в образовательных целях. Код предоставляется "как есть" для изучения архитектуры MoE Transformer.

---

## 🙏 Благодарности

Особая благодарность:
- Команде Qwen3 за открытую архитектуру
- Сообществу PyTorch за отличный фреймворк
- Всем исследователям в области MoE и Transformers

---

<div align="center">

**Made with ❤️ for ML Education**

⭐ Star this repo if you found it helpful!

</div>
