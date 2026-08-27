## ЦЕЛЬ

Создать веб-интерфейс для агентной системы с использованием Streamlit, который:

- Соответствует ТЗ (раздел 11.1) — 8 экранов с учётом ролей.
- Работает с FastAPI-бэкендом через REST API.
- Поддерживает ролевую модель (администратор, эксперт, пользователь, аудитор).
- Использует встроенные компоненты Streamlit + кастомные расширения (st-aggrid, streamlit-agraph).
- Обеспечивает приемлемую производительность для вывода информации (таблицы, графы, формы).

## S.1. АРХИТЕКТУРА ПРИЛОЖЕНИЯ

### S.1.1 Стек технологий

| Компонент | Технология | Назначение |
|---|---|---|
| Фреймворк | Streamlit 1.30+ | Интерфейс |
| Язык | Python 3.11+ | Весь код |
| HTTP-клиент | Requests / httpx | Запросы к FastAPI |
| Таблицы | st-aggrid (AgGrid) | Интерактивные таблицы с сортировкой, фильтрацией, пагинацией |
| Графы | streamlit-agraph | Визуализация топологии участка |
| Формы | Streamlit Forms | Ввод данных |
| Уведомления | st.toast / st.sidebar | Системные сообщения |
| Стейт-менеджмент | st.session_state | Глобальное состояние |

### S.1.2 Структура проекта

```
ui_streamlit/
├── app.py                     # Главный файл (навигация + роли)
├── pages/
│   ├── 1_Search.py            # Поиск
│   ├── 2_Results.py           # Результаты поиска
│   ├── 3_Upload.py            # Загрузка паспорта
│   ├── 4_Component.py         # Карточка изделия
│   ├── 5_Compare.py           # Сравнение деталей
│   ├── 6_Expert.py            # Экспертная проверка
│   ├── 7_Audit.py             # Аудит
│   └── 8_Admin.py             # Управление справочниками
├── components/
│   ├── __init__.py
│   ├── auth.py                # Логин, проверка ролей
│   ├── api.py                 # HTTP-клиент (эндпоинты)
│   ├── tables.py              # Обёртка для st-aggrid
│   ├── graphs.py              # Обёртка для streamlit-agraph
│   ├── cards.py               # Карточки (MUI-подобные)
│   └── utils.py               # Форматтеры, константы
├── theme.py                   # Цветовая схема (CSS + Streamlit config)
├── .streamlit/
│   └── config.toml            # Настройки темы
└── requirements.txt
```

## S.2. ТЕМА И СТИЛИ

### S.2.1 Цветовая палитра статусов (через CSS)

```css
/* .streamlit/config.toml */
[theme]
primary = "#1976d2"
background = "#ffffff"
secondaryBackgroundColor = "#f5f5f5"
textColor = "#000000"
font = "sans-serif"
```

### S.2.2 Кастомные цвета для статусов (в коде)

```python
# theme.py
STATUS_COLORS = {
    "Соответствует": "#2e7d32",      # green
    "Потенциальный аналог": "#ed6c02", # orange
    "Требует проверки": "#d32f2f",    # red
    "Нет данных": "#9e9e9e",          # grey
}
```

## S.3. ЭКРАНЫ

### S.3.1 Экран «Поиск» (pages/1_Search.py)

Доступ: все роли.

Компоненты Streamlit:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| SearchForm | st.text_area | Ввод запроса |
| ModeSwitcher | st.radio / st.selectbox | Детерминированный / LLM |
| FilterPanel | st.expander + st.selectbox, st.number_input | Расширенные фильтры |
| SearchHistory | st.dataframe / st.button | Последние запросы |

Логика:

1. Пользователь вводит запрос.
2. Выбирает режим (по умолчанию — детерминированный).
3. Нажимает st.button("Найти").
4. Отправляется POST-запрос к /api/search.
5. При получении ответа — перенаправление на 2_Results.py с request_id в st.session_state.

### S.3.2 Экран «Результаты поиска» (pages/2_Results.py)

Доступ: все роли.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| ResultsTable | st-aggrid (AgGrid) | Таблица кандидатов с сортировкой, фильтрацией, пагинацией |
| MatchScore | st.progress + st.caption | Визуальный индикатор процента совпадения |
| StatusBadge | st.markdown с цветным текстом | Статус (Соответствует / Потенциальный аналог / ...) |
| SourceLinks | st.link_button | Ссылки на источники |

Таблица (колонцы):

| Код МТР | КСМ | Тип | DN | PN | Материал | Совпадение % | Статус | Наличие | Источники |
|---|---|---|---|---|---|---|---|---|---|
| MTR-001 | KSM-001 | Задвижка | 150 | 4.0 | 09Г2С | 94% | ⚠️ Потенциальный аналог | 12 шт | 📄 📊 |

Детали строки (разворачивается через AgGrid):

- Совпавшие параметры (зелёные галочки).
- Не совпавшие параметры (красные крестики).
- Недостающие параметры (жёлтые знаки вопроса).
- Предупреждения и рекомендации.
- Кнопка "Открыть карточку" → st.switch_page("4_Component").

### S.3.3 Экран «Загрузка паспорта» (pages/3_Upload.py)

Доступ: все роли.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| UploadDropzone | st.file_uploader | Drag-and-drop для PDF |
| ProgressTracker | st.progress + st.text | Индикатор обработки |
| ExtractedParamsTable | st.dataframe | Извлечённые параметры после завершения |
| DocumentList | st.dataframe | Список загруженных документов с их статусами |

Логика:

1. Пользователь загружает PDF через st.file_uploader.
2. Бэкенд возвращает document_id.
3. UI начинает опрос /api/passport/status/{document_id} каждые 2 секунды (через st.empty() + time.sleep).
4. При статусе completed — отобразить извлечённые параметры.
5. Если статус error — показать ошибку через st.error.

### S.3.4 Экран «Карточка изделия» (pages/4_Component.py)

Доступ: все роли.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| ComponentCard | st.markdown + st.columns | Заголовок детали (KSM, MTR, тип) |
| AttributeTable | st.dataframe с цветовой подсветкой | Все параметры с уверенностью |
| ConfidenceBadge | st.markdown с цветным фоном | Уверенность 0–1 |
| StockCard | st.metric | Остаток, цена, сроки |
| CompatibilityCard | st.alert (success/warning/error) | Результаты проверки |
| NeighborsGraph | streamlit-agraph | Визуализация соседей |

Пример визуализации графа:

```python
from streamlit_agraph import agraph, Node, Edge, Config

nodes = [
    Node(id="KSM-001", label="Задвижка DN150", size=25),
    Node(id="KSM-002", label="Труба DN150", size=20),
    Node(id="KSM-003", label="Переход DN150→DN100", size=20),
]
edges = [
    Edge(source="KSM-001", target="KSM-002", label="сварка"),
    Edge(source="KSM-002", target="KSM-003", label="фланец"),
]
config = Config(width=750, height=500, directed=True, physics=True, hierarchical=False)
agraph(nodes, edges, config)
```

### S.3.5 Экран «Сравнение деталей» (pages/5_Compare.py)

Доступ: все роли.

Компоненты:

- CompareSelector — два st.selectbox с поиском по KSM/названию (или st.text_input + st.button для поиска).
- CompareTable — st.dataframe с колонками: Параметр, Деталь 1, Деталь 2, Статус (смайлики/цвета).
- CompareRecommendation — st.success / st.warning / st.error с итоговой рекомендацией.

### S.3.6 Экран «Экспертная проверка» (pages/6_Expert.py)

Доступ: эксперт, администратор.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| ExpertReviewTabs | st.tabs | Запросы / Паспорта на проверку |
| ReviewList | st.dataframe | Список запросов с кнопкой "Открыть" |
| ReviewForm | st.expander / st.form | Редактирование параметров, кнопки "Подтвердить"/"Отклонить", поле для комментария |
| PassportReviewList | st.dataframe | Паспорта с предложенными кандидатами |
| PassportLinkModal | st.selectbox + st.button | Выбор KSM из предложенных + кнопка "Связать" |

Логика формы проверки:

```python
with st.form("review_form"):
    st.subheader(f"Запрос: {query}")
    st.dataframe(candidates_df)
    
    new_dn = st.number_input("DN", value=current_dn)
    new_pn = st.number_input("PN", value=current_pn)
    new_material = st.text_input("Материал", value=current_material)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        confirm = st.form_submit_button("Подтвердить", type="primary")
    with col2:
        reject = st.form_submit_button("Отклонить")
    with col3:
        changes = st.form_submit_button("Требует изменений")
    
    comment = st.text_area("Комментарий эксперта")
```

### S.3.7 Экран «Аудит» (pages/7_Audit.py)

Доступ: аудитор, администратор.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| AuditFilter | st.date_input, st.selectbox, st.multiselect | Фильтры по дате, пользователю, действию, статусу |
| AuditTable | st-aggrid | Таблица логов (Время, Пользователь, Действие, Статус, Длительность) |
| AuditDetailModal | st.expander | Развёрнутые данные (промпт, ответ, параметры) |

### S.3.8 Экран «Управление справочниками» (pages/8_Admin.py)

Доступ: администратор.

Компоненты:

| Компонент | Элемент Streamlit | Назначение |
|---|---|---|
| DictionaryTabs | st.tabs | 5 вкладок (Ключевые слова, Контекстные правила, Синонимы, Константы, Правила валидации) |
| DictionaryTable | st.dataframe + st.button (Редактировать/Удалить) | Текущие записи |
| DictionaryForm | st.expander / st.form | Добавление/редактирование записи |
| ReloadCacheButton | st.button | Вызов POST /api/admin/dictionaries/reload |

## S.4. API-КОНТРАКТЫ

Полностью совпадают с UI.4 из React-версии.
Все эндпоинты (авторизация, поиск, паспорта, компоненты, сравнение, нормы, эксперт, аудит, администрирование) — без изменений.

## S.5. РОЛЕВАЯ МОДЕЛЬ

Реализация в Streamlit:

```python
# components/auth.py
def check_role(required_roles: list):
    if "role" not in st.session_state:
        st.session_state.role = "user"  # default
    
    if st.session_state.role not in required_roles:
        st.error("Доступ запрещён. Недостаточно прав.")
        st.stop()
```

Использование в каждом экране:

```python
# pages/6_Expert.py
from components.auth import check_role
check_role(["expert", "admin"])
```

## S.6. ГЛОБАЛЬНОЕ СОСТОЯНИЕ (SESSION_STATE)

| Ключ | Назначение |
|---|---|
| st.session_state.role | Роль пользователя (user/expert/auditor/admin) |
| st.session_state.token | JWT-токен для API-запросов |
| st.session_state.request_id | Идентификатор текущего запроса (для результатов) |
| st.session_state.results | Кеш результатов поиска (для перехода между страницами) |

## S.7. ПЛАН РАЗРАБОТКИ (3 СПРИНТА)

| Спринт | Задачи |
|---|---|
| 1 | Настройка проекта (requirements.txt, config.toml). Экран поиска + результаты (st-aggrid). |
| 2 | Загрузка паспорта (прогресс, извлечение). Карточка изделия (атрибуты, граф через streamlit-agraph). |
| 3 | Сравнение. Экспертная проверка (формы, табы). Аудит (фильтры, таблица). Администрирование справочников. |

## КРИТЕРИИ ГОТОВНОСТИ

- Все 8 экранов реализованы.
- Авторизация и ролевая модель работают.
- API-запросы к бэкенду проходят.
- Таблицы (st-aggrid) поддерживают сортировку, фильтрацию, пагинацию.
- Графы (streamlit-agraph) отображают топологию.
- Прогресс-бар и статусы отображаются корректно.
- Приложение запускается одной командой: streamlit run app.py.
