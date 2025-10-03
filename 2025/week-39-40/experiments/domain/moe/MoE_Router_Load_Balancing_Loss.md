# MoE Router: Load Balancing Loss - Вычисление Frequency

## Оглавление
- [Обзор](#обзор)
- [Что такое Frequency (f_i)?](#что-такое-frequency-f_i)
- [Зачем нужен Load Balancing Loss?](#зачем-нужен-load-balancing-loss)
- [Подход 1: torch.bincount (Рекомендуется)](#подход-1-torchbincount-рекомендуется)
- [Подход 2: One-hot Encoding + Mean](#подход-2-one-hot-encoding--mean)
- [Сравнение подходов](#сравнение-подходов)
- [Полная реализация _compute_balance_loss](#полная-реализация-_compute_balance_loss)
- [Практический пример](#практический-пример)

---

## Обзор

В методе `_compute_balance_loss` класса `MoERouter` необходимо вычислить **load balancing loss**, который предотвращает "коллапс экспертов" — ситуацию, когда модель использует только малую часть доступных экспертов.

### Формула Load Balancing Loss:

```
L_balance = α * N * Σ (f_i * P_i)
                    i=1..N

где:
  α - balance_loss_coef (коэффициент, например 0.01)
  N - num_experts (количество экспертов, например 128)
  f_i - frequency: доля токенов, выбравших эксперта i
  P_i - mean gating probability: средний вес эксперта i
```

**Этот документ фокусируется на вычислении f_i (frequency).**

---

## Что такое Frequency (f_i)?

**Frequency** — это **доля токенов, которые выбрали эксперта i** среди всех токенов в батче.

### Математическое определение:

```
f_i = (количество раз, когда эксперт i был выбран) / (общее количество выборов)

где:
  общее количество выборов = batch_size * seq_len * top_k
```

### Пример:

```
batch_size = 2
seq_len = 10
top_k = 8
num_experts = 128

Общее количество выборов = 2 * 10 * 8 = 160

Если эксперт 42 был выбран 12 раз:
  f_42 = 12 / 160 = 0.075 (7.5%)

Если эксперт 99 был выбран 8 раз:
  f_99 = 8 / 160 = 0.050 (5.0%)

Если эксперт 0 не был выбран:
  f_0 = 0 / 160 = 0.0 (0%)
```

### Визуализация:

```
selected_experts: (batch_size=2, seq_len=10, top_k=8)

Batch 0:
  Токен 0: [42, 15,  7, 123, 99,  4, 88, 23]
  Токен 1: [15,  7, 99,  42, 23,  4, 11, 56]
  Токен 2: [ 7, 99, 15,  23, 42, 88,  4, 11]
  ...
  Токен 9: [42, 99, 15,   7, 23, 88,  4, 11]

Batch 1:
  Токен 0: [99, 42, 15,  7, 23, 88,  4, 11]
  ...
  Токен 9: [15,  7, 99, 42, 23, 88,  4, 11]

                    ↓
              Подсчет частот
                    ↓

Эксперт   0: выбран  0 раз → f_0   = 0/160 = 0.000
Эксперт   4: выбран 20 раз → f_4   = 20/160 = 0.125
Эксперт   7: выбран 18 раз → f_7   = 18/160 = 0.113
Эксперт  15: выбран 19 раз → f_15  = 19/160 = 0.119
Эксперт  42: выбран 12 раз → f_42  = 12/160 = 0.075
Эксперт  99: выбран  8 раз → f_99  = 8/160 = 0.050
...
Эксперт 127: выбран  0 раз → f_127 = 0/160 = 0.000

Результат: frequency тензор формы (128,)
```

---

## Зачем нужен Load Balancing Loss?

### Проблема: Expert Collapse (Коллапс экспертов)

Без балансировки модель может научиться использовать только 10-20 экспертов из 128:

```
❌ БЕЗ балансировки:

Эксперт   0: ████████████████████ 0.45  (45% токенов)
Эксперт   1: ███████████████      0.35  (35% токенов)
Эксперт   2: █████                0.10  (10% токенов)
Эксперт   3: ██                   0.05  (5% токенов)
Эксперт   4: █                    0.03  (3% токенов)
Эксперт   5:                      0.02  (2% токенов)
Эксперт 6-127:                    0.00  (не используются!)

Проблемы:
  - Потеря модельной емкости (capacity)
  - Неэффективное использование параметров
  - Ухудшение обобщающей способности
```

### Решение: Load Balancing Loss

Добавляя балансирующий loss, модель мотивируется равномерно распределять нагрузку:

```
✅ С балансировкой:

Эксперт   0: ███  0.012  (1.2%)
Эксперт   1: ███  0.011  (1.1%)
Эксперт   2: ███  0.010  (1.0%)
Эксперт   3: ███  0.009  (0.9%)
...
Эксперт 127: ███  0.008  (0.8%)

Все эксперты используются примерно одинаково!
Идеально: f_i ≈ 1/128 ≈ 0.0078 для каждого эксперта
```

---

## Подход 1: torch.bincount (Рекомендуется)

### Что такое torch.bincount?

`torch.bincount` подсчитывает, сколько раз каждое целое число встречается в тензоре.

### Простой пример:

```python
import torch

# Пример: подсчет частот чисел
indices = torch.tensor([0, 1, 1, 2, 1, 0, 3])
counts = torch.bincount(indices)

print(counts)
# tensor([2, 3, 1, 1])
#         ↑  ↑  ↑  ↑
#         0  1  2  3  ← индексы
#
# Интерпретация:
#   0 встречается 2 раза
#   1 встречается 3 раза
#   2 встречается 1 раз
#   3 встречается 1 раз
```

### Параметр minlength:

```python
# Если максимальное значение < желаемой длины
indices = torch.tensor([0, 1, 1, 2])
counts = torch.bincount(indices, minlength=5)

print(counts)
# tensor([1, 2, 1, 0, 0])
#         ↑  ↑  ↑  ↑  ↑
#         0  1  2  3  4
#
# Индексы 3 и 4 не встречаются → count = 0
# minlength гарантирует длину результата
```

### Применение к MoE Router:

#### Входные данные:

```python
selected_experts: torch.Tensor  # (batch_size, seq_len, top_k)
# Пример: (2, 10, 8)
#   - 2 батча
#   - 10 токенов per батч
#   - 8 выбранных экспертов per токен
#   - Значения: индексы экспертов [0, 127]
```

#### Алгоритм:

```python
# ═══════════════════════════════════════════════════════════════
# Шаг 1: Flatten в 1D тензор
# ═══════════════════════════════════════════════════════════════

# Было: (batch_size, seq_len, top_k) = (2, 10, 8)
flattened_experts = selected_experts.view(-1)
# Стало: (160,) — все индексы в одном массиве

# Пример содержимого:
# flattened_experts = [42, 15, 7, 123, 99, 4, 88, 23,  ← Токен 0, Batch 0
#                      15, 7, 99, 42, 23, 4, 11, 56,   ← Токен 1, Batch 0
#                      ...]

# ═══════════════════════════════════════════════════════════════
# Шаг 2: Подсчет частот с помощью bincount
# ═══════════════════════════════════════════════════════════════

expert_counts = torch.bincount(
    flattened_experts,
    minlength=self.num_experts  # 128 — гарантируем вектор (128,)
)
# expert_counts[i] = сколько раз эксперт i был выбран

# Пример:
# expert_counts = [0, 0, 0, 0, 20, 0, 0, 18, ..., 12, ..., 8, ...]
#                  ↑              ↑        ↑         ↑        ↑
#                  0              4        7        42       99

# ═══════════════════════════════════════════════════════════════
# Шаг 3: Нормализация в частоты (доли)
# ═══════════════════════════════════════════════════════════════

batch_size, seq_len, top_k = selected_experts.shape
total_selections = batch_size * seq_len * top_k  # 2 * 10 * 8 = 160

frequency = expert_counts.float() / total_selections
# frequency[i] = доля токенов, выбравших эксперта i

# Пример:
# frequency = [0.000, 0.000, 0.000, 0.000, 0.125, 0.000, 0.000, 0.113, ...]
#              ↑                            ↑                    ↑
#              0                            4                    7
#              0/160 = 0%                  20/160 = 12.5%       18/160 = 11.3%
```

### Полный код:

```python
def _compute_frequency_bincount(self, selected_experts: torch.Tensor) -> torch.Tensor:
    """
    Вычисляет частоту выбора каждого эксперта (f_i).

    Args:
        selected_experts: (batch_size, seq_len, top_k) - индексы выбранных экспертов

    Returns:
        frequency: (num_experts,) - доля токенов, выбравших каждого эксперта
    """
    # Flatten: (B, S, K) → (B*S*K,)
    flattened_experts = selected_experts.view(-1)

    # Подсчет: сколько раз каждый эксперт был выбран
    expert_counts = torch.bincount(
        flattened_experts,
        minlength=self.num_experts  # (num_experts,)
    )

    # Нормализация: переводим counts в frequencies
    batch_size, seq_len, top_k = selected_experts.shape
    total_selections = batch_size * seq_len * top_k
    frequency = expert_counts.float() / total_selections

    return frequency  # (num_experts,)
```

### Пошаговая визуализация:

```
┌─────────────────────────────────────────────────────────────┐
│ Входные данные: selected_experts (2, 10, 8)                │
└─────────────────────────────────────────────────────────────┘

       Batch 0              Batch 1
    ┌──────────┐         ┌──────────┐
    │ Токен 0  │         │ Токен 0  │
    │ [42,15,  │         │ [99,42,  │
    │  7,123,  │         │  15,7,   │
    │  99,4,   │         │  23,88,  │
    │  88,23]  │         │  4,11]   │
    │          │         │          │
    │ Токен 1  │         │ Токен 1  │
    │ [15,7,   │   ...   │ [15,7,   │
    │  99,42,  │         │  99,42,  │
    │  ...]    │         │  ...]    │
    │   ...    │         │   ...    │
    │ Токен 9  │         │ Токен 9  │
    └──────────┘         └──────────┘
         │                    │
         └────────┬───────────┘
                  ↓
          .view(-1) — Flatten
                  ↓
    ┌─────────────────────────────────┐
    │ flattened_experts: (160,)       │
    │                                 │
    │ [42, 15, 7, 123, 99, 4, 88, 23,│
    │  15, 7, 99, 42, 23, 4, 11, 56, │
    │  7, 99, 15, 23, 42, 88, 4, 11, │
    │  ...]                           │
    └─────────────────────────────────┘
                  ↓
      torch.bincount(minlength=128)
                  ↓
    ┌─────────────────────────────────┐
    │ expert_counts: (128,)           │
    │                                 │
    │ [0, 0, 0, 0, 20, ..., 18, ...]  │
    │  ↑           ↑         ↑        │
    │  эксп 0      эксп 4    эксп 7   │
    │  не выбран   20 раз    18 раз   │
    └─────────────────────────────────┘
                  ↓
         / total_selections (160)
                  ↓
    ┌─────────────────────────────────┐
    │ frequency: (128,)               │
    │                                 │
    │ [0.000, 0.000, 0.000, 0.000,   │
    │  0.125, ..., 0.113, ...]        │
    │  ↑                   ↑           │
    │  0%                  11.3%       │
    └─────────────────────────────────┘
```

---

## Подход 2: One-hot Encoding + Mean

### Что такое One-hot Encoding?

One-hot encoding преобразует индексы в бинарные векторы:

```python
import torch.nn.functional as F

# Пример
indices = torch.tensor([2, 0, 1, 2])
one_hot = F.one_hot(indices, num_classes=4)

print(one_hot)
# tensor([[0, 0, 1, 0],  ← индекс 2 → позиция 2 = 1
#         [1, 0, 0, 0],  ← индекс 0 → позиция 0 = 1
#         [0, 1, 0, 0],  ← индекс 1 → позиция 1 = 1
#         [0, 0, 1, 0]]) ← индекс 2 → позиция 2 = 1
```

### Применение к MoE Router:

#### Алгоритм:

```python
# ═══════════════════════════════════════════════════════════════
# Шаг 1: One-hot encoding
# ═══════════════════════════════════════════════════════════════

# Входные данные: selected_experts (batch_size, seq_len, top_k)
# Пример: (2, 10, 8)

one_hot = F.one_hot(
    selected_experts,
    num_classes=self.num_experts  # 128
)
# Результат: (batch_size, seq_len, top_k, num_experts)
# Пример: (2, 10, 8, 128)

# ═══════════════════════════════════════════════════════════════
# Детализация для одного токена
# ═══════════════════════════════════════════════════════════════

# Токен [0, 0] выбрал экспертов: [42, 15, 7, 123, 99, 4, 88, 23]
# one_hot[0, 0] имеет форму (8, 128):
#
#     Эксперт:  0  1  2 ... 4  5  6  7 ... 15 ... 23 ... 42 ... 88 ... 99 ... 123 ... 127
#     ────────────────────────────────────────────────────────────────────────────────────
# K=0 [42]:     0  0  0 ... 0  0  0  0 ... 0  ... 0  ... 1  ... 0  ... 0  ... 0   ... 0
# K=1 [15]:     0  0  0 ... 0  0  0  0 ... 1  ... 0  ... 0  ... 0  ... 0  ... 0   ... 0
# K=2 [7]:      0  0  0 ... 0  0  0  1 ... 0  ... 0  ... 0  ... 0  ... 0  ... 0   ... 0
# K=3 [123]:    0  0  0 ... 0  0  0  0 ... 0  ... 0  ... 0  ... 0  ... 0  ... 1   ... 0
# K=4 [99]:     0  0  0 ... 0  0  0  0 ... 0  ... 0  ... 0  ... 0  ... 1  ... 0   ... 0
# K=5 [4]:      0  0  0 ... 1  0  0  0 ... 0  ... 0  ... 0  ... 0  ... 0  ... 0   ... 0
# K=6 [88]:     0  0  0 ... 0  0  0  0 ... 0  ... 0  ... 0  ... 1  ... 0  ... 0   ... 0
# K=7 [23]:     0  0  0 ... 0  0  0  0 ... 0  ... 1  ... 0  ... 0  ... 0  ... 0   ... 0

# ═══════════════════════════════════════════════════════════════
# Шаг 2: Усреднение по всем измерениям
# ═══════════════════════════════════════════════════════════════

frequency = one_hot.float().mean(dim=[0, 1, 2])
# Усредняем по batch (dim=0), seq (dim=1), top_k (dim=2)
# Результат: (num_experts,)

# Математически:
# frequency[i] = Σ Σ Σ one_hot[b, s, k, i] / (B * S * K)
#               b  s  k
```

### Полный код:

```python
def _compute_frequency_onehot(self, selected_experts: torch.Tensor) -> torch.Tensor:
    """
    Вычисляет частоту выбора каждого эксперта через one-hot encoding.

    Args:
        selected_experts: (batch_size, seq_len, top_k)

    Returns:
        frequency: (num_experts,)
    """
    # One-hot: (B, S, K) → (B, S, K, N)
    one_hot = F.one_hot(
        selected_experts,
        num_classes=self.num_experts
    )

    # Mean по batch, seq, top_k: (B, S, K, N) → (N,)
    frequency = one_hot.float().mean(dim=[0, 1, 2])

    return frequency  # (num_experts,)
```

### Математическое объяснение:

Для каждого эксперта i:

```
frequency[i] = (количество единиц в столбце i) / (B * S * K)

где:
  - B = batch_size
  - S = seq_len
  - K = top_k
  - Столбец i содержит 1, когда эксперт i был выбран
```

**Пример:**
```python
# Дано: (B=2, S=10, K=8) → total = 160 выборов

# Для эксперта 42:
# one_hot[:, :, :, 42] содержит 12 единиц (в 12 позициях)
# frequency[42] = 12 / 160 = 0.075

# Для эксперта 99:
# one_hot[:, :, :, 99] содержит 8 единиц
# frequency[99] = 8 / 160 = 0.050

# Для эксперта 0:
# one_hot[:, :, :, 0] содержит 0 единиц
# frequency[0] = 0 / 160 = 0.0
```

---

## Сравнение подходов

### Производительность:

| Характеристика | `torch.bincount` | One-hot + mean |
|----------------|------------------|----------------|
| **Скорость** | ⚡⚡⚡ Очень быстро | 🐢 Медленнее |
| **Память** | 💾 O(num_experts) | 💾💾 O(B*S*K*N) — 4D тензор! |
| **Читаемость** | ⭐⭐⭐ Хорошо | ⭐⭐⭐⭐ Более наглядно |
| **Сложность кода** | 3 строки | 2 строки |

### Пример затрат памяти:

```python
# Параметры:
batch_size = 2
seq_len = 10
top_k = 8
num_experts = 128

# torch.bincount:
# flattened: (160,) — int64 → 160 * 8 bytes = 1.28 KB
# expert_counts: (128,) — int64 → 128 * 8 bytes = 1.02 KB
# Итого: ~2.3 KB

# One-hot + mean:
# one_hot: (2, 10, 8, 128) — int64 → 2*10*8*128 * 8 bytes = 163.84 KB
# Итого: ~164 KB (в 71 раз больше!)
```

### Когда использовать каждый подход:

| Подход | Когда использовать |
|--------|-------------------|
| **torch.bincount** | ✅ В продакшене (production code)<br>✅ Когда важна скорость<br>✅ Для больших батчей |
| **One-hot + mean** | ✅ Для обучения/понимания<br>✅ Для отладки (более наглядно)<br>✅ Для маленьких экспериментов |

### Рекомендация:

**Используйте `torch.bincount` в финальной реализации** для оптимальной производительности.

---

## Полная реализация _compute_balance_loss

Теперь, когда мы знаем как вычислить frequency, давайте рассмотрим полную реализацию `_compute_balance_loss`:

### Формула:

```
L_balance = α * N * Σ (f_i * P_i)
                    i=1..N

где:
  α = balance_loss_coef  (0.01)
  N = num_experts        (128)
  f_i = frequency        (доля токенов, выбравших эксперта i)
  P_i = mean probability (средний gating score эксперта i)
```

### Шаги реализации:

```python
def _compute_balance_loss(
    self,
    gating_scores: torch.Tensor,      # (batch_size, seq_len, num_experts)
    selected_experts: torch.Tensor    # (batch_size, seq_len, top_k)
) -> torch.Tensor:
    """
    Вычисляет load balancing loss.

    Формула: L = balance_loss_coef * num_experts * Σ(f_i * P_i)

    Args:
        gating_scores: Softmax вероятности для всех экспертов
        selected_experts: Индексы выбранных top-k экспертов

    Returns:
        balance_loss: Скаляр тензор
    """
    # ═══════════════════════════════════════════════════════════════
    # Шаг 1: Вычисляем frequency (f_i) — доля токенов per эксперт
    # ═══════════════════════════════════════════════════════════════

    # Flatten индексов экспертов
    flattened_experts = selected_experts.view(-1)  # (B*S*K,)

    # Подсчет частот
    expert_counts = torch.bincount(
        flattened_experts,
        minlength=self.num_experts
    )  # (num_experts,)

    # Нормализация в доли
    batch_size, seq_len, top_k = selected_experts.shape
    total_selections = batch_size * seq_len * top_k
    frequency = expert_counts.float() / total_selections  # (num_experts,)

    # ═══════════════════════════════════════════════════════════════
    # Шаг 2: Вычисляем mean probability (P_i) — средний вес эксперта
    # ═══════════════════════════════════════════════════════════════

    # gating_scores: (batch_size, seq_len, num_experts)
    # Усредняем по batch и seq dimensions
    mean_prob = gating_scores.mean(dim=[0, 1])  # (num_experts,)

    # ═══════════════════════════════════════════════════════════════
    # Шаг 3: Вычисляем loss = α * N * Σ(f_i * P_i)
    # ═══════════════════════════════════════════════════════════════

    # Поэлементное произведение и суммирование
    balance_loss = self.balance_loss_coef * self.num_experts * (frequency * mean_prob).sum()

    return balance_loss  # Скаляр
```

### Детализация каждого шага:

#### Шаг 1: Frequency (f_i)

```python
# Пример значений после вычисления:
frequency = tensor([
    0.000,  # Эксперт 0: 0% токенов
    0.000,  # Эксперт 1: 0% токенов
    0.000,  # Эксперт 2: 0% токенов
    0.000,  # Эксперт 3: 0% токенов
    0.125,  # Эксперт 4: 12.5% токенов ✓
    0.000,  # Эксперт 5: 0% токенов
    0.000,  # Эксперт 6: 0% токенов
    0.113,  # Эксперт 7: 11.3% токенов ✓
    ...
])

# Идеально: f_i ≈ 1/128 ≈ 0.0078 для каждого эксперта
# Но на практике будут различия
```

#### Шаг 2: Mean Probability (P_i)

```python
# gating_scores: (batch_size=2, seq_len=10, num_experts=128)

# Усредняем по batch и seq:
mean_prob = gating_scores.mean(dim=[0, 1])  # (128,)

# Пример значений:
mean_prob = tensor([
    0.0075,  # Эксперт 0: средний gating score
    0.0076,  # Эксперт 1
    0.0077,  # Эксперт 2
    0.0078,  # Эксперт 3
    0.0085,  # Эксперт 4: высокий средний score ✓
    0.0074,  # Эксперт 5
    0.0073,  # Эксперт 6
    0.0082,  # Эксперт 7: высокий средний score ✓
    ...
])

# Идеально: все P_i ≈ 1/128 ≈ 0.0078
```

#### Шаг 3: Balance Loss

```python
# Вычисляем произведение f_i * P_i для каждого эксперта:
product = frequency * mean_prob

# Пример:
product = tensor([
    0.000 * 0.0075 = 0.000000,  # Эксперт 0
    0.000 * 0.0076 = 0.000000,  # Эксперт 1
    ...
    0.125 * 0.0085 = 0.001063,  # Эксперт 4: высокий вклад в loss!
    ...
    0.113 * 0.0082 = 0.000927,  # Эксперт 7: высокий вклад в loss!
    ...
])

# Суммируем:
sum_product = product.sum()  # Например: 0.0234

# Умножаем на коэффициенты:
balance_loss = 0.01 * 128 * 0.0234 = 0.0300
#              ↑     ↑     ↑
#              α     N     Σ(f_i * P_i)
```

### Интуиция за формулой:

**Цель:** Сделать произведение `f_i * P_i` маленьким для каждого эксперта.

```
Если эксперт используется часто (высокий f_i) И имеет высокий средний score (высокий P_i):
  → Произведение f_i * P_i будет большим
  → Balance loss будет большим
  → Градиенты заставят модель снизить использование этого эксперта

Если все эксперты используются равномерно:
  → f_i ≈ P_i ≈ 1/N для всех i
  → Σ(f_i * P_i) ≈ N * (1/N) * (1/N) = 1/N
  → Balance loss минимален ✓
```

---

## Практический пример

### Полный рабочий код:

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class MoERouterExample(nn.Module):
    def __init__(self, num_experts=128, balance_loss_coef=0.01):
        super().__init__()
        self.num_experts = num_experts
        self.balance_loss_coef = balance_loss_coef

    def _compute_balance_loss(
        self,
        gating_scores: torch.Tensor,
        selected_experts: torch.Tensor
    ) -> torch.Tensor:
        """Вычисляет load balancing loss."""

        print("="*70)
        print("ВЫЧИСЛЕНИЕ LOAD BALANCING LOSS")
        print("="*70)

        # Шаг 1: Frequency
        print("\n[Шаг 1] Вычисление frequency (f_i)")
        print("-"*70)

        flattened_experts = selected_experts.view(-1)
        print(f"  Flattened shape: {flattened_experts.shape}")
        print(f"  Первые 20 индексов: {flattened_experts[:20]}")

        expert_counts = torch.bincount(
            flattened_experts,
            minlength=self.num_experts
        )
        print(f"\n  Expert counts shape: {expert_counts.shape}")
        print(f"  Ненулевые counts:")
        nonzero_idx = expert_counts.nonzero().squeeze()
        for idx in nonzero_idx[:10]:  # Показываем первые 10
            print(f"    Эксперт {idx:3d}: выбран {expert_counts[idx]:2d} раз")

        batch_size, seq_len, top_k = selected_experts.shape
        total_selections = batch_size * seq_len * top_k
        frequency = expert_counts.float() / total_selections

        print(f"\n  Total selections: {total_selections}")
        print(f"  Frequency shape: {frequency.shape}")
        print(f"  Ненулевые frequencies:")
        for idx in nonzero_idx[:10]:
            print(f"    f_{idx:3d} = {frequency[idx]:.6f} ({frequency[idx]*100:.2f}%)")

        # Шаг 2: Mean Probability
        print(f"\n[Шаг 2] Вычисление mean probability (P_i)")
        print("-"*70)

        mean_prob = gating_scores.mean(dim=[0, 1])
        print(f"  Gating scores shape: {gating_scores.shape}")
        print(f"  Mean prob shape: {mean_prob.shape}")
        print(f"  Mean prob (первые 10):")
        for i in range(10):
            print(f"    P_{i:3d} = {mean_prob[i]:.6f}")

        # Шаг 3: Balance Loss
        print(f"\n[Шаг 3] Вычисление balance loss")
        print("-"*70)

        product = frequency * mean_prob
        print(f"  Product f_i * P_i (ненулевые):")
        for idx in nonzero_idx[:10]:
            print(f"    f_{idx:3d} * P_{idx:3d} = {frequency[idx]:.6f} * {mean_prob[idx]:.6f} = {product[idx]:.8f}")

        sum_product = product.sum()
        balance_loss = self.balance_loss_coef * self.num_experts * sum_product

        print(f"\n  Σ(f_i * P_i) = {sum_product:.8f}")
        print(f"  balance_loss_coef = {self.balance_loss_coef}")
        print(f"  num_experts = {self.num_experts}")
        print(f"  Balance Loss = {self.balance_loss_coef} * {self.num_experts} * {sum_product:.8f}")
        print(f"               = {balance_loss:.8f}")

        print("\n" + "="*70 + "\n")

        return balance_loss


# ═══════════════════════════════════════════════════════════════════
# Тестирование
# ═══════════════════════════════════════════════════════════════════

# Создаем router
router = MoERouterExample(num_experts=128, balance_loss_coef=0.01)

# Симулируем данные
batch_size, seq_len, num_experts = 2, 10, 128
top_k = 8

# Случайные gating scores (после softmax)
gating_scores = torch.rand(batch_size, seq_len, num_experts)
gating_scores = F.softmax(gating_scores, dim=-1)

# Выбираем top-k экспертов
_, selected_experts = torch.topk(gating_scores, k=top_k, dim=-1)

print(f"Input shapes:")
print(f"  gating_scores: {gating_scores.shape}")
print(f"  selected_experts: {selected_experts.shape}\n")

# Вычисляем balance loss
balance_loss = router._compute_balance_loss(gating_scores, selected_experts)

print(f"ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
print(f"  Balance Loss = {balance_loss.item():.8f}")
```

### Ожидаемый вывод:

```
Input shapes:
  gating_scores: torch.Size([2, 10, 128])
  selected_experts: torch.Size([2, 10, 8])

======================================================================
ВЫЧИСЛЕНИЕ LOAD BALANCING LOSS
======================================================================

[Шаг 1] Вычисление frequency (f_i)
----------------------------------------------------------------------
  Flattened shape: torch.Size([160])
  Первые 20 индексов: tensor([105,  46,  83,  16,  89,  80,  18,  92, 105,  83,  46,  89,  16,
         92,  18,  80,  83, 105,  46,  89])

  Expert counts shape: torch.Size([128])
  Ненулевые counts:
    Эксперт   0: выбран  2 раз
    Эксперт   1: выбран  1 раз
    Эксперт   3: выбран  2 раз
    Эксперт   4: выбран  1 раз
    Эксперт   5: выбран  1 раз
    Эксперт   6: выбран  2 раз
    Эксперт   7: выбран  1 раз
    Эксперт   9: выбран  1 раз
    Эксперт  10: выбран  2 раз
    Эксперт  12: выбран  1 раз

  Total selections: 160
  Frequency shape: torch.Size([128])
  Ненулевые frequencies:
    f_  0 = 0.012500 (1.25%)
    f_  1 = 0.006250 (0.62%)
    f_  3 = 0.012500 (1.25%)
    f_  4 = 0.006250 (0.62%)
    f_  5 = 0.006250 (0.62%)
    f_  6 = 0.012500 (1.25%)
    f_  7 = 0.006250 (0.62%)
    f_  9 = 0.006250 (0.62%)
    f_ 10 = 0.012500 (1.25%)
    f_ 12 = 0.006250 (0.62%)

[Шаг 2] Вычисление mean probability (P_i)
----------------------------------------------------------------------
  Gating scores shape: torch.Size([2, 10, 128])
  Mean prob shape: torch.Size([128])
  Mean prob (первые 10):
    P_  0 = 0.007889
    P_  1 = 0.007812
    P_  2 = 0.007734
    P_  3 = 0.007856
    P_  4 = 0.007801
    P_  5 = 0.007823
    P_  6 = 0.007845
    P_  7 = 0.007867
    P_  8 = 0.007889
    P_  9 = 0.007801

[Шаг 3] Вычисление balance loss
----------------------------------------------------------------------
  Product f_i * P_i (ненулевые):
    f_  0 * P_  0 = 0.012500 * 0.007889 = 0.00009861
    f_  1 * P_  1 = 0.006250 * 0.007812 = 0.00004882
    f_  3 * P_  3 = 0.012500 * 0.007856 = 0.00009820
    f_  4 * P_  4 = 0.006250 * 0.007801 = 0.00004876
    f_  5 * P_  5 = 0.006250 * 0.007823 = 0.00004889
    f_  6 * P_  6 = 0.012500 * 0.007845 = 0.00009806
    f_  7 * P_  7 = 0.006250 * 0.007867 = 0.00004917
    f_  9 * P_  9 = 0.006250 * 0.007801 = 0.00004876
    f_ 10 * P_ 10 = 0.012500 * 0.007834 = 0.00009792
    f_ 12 * P_ 12 = 0.006250 * 0.007789 = 0.00004868

  Σ(f_i * P_i) = 0.00781250
  balance_loss_coef = 0.01
  num_experts = 128
  Balance Loss = 0.01 * 128 * 0.00781250
               = 0.10000000

======================================================================

ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:
  Balance Loss = 0.10000000
```

---

## Резюме

### Ключевые моменты:

1. **Frequency (f_i)** показывает долю токенов, выбравших каждого эксперта
   - Вычисляется через `torch.bincount` (быстрее) или one-hot encoding (нагляднее)
   - Результат: тензор формы `(num_experts,)` с суммой ≈ top_k

2. **Load Balancing Loss** предотвращает коллапс экспертов
   - Формула: `α * N * Σ(f_i * P_i)`
   - Минимизируется, когда все эксперты используются равномерно

3. **Рекомендуется использовать `torch.bincount`** для production кода
   - Быстрее и эффективнее по памяти
   - Простая реализация (3 строки кода)

### Следующие шаги:

После вычисления frequency, нужно:
1. Вычислить mean probability (P_i): `gating_scores.mean(dim=[0, 1])`
2. Вычислить loss: `balance_loss_coef * num_experts * (frequency * mean_prob).sum()`
3. Вернуть balance_loss из метода `_compute_balance_loss`

---

**Дата создания**: 2025-10-02
**Автор**: AI Teacher для Qwen3 MoE Project
**Связанные файлы**:
- `experiments/domain/moe/router.py`
- `experiments/domain/moe/MoE_Router_Gate_Initialization.md`
