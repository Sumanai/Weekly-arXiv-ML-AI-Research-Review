# 📚 nn.ModuleList: Полное руководство для MoE Layer

> **Образовательный материал**: Глубокое погружение в работу `nn.ModuleList` на примере Mixture-of-Experts архитектуры.

---

## 🎯 Содержание

1. [Введение](#введение)
2. [Проблема: Почему обычный список не работает?](#проблема-почему-обычный-список-не-работает)
3. [Решение: nn.ModuleList](#решение-nnmodulelist)
4. [Пошаговое объяснение конструкции](#пошаговое-объяснение-конструкции)
5. [Визуализация в памяти](#визуализация-в-памяти)
6. [Использование в forward()](#использование-в-forward)
7. [Контрольные вопросы](#контрольные-вопросы)
8. [Практические примеры](#практические-примеры)
9. [Сравнение с другими контейнерами](#сравнение-с-другими-контейнерами)
10. [Частые ошибки и решения](#частые-ошибки-и-решения)
11. [Ссылки и ресурсы](#ссылки-и-ресурсы)

---

## Введение

В архитектуре **Mixture-of-Experts (MoE)** мы используем **несколько параллельных нейронных сетей** (экспертов), которые обрабатывают разные части входных данных. Для хранения этих экспертов в PyTorch нужен специальный контейнер — **`nn.ModuleList`**.

### Ключевой вопрос
**Зачем нужен `nn.ModuleList`, если в Python уже есть обычный `list`?**

Ответ: PyTorch должен **отслеживать параметры** всех экспертов для:
- Вычисления градиентов
- Переноса на GPU/CPU
- Сохранения/загрузки модели
- Применения оптимизатора

Обычный Python список этого **не обеспечивает**.

---

## Проблема: Почему обычный список не работает?

### ❌ Неправильный подход

```python
class BrokenMoELayer(nn.Module):
    def __init__(self, hidden_size=512, num_experts=8):
        super().__init__()

        # ⚠️ ОШИБКА: Обычный Python список!
        self.experts = [
            Expert(hidden_size, intermediate_size=2048)
            for _ in range(num_experts)
        ]
```

### Что пойдёт не так?

#### 1. **Параметры не регистрируются**
```python
moe = BrokenMoELayer()
print(list(moe.parameters()))  # ❌ Пустой список! Эксперты не видны PyTorch
```

#### 2. **Градиенты не распространяются**
```python
output = moe(x)
loss = output.sum()
loss.backward()  # ❌ Градиенты к экспертам НЕ дойдут!
```

#### 3. **Модель не переносится на GPU**
```python
moe = moe.to('cuda')  # ❌ Эксперты остаются на CPU!
x = x.to('cuda')
output = moe(x)  # 💥 RuntimeError: Input and weight are on different devices
```

#### 4. **Сохранение/загрузка не работает**
```python
torch.save(moe.state_dict(), 'model.pt')  # ❌ Веса экспертов НЕ сохранятся!
```

### 🔍 Почему так происходит?

PyTorch **автоматически регистрирует** только те атрибуты, которые являются:
- `nn.Module` (один модуль)
- `nn.ModuleList` (список модулей)
- `nn.ModuleDict` (словарь модулей)
- `nn.Sequential` (последовательность модулей)

Обычный Python `list` — это **не PyTorch контейнер**, поэтому он игнорируется.

---

## Решение: nn.ModuleList

### ✅ Правильный подход

```python
class SimpleMoELayer(nn.Module):
    def __init__(self, hidden_size=512, num_experts=8):
        super().__init__()

        # ✅ ПРАВИЛЬНО: nn.ModuleList!
        self.experts = nn.ModuleList([
            Expert(hidden_size, intermediate_size=2048)
            for _ in range(num_experts)
        ])
```

### Что это даёт?

#### 1. **Параметры видны PyTorch**
```python
moe = SimpleMoELayer()
print(len(list(moe.parameters())))  # ✅ Все параметры Router + 8 экспертов
```

#### 2. **Градиенты распространяются корректно**
```python
output = moe(x)
loss = output.sum()
loss.backward()  # ✅ Градиенты доходят до всех 8 экспертов!

for expert in moe.experts:
    print(expert.ffn.w1.grad)  # ✅ Градиенты есть!
```

#### 3. **Модель переносится на GPU целиком**
```python
moe = moe.to('cuda')  # ✅ Все 8 экспертов переносятся на GPU
x = x.to('cuda')
output = moe(x)  # ✅ Работает корректно
```

#### 4. **Сохранение/загрузка работает**
```python
torch.save(moe.state_dict(), 'model.pt')  # ✅ Все веса сохраняются
moe.load_state_dict(torch.load('model.pt'))  # ✅ Загрузка работает
```

---

## Пошаговое объяснение конструкции

Разберём построчно код из `SimpleMoELayer`:

```python
self.experts = nn.ModuleList([
    Expert(hidden_size, intermediate_size, expert_dropout)
    for _ in range(num_experts)
])
```

### Шаг 1: List Comprehension (внутренняя часть)

```python
[Expert(hidden_size, intermediate_size, expert_dropout) for _ in range(num_experts)]
```

**Что происходит:**
1. `range(num_experts)` → `[0, 1, 2, 3, 4, 5, 6, 7]` (для 8 экспертов)
2. `for _ in range(...)` — цикл; `_` означает "итератор не используется"
3. `Expert(...)` создаётся **8 раз** с одинаковыми параметрами
4. Результат: **Python список** из 8 объектов `Expert`

**Эквивалентный код без list comprehension:**

```python
experts_list = []
for i in range(8):
    expert = Expert(
        hidden_size=512,
        intermediate_size=2048,
        dropout=0.0
    )
    experts_list.append(expert)
# experts_list = [Expert₀, Expert₁, Expert₂, ..., Expert₇]
```

### Шаг 2: Обёртка в nn.ModuleList

```python
self.experts = nn.ModuleList([...])
```

**Что делает `nn.ModuleList`:**
1. Принимает Python список модулей
2. **Регистрирует** каждый модуль как подмодуль
3. Возвращает специальный контейнер, который:
   - Поддерживает индексацию: `self.experts[3]`
   - Поддерживает итерацию: `for expert in self.experts`
   - Поддерживает `len()`: `len(self.experts)`
   - **НЕ поддерживает** `.append()` после инициализации (только чтение)

### Шаг 3: Важные детали

#### Каждый эксперт инициализируется **независимо**

```python
# Все эксперты имеют РАЗНЫЕ веса!
moe = SimpleMoELayer(hidden_size=512, num_experts=8)

expert_0_weight = moe.experts[0].ffn.w1.weight
expert_1_weight = moe.experts[1].ffn.w1.weight

print(torch.allclose(expert_0_weight, expert_1_weight))  # ✅ False — веса разные!
```

**Почему?** Каждый `Expert(...)` вызывает свою инициализацию весов (Xavier, Kaiming и т.д.).

#### Эксперты имеют одинаковую **архитектуру**, но разные **параметры**

```
Архитектура (одинакова):
  Expert → SwiGLU(512, 2048, 512) → Dropout(0.0)

Параметры (разные):
  Expert₀: w1, w2, w3 инициализированы случайно
  Expert₁: w1, w2, w3 инициализированы случайно (другие значения!)
  ...
```

---

## Визуализация в памяти

### Структура SimpleMoELayer

```
SimpleMoELayer (nn.Module)
│
├── self.hidden_size = 512              # Обычный атрибут (int)
├── self.num_experts = 8                # Обычный атрибут (int)
├── self.top_k = 2                      # Обычный атрибут (int)
│
├── self.router ─────────────┐          # Зарегистрированный подмодуль
│                            │
│                            ├─→ MoERouter (nn.Module)
│                            │   ├── gate: nn.Linear(512, 8)
│                            │   │   ├── weight: Tensor(8, 512)
│                            │   │   └── bias: Tensor(8)
│                            │   └── параметры: 4104
│                            │
└── self.experts ────────────┐          # Зарегистрированный подмодуль (контейнер)
                             │
                             ├─→ nn.ModuleList
                             │   │
                             │   ├── [0] Expert₀ (nn.Module)
                             │   │   ├── ffn: SwiGLU
                             │   │   │   ├── w1: nn.Linear(512, 2048)
                             │   │   │   ├── w2: nn.Linear(512, 2048)
                             │   │   │   └── w3: nn.Linear(2048, 512)
                             │   │   └── dropout: nn.Dropout(0.0)
                             │   │
                             │   ├── [1] Expert₁ (nn.Module)
                             │   │   └── ... (та же архитектура, другие веса)
                             │   │
                             │   ├── [2] Expert₂ (nn.Module)
                             │   ⋮
                             │   └── [7] Expert₇ (nn.Module)
                             │       └── ... (та же архитектура, другие веса)
                             │
                             └── Общее количество параметров в экспертах: ~8.4M
```

### Что видит PyTorch при вызове `.parameters()`?

```python
moe = SimpleMoELayer(hidden_size=512, num_experts=8)

for name, param in moe.named_parameters():
    print(name, param.shape)

# Вывод:
# router.gate.weight          torch.Size([8, 512])
# router.gate.bias            torch.Size([8])
# experts.0.ffn.w1.weight     torch.Size([2048, 512])
# experts.0.ffn.w1.bias       torch.Size([2048])
# experts.0.ffn.w2.weight     torch.Size([2048, 512])
# experts.0.ffn.w2.bias       torch.Size([2048])
# experts.0.ffn.w3.weight     torch.Size([512, 2048])
# experts.0.ffn.w3.bias       torch.Size([512])
# experts.1.ffn.w1.weight     torch.Size([2048, 512])
# experts.1.ffn.w1.bias       torch.Size([2048])
# ... (аналогично для Expert₂...Expert₇)
```

**Обратите внимание:**
- Имена параметров включают префикс `experts.0`, `experts.1` и т.д.
- Это автоматическая нумерация от `nn.ModuleList`
- PyTorch **видит все параметры** благодаря регистрации

---

## Использование в forward()

### Как Router выбирает экспертов

```python
def forward(self, hidden_states, training=True):
    # Шаг 1: Router выбирает top_k экспертов для каждого токена
    routing_weights, selected_experts, balance_loss = self.router(hidden_states, training)

    # routing_weights: (batch_size, seq_len, top_k=2)
    #   Пример для токена [0, 0]: [0.7, 0.3] — веса для двух экспертов

    # selected_experts: (batch_size, seq_len, top_k=2) dtype=long
    #   Пример для токена [0, 0]: [2, 5] — индексы экспертов (Expert₂ и Expert₅)
```

### Как обрабатываются токены

```python
    # Шаг 2: Обработка каждого токена выбранными экспертами
    batch_size, seq_len, hidden_size = hidden_states.shape
    output = torch.zeros_like(hidden_states)  # (batch_size, seq_len, hidden_size)

    for b in range(batch_size):
        for s in range(seq_len):
            token = hidden_states[b, s:s+1, :]  # (1, 1, hidden_size) — ВАЖНО: s:s+1!
            token_output = torch.zeros(1, 1, hidden_size)

            # Для каждого из top_k=2 экспертов
            for k in range(self.top_k):
                # Получаем индекс эксперта (0-7)
                expert_idx = selected_experts[b, s, k].item()  # int: 0, 1, 2, ..., 7

                # Получаем вес (0.0-1.0)
                weight = routing_weights[b, s, k].item()  # float: 0.7, 0.3, ...

                # Получаем эксперт из ModuleList по индексу
                expert = self.experts[expert_idx]  # ✅ Индексация как в обычном списке!

                # Обрабатываем токен экспертом
                expert_output = expert(token)  # (1, 1, hidden_size)

                # Взвешенное суммирование
                token_output += weight * expert_output

            # Сохраняем результат
            output[b, s, :] = token_output.squeeze()  # (hidden_size,)

    # Шаг 3: Residual connection
    output = output + hidden_states

    return output, balance_loss
```

### Ключевые моменты

#### 1. **Индексация `self.experts[expert_idx]`**

```python
expert_idx = 5  # Router выбрал Expert₅
expert = self.experts[expert_idx]  # Получаем Expert₅

# nn.ModuleList поддерживает индексацию как обычный список:
self.experts[0]  # Expert₀
self.experts[7]  # Expert₇
```

#### 2. **Почему `.item()` для индекса?**

```python
expert_idx = selected_experts[b, s, k].item()  # Tensor(5) → int(5)
```

**Причина:** `selected_experts[b, s, k]` — это **0-мерный тензор** (скаляр), а для индексации нужен **Python int**.

```python
# ❌ Не работает:
expert = self.experts[selected_experts[b, s, k]]  # TypeError!

# ✅ Работает:
expert = self.experts[selected_experts[b, s, k].item()]  # int → индекс
```

#### 3. **Почему `s:s+1`, а не `s`?**

```python
token = hidden_states[b, s:s+1, :]  # ✅ (1, 1, 512) — сохраняет размерность seq
# vs
token = hidden_states[b, s, :]      # ❌ (512,) — теряет размерность seq
```

**Причина:** Expert ожидает вход формы `(batch, seq, hidden)`. Если использовать `[b, s, :]`, получим форму `(hidden,)`, что сломает forward pass.

---

## Контрольные вопросы

Проверьте своё понимание:

### Вопрос 1
**Что вернёт `len(self.experts)`?**

<details>
<summary>Ответ</summary>

`8` — количество экспертов в `nn.ModuleList`.

```python
moe = SimpleMoELayer(num_experts=8)
print(len(moe.experts))  # 8
```
</details>

---

### Вопрос 2
**Все ли эксперты имеют одинаковые веса после инициализации?**

<details>
<summary>Ответ</summary>

**Нет!** Каждый `Expert` инициализируется **независимо** с разными случайными весами.

```python
expert_0 = moe.experts[0]
expert_1 = moe.experts[1]

# Архитектура одинакова, но веса разные:
print(expert_0.ffn.w1.weight)  # Случайные веса A
print(expert_1.ffn.w1.weight)  # Случайные веса B (≠ A)
```
</details>

---

### Вопрос 3
**Что произойдёт, если заменить `nn.ModuleList` на обычный `list`?**

<details>
<summary>Ответ</summary>

Модель **не будет обучаться**:
- Параметры экспертов не зарегистрируются
- Градиенты не дойдут до экспертов
- `.to(device)` не перенесёт экспертов
- Сохранение/загрузка не будет работать

```python
# ❌ Сломанная версия:
self.experts = [Expert(...) for _ in range(8)]

# При обучении:
optimizer.step()  # Обновятся только параметры Router, эксперты останутся неизменными!
```
</details>

---

### Вопрос 4
**Можно ли обращаться к экспертам по индексу `self.experts[3]`?**

<details>
<summary>Ответ</summary>

**Да!** `nn.ModuleList` поддерживает индексацию как обычный список.

```python
third_expert = moe.experts[3]  # Получаем Expert₃
output = third_expert(x)  # Обрабатываем входные данные
```

Также поддерживаются:
- Итерация: `for expert in moe.experts:`
- Длина: `len(moe.experts)`
- Срезы: `moe.experts[2:5]` (НО это возвращает обычный список, не ModuleList!)
</details>

---

### Вопрос 5
**Можно ли добавлять экспертов в `nn.ModuleList` после инициализации?**

<details>
<summary>Ответ</summary>

**Можно, но НЕ рекомендуется в production.**

```python
# ✅ Работает, но редко используется:
moe.experts.append(Expert(512, 2048))  # Добавляем 9-го эксперта

# ⚠️ Проблема: Router обучен на 8 экспертов, а теперь их 9!
# Индексы 0-7 будут использоваться, а эксперт 8 — нет.
```

**Когда это полезно:**
- Динамическое добавление экспертов во время обучения (редкий кейс)
- Эксперименты с transfer learning

**Обычно:** Количество экспертов фиксировано при инициализации.
</details>

---

## Практические примеры

### Пример 1: Создание и проверка MoE Layer

```python
import torch
from experiments.domain.moe.moe_layer import SimpleMoELayer

# Создание MoE Layer
moe = SimpleMoELayer(
    hidden_size=512,
    num_experts=8,
    top_k=2,
    intermediate_size=2048
)

# Проверка структуры
print(f"Количество экспертов: {len(moe.experts)}")  # 8
print(f"Тип контейнера: {type(moe.experts)}")       # <class 'torch.nn.modules.container.ModuleList'>

# Проверка параметров
total_params = sum(p.numel() for p in moe.parameters())
print(f"Всего параметров: {total_params:,}")

# Проверка отдельного эксперта
expert_0 = moe.experts[0]
print(f"Первый эксперт: {expert_0}")
print(f"Архитектура: {expert_0.ffn}")
```

### Пример 2: Итерация по экспертам

```python
# Итерация по всем экспертам
for idx, expert in enumerate(moe.experts):
    num_params = sum(p.numel() for p in expert.parameters())
    print(f"Expert {idx}: {num_params:,} параметров")

# Вывод:
# Expert 0: 1,050,112 параметров
# Expert 1: 1,050,112 параметров
# Expert 2: 1,050,112 параметров
# ...
# Expert 7: 1,050,112 параметров
```

### Пример 3: Доступ к параметрам конкретного эксперта

```python
# Получаем веса первого эксперта
expert_0 = moe.experts[0]
w1_weight = expert_0.ffn.w1.weight  # (2048, 512)
w1_bias = expert_0.ffn.w1.bias      # (2048,)

print(f"W1 weight shape: {w1_weight.shape}")
print(f"W1 bias shape: {w1_bias.shape}")
print(f"W1 weight sample: {w1_weight[0, :5]}")  # Первые 5 значений
```

### Пример 4: Forward pass с анализом

```python
# Входные данные
x = torch.randn(2, 10, 512)  # (batch=2, seq=10, hidden=512)

# Forward pass
output, balance_loss = moe(x, training=True)

print(f"Input shape:  {x.shape}")        # (2, 10, 512)
print(f"Output shape: {output.shape}")   # (2, 10, 512)
print(f"Balance loss: {balance_loss.item():.6f}")

# Проверка residual connection
# Output ≠ 0, даже если Router обнулил веса
print(f"Output is non-zero: {not torch.allclose(output, torch.zeros_like(output))}")  # True
```

### Пример 5: Перенос на GPU

```python
# Проверка переноса на GPU (если доступен)
if torch.cuda.is_available():
    moe = moe.to('cuda')
    x = x.to('cuda')

    # Проверяем, что все эксперты на GPU
    for idx, expert in enumerate(moe.experts):
        device = next(expert.parameters()).device
        print(f"Expert {idx} на устройстве: {device}")

    # Вывод:
    # Expert 0 на устройстве: cuda:0
    # Expert 1 на устройстве: cuda:0
    # ...
    # Expert 7 на устройстве: cuda:0
```

### Пример 6: Сохранение и загрузка

```python
# Сохранение модели
torch.save(moe.state_dict(), 'moe_layer.pt')
print("Модель сохранена")

# Создание новой модели
moe_new = SimpleMoELayer(hidden_size=512, num_experts=8, top_k=2)

# Загрузка весов
moe_new.load_state_dict(torch.load('moe_layer.pt'))
print("Модель загружена")

# Проверка идентичности
x = torch.randn(1, 5, 512)
out1, _ = moe(x, training=False)
out2, _ = moe_new(x, training=False)

print(f"Выходы идентичны: {torch.allclose(out1, out2)}")  # True
```

---

## Сравнение с другими контейнерами

PyTorch предоставляет несколько контейнеров для модулей:

### nn.ModuleList vs nn.Sequential

| Характеристика | `nn.ModuleList` | `nn.Sequential` |
|----------------|-----------------|-----------------|
| **Порядок выполнения** | Произвольный (вы контролируете) | Строго последовательный |
| **Доступ по индексу** | ✅ Да (`self.experts[3]`) | ✅ Да (`self.layers[2]`) |
| **Автоматический forward** | ❌ Нет (пишете сами) | ✅ Да (последовательно) |
| **Использование** | Параллельные ветви, условная логика | Линейные стеки (ResNet, VGG) |

**Пример nn.Sequential:**
```python
# Линейный стек слоёв
self.layers = nn.Sequential(
    nn.Linear(512, 1024),
    nn.ReLU(),
    nn.Linear(1024, 512)
)

# Forward автоматический:
output = self.layers(x)  # x → Linear → ReLU → Linear
```

**Почему MoE использует ModuleList, а не Sequential?**
- Эксперты работают **параллельно**, а не последовательно
- Каждый токен идёт только к **top_k экспертам**, а не ко всем
- Нужен **произвольный доступ** по индексу: `self.experts[expert_idx]`

---

### nn.ModuleList vs nn.ModuleDict

| Характеристика | `nn.ModuleList` | `nn.ModuleDict` |
|----------------|-----------------|-----------------|
| **Индексация** | По числовому индексу: `[0], [1]` | По строковому ключу: `['encoder'], ['decoder']` |
| **Порядок** | Упорядочен (как список) | Упорядочен (Python 3.7+) |
| **Использование** | Однородные модули (8 экспертов) | Разнородные модули (encoder + decoder) |

**Пример nn.ModuleDict:**
```python
# Словарь разных компонентов
self.components = nn.ModuleDict({
    'encoder': TransformerEncoder(...),
    'decoder': TransformerDecoder(...),
    'head': nn.Linear(512, vocab_size)
})

# Доступ по ключу:
encoded = self.components['encoder'](x)
decoded = self.components['decoder'](encoded)
output = self.components['head'](decoded)
```

**Почему MoE использует ModuleList, а не ModuleDict?**
- Эксперты **однородны** (одинаковая архитектура)
- Индексы **числовые** (0-7), а не семантические ('expert_relu', 'expert_conv')
- Router возвращает **числовые индексы**, удобно для прямого доступа

---

### Сводная таблица

| Сценарий | Контейнер | Пример |
|----------|-----------|--------|
| Линейный стек слоёв | `nn.Sequential` | ResNet block, MLP |
| Параллельные однородные модули | `nn.ModuleList` | MoE experts, multi-head attention |
| Разнородные именованные компоненты | `nn.ModuleDict` | Encoder-Decoder, multi-task heads |
| Условная логика с ветвлениями | `nn.ModuleList` + custom forward | Neural Architecture Search, AdaIN |

---

## Частые ошибки и решения

### Ошибка 1: Использование обычного списка

**Проблема:**
```python
self.experts = [Expert(...) for _ in range(8)]  # ❌
```

**Симптом:**
```python
RuntimeError: Input and weight are on different devices
# или
# Модель не обучается (loss не уменьшается)
```

**Решение:**
```python
self.experts = nn.ModuleList([Expert(...) for _ in range(8)])  # ✅
```

---

### Ошибка 2: Забыли `.item()` при индексации

**Проблема:**
```python
expert_idx = selected_experts[b, s, k]  # Tensor(5)
expert = self.experts[expert_idx]  # ❌ TypeError!
```

**Симптом:**
```python
TypeError: list indices must be integers or slices, not Tensor
```

**Решение:**
```python
expert_idx = selected_experts[b, s, k].item()  # int(5)
expert = self.experts[expert_idx]  # ✅
```

---

### Ошибка 3: Неправильная индексация токена

**Проблема:**
```python
token = hidden_states[b, s, :]  # ❌ (512,) вместо (1, 1, 512)
expert_output = expert(token)   # RuntimeError: Expected 3D tensor
```

**Симптом:**
```python
RuntimeError: Expected 3D input (got 1D input)
```

**Решение:**
```python
token = hidden_states[b, s:s+1, :]  # ✅ (1, 1, 512)
expert_output = expert(token)
```

---

### Ошибка 4: Изменение размера ModuleList после обучения Router

**Проблема:**
```python
# Обучили Router на 8 экспертов
moe = SimpleMoELayer(num_experts=8)
train(moe)

# Потом добавили 9-го эксперта
moe.experts.append(Expert(...))  # ⚠️ Router не знает про индекс 8!
```

**Симптом:**
- Expert 8 никогда не используется (Router выдаёт только индексы 0-7)

**Решение:**
- Фиксируйте `num_experts` при инициализации
- Если нужно добавить экспертов — переобучите Router

---

### Ошибка 5: Срезы возвращают обычный список

**Проблема:**
```python
first_three = moe.experts[:3]  # ❌ Возвращает list, а не nn.ModuleList!
first_three = first_three.to('cuda')  # AttributeError!
```

**Симптом:**
```python
AttributeError: 'list' object has no attribute 'to'
```

**Решение:**
Используйте итерацию или индексацию по одному:
```python
for expert in moe.experts[:3]:
    expert.to('cuda')  # ✅
```

---

## Ссылки и ресурсы

### Официальная документация PyTorch
- [nn.ModuleList](https://pytorch.org/docs/stable/generated/torch.nn.ModuleList.html)
- [nn.Sequential](https://pytorch.org/docs/stable/generated/torch.nn.Sequential.html)
- [nn.ModuleDict](https://pytorch.org/docs/stable/generated/torch.nn.ModuleDict.html)

### Связанные файлы проекта
- `experiments/domain/moe/moe_layer.py` — реализация SimpleMoELayer
- `experiments/domain/moe/router.py` — MoE Router с Top-K gating
- `experiments/domain/moe/expert.py` — Expert Network (SwiGLU)
- `experiments/domain/moe/test/test_moe_layer.py` — тесты для MoE Layer

### Дополнительные материалы
- [PyTorch Container Modules](https://pytorch.org/docs/stable/nn.html#containers)
- [Mixture-of-Experts Papers](https://arxiv.org/abs/2202.09368)
- [Qwen3 Technical Report](https://arxiv.org/abs/2409.12186)

---

## 🎓 Заключение

**Ключевые выводы:**

1. ✅ **`nn.ModuleList` обязателен** для хранения списка модулей в PyTorch
2. ✅ **Обычный Python `list` НЕ регистрирует** параметры и ломает обучение
3. ✅ **Индексация работает** как в обычном списке: `self.experts[idx]`
4. ✅ **Каждый модуль инициализируется независимо** с разными весами
5. ✅ **Использование в MoE**: Router → индексы → доступ к экспертам → обработка

**Практическая рекомендация:**

При работе со списком модулей в PyTorch **всегда** используйте:
- `nn.ModuleList` — для однородных модулей (эксперты, слои attention)
- `nn.Sequential` — для последовательных операций (ResNet block)
- `nn.ModuleDict` — для именованных компонентов (encoder/decoder)

**Никогда не используйте** обычный Python `list` для хранения `nn.Module`!

---

<div align="center">

**Made with ❤️ for Deep Learning Education**

[⬆ Вернуться к содержанию](#-содержание)

</div>
