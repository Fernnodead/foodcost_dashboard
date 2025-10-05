import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

st.set_page_config(page_title="Фудкост — дэшборд", layout="wide")

# Категории и ключевые слова
CATEGORY_KEYWORDS = {
    "Мясо": ["говядин", "баранин", "свинин", "мяс", "фарш", "вырезк", "стейк", "бекон", "ветчин", "телятин", "ребр", "шея"],
    "Птица": ["кур", "индейк", "утк", "бедро", "грудк", "крылыш", "окороч", "печень кур", "сердечк", "желудк", "цыпл"],
    "Рыба/морепродукты": ["лосос", "семг", "тунец", "дорадо", "сибас", "форел", "треск", "хек", "щук", "окун", "скумбр", "камбал", "селед", "анчоус",
                          "кревет", "мид", "кальмар", "осьминог", "гребеш", "морепродукт", "филе рыбы","Гребешки охл","Гребешки в раковине"],
    "Сыр": ["сыр", "моцарелл", "пармез", "фет", "бри", "чеддер", "горгонзол", "маскарпон", "рикотт", "сулугуни", "брынз", "эмментал", "дорблю", "камамбер"],
    "Молочка": ["сливк", "масло", "молок", "йогурт", "сметан", "творог", "кефир", "ряженк", "сгущен"],
    "Фрукты/овощи": ["помид", "томат", "огур", "лук", "картоф", "лимон", "яблок", "апельс", "зелень", "капуст", "перец", "баклажан",
                     "фрукт", "овощ", "манго", "виноград", "гранат", "груша", "ананас", "морков", "кабач", "цуккин", "свекл", "чеснок",
                     "имбир", "кинз", "петруш", "укроп", "базилик", "шпинат", "сельдер", "рукол", "фенхел", "лайм", "киви", "авокадо",
                     "броккол", "цветн", "айсберг", "ромэн", "редис", "черри"],
    "Бакалея": ["мук", "сахар", "соль", "рис", "круп", "спец", "греч", "овсян", "макарон", "какао", "дрожж", "крахмал", "кускус", "булгур",
                "чечевиц", "нут", "фасол", "панировоч", "ванили", "разрыхл", "сода", "орех", "семечк", "изюм", "шоколад", "сироп"],
    "Хлеб/выпечка": ["лаваш", "булк", "хлеб", "лепеш", "тортиль", "пита", "багет", "чиабат", "тесто", "слоен"],
    "Соусы": ["соус", "кетчуп", "горчиц", "майонез", "паст томат", "аджик", "соев", "терияк", "табаск", "тартар", "песто", "цезар", "хойсин", "устрич", "васаб"],
    "Прочее": []
}

RU_MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
    7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

def detect_category(name: str) -> str:
    n = str(name).lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if cat == "Прочее":
            continue
        for k in keys:
            if k in n:
                return cat
    return "Прочее"


# skiprows и дата

DATE_PAT = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
PERIOD_PAT = re.compile(r"[Пп]ериод\s*[csс]\s*(\d{2}\.\d{2}\.\d{4})\s*по\s*(\d{2}\.\d{2}\.\d{4})")

def find_header_row(raw: pd.DataFrame, max_scan: int = 60) -> int | None:
    """Найти номер строки, где находится заголовок (содержит 'Товар')."""
    for i in range(min(max_scan, len(raw))):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if any("товар" in c for c in row):
            return i
    return None

def extract_period_from_top(raw: pd.DataFrame, head_scan: int = 12):
    """Ищем 'Период c dd.mm.yyyy по dd.mm.yyyy' в первых строках."""
    txt = " ".join(
        " ".join(map(str, raw.iloc[i].dropna().tolist()))
        for i in range(min(head_scan, len(raw)))
    )
    m = PERIOD_PAT.search(txt)
    if not m:
        return None, None
    try:
        start = pd.to_datetime(m.group(1), dayfirst=True)
        end = pd.to_datetime(m.group(2), dayfirst=True)
        return start, end
    except Exception:
        return None, None

def choose_cost_column(cols: list[str]) -> str | None:
    """Предпочитаем 'Отпускные суммы', затем что-то со словом 'сумм'/'стоим'."""
    if "Отпускные суммы" in cols:
        return "Отпускные суммы"
    for c in cols:
        cl = str(c).lower()
        if "сумм" in cl or "стоим" in cl:
            return c
    return None

def choose_qty_column(cols: list[str]) -> str | None:
    if "Количество" in cols:
        return "Количество"
    return None

def choose_unit_column(cols: list[str]) -> str | None:
    if "Ед. изм." in cols:
        return "Ед. изм."
    return None

def extract_row_date_series(df: pd.DataFrame) -> pd.Series:
    """Дату строки: явная колонка 'Дата' или парсинг из первой колонки ('... от dd.mm.yyyy')."""
    # явная колонка
    date_col = None
    for c in df.columns:
        if re.search(r"дата|date", str(c).lower()):
            date_col = c
            break
    if date_col is not None:
        return pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

    # парсим из первой колонки
    first_col = df.columns[0]
    s = df[first_col].astype(str).str.extract(DATE_PAT, expand=False)
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

# ---------------------------
# Загрузка данных (авто skiprows + корректная дата)
# ---------------------------
@st.cache_data
def load_data(path: str = "Фудкост (1).xlsx"):
    xls = pd.ExcelFile(path)
    all_rows = []

    for sheet in xls.sheet_names:
        if sheet in ["Фудкост", "Цены с новым фудкостом"]:
            continue

        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        header_row = find_header_row(raw)
        if header_row is None:
            continue

        period_start, period_end = extract_period_from_top(raw)

        df = pd.read_excel(path, sheet_name=sheet, skiprows=header_row)
        cols = list(df.columns)

        # Найдём ключевые колонки
        prod_col = "Товар" if "Товар" in df.columns else (df.columns[3] if len(df.columns) > 3 else df.columns[-1])
        unit_col = choose_unit_column(cols) or (df.columns[5] if len(df.columns) > 5 else df.columns[-1])
        qty_col = choose_qty_column(cols) or (df.columns[6] if len(df.columns) > 6 else df.columns[-1])
        cost_col = choose_cost_column(cols) or (df.columns[11] if len(df.columns) > 11 else df.columns[-1])

        tmp = df[[prod_col, unit_col, qty_col, cost_col]].copy()
        tmp.columns = ["Товар", "Ед. изм.", "Количество", "Стоимость"]
        tmp = tmp.dropna(subset=["Товар"])

        # Приводим числа
        tmp["Стоимость"] = pd.to_numeric(tmp["Стоимость"], errors="coerce")
        tmp["Количество"] = pd.to_numeric(tmp["Количество"], errors="coerce")

        # Если расходы у тебя отрицательные — раскомментируй следующие 2 строки:
        # tmp = tmp[(tmp["Стоимость"] < 0) & (tmp["Количество"] > 0)]
        # tmp["Стоимость"] = tmp["Стоимость"].abs()

        tmp["Курс"] = sheet

        # Дата
        row_dates = extract_row_date_series(df)
        tmp["Дата"] = row_dates
        if tmp["Дата"].isna().all():
            tmp["Дата"] = period_start  # если не нашли — ставим начало периода

        tmp["Дата"] = pd.to_datetime(tmp["Дата"], errors="coerce", dayfirst=True)

        # Категория
        tmp["Категория"] = tmp["Товар"].apply(detect_category)

        all_rows.append(tmp)

    if not all_rows:
        return pd.DataFrame(columns=["Товар", "Ед. изм.", "Количество", "Стоимость", "Курс", "Категория", "Дата", "Год", "Месяц"])

    out = pd.concat(all_rows, ignore_index=True)
    # Добавим год и месяц для фильтров
    out["Год"] = out["Дата"].dt.year
    out["Месяц"] = out["Дата"].dt.month

    return out

df = load_data()

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

# ---------------------------
# Фильтры (по месяцу и году)
# ---------------------------
with st.sidebar:
    st.header("Фильтры")

    # Доступные годы/месяцы из данных
    if "Год" in df.columns and df["Год"].notna().any():
        available_years = sorted(df["Год"].dropna().unique().tolist())
        selected_year = st.selectbox("Год", options=available_years, index=len(available_years)-1)
    else:
        selected_year = None

    if "Месяц" in df.columns and df["Месяц"].notna().any():
        available_months = sorted([int(m) for m in df["Месяц"].dropna().unique().tolist() if pd.notna(m) and m >= 1 and m <= 12])
        # по умолчанию последний месяц из данных
        m_default_idx = len(available_months)-1 if available_months else 0
        selected_month = st.selectbox(
            "Месяц",
            options=available_months,
            index=m_default_idx,
            format_func=lambda m: RU_MONTHS.get(int(m), str(m))
        )
    else:
        selected_month = None

    selected_course = st.multiselect("Курсы", options=sorted(df["Курс"].dropna().unique().tolist()))
    selected_unit = st.multiselect("Ед. изм.", options=sorted(df["Ед. изм."].dropna().unique().tolist()))
    selected_category = st.multiselect("Категория", options=sorted(df["Категория"].dropna().unique().tolist()))

# ---------------------------
# Применяем фильтры
# ---------------------------
filtered = df.copy()

if selected_year is not None and selected_month is not None:
    filtered = filtered[(filtered["Год"] == selected_year) & (filtered["Месяц"] == selected_month)]

if selected_course:
    filtered = filtered[filtered["Курс"].isin(selected_course)]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].isin(selected_category)]

# ---------------------------
# Группировка по товарам
# ---------------------------
grouped = (
    filtered.groupby(["Товар", "Ед. изм."], dropna=False)
    .agg({"Стоимость": "sum", "Количество": "sum", "Курс": lambda x: ", ".join(sorted(set(map(str, x))))})
    .reset_index()
    .rename(columns={"Курс": "Курсы"})
)

# ---------------------------
# Основная таблица
# ---------------------------
st.subheader("📦 Сводка по продуктам")
st.dataframe(grouped.sort_values(by="Стоимость", ascending=False), use_container_width=True)


# Визуализация — ТОП-10 продуктов
st.subheader("💰 Топ-10 продуктов по стоимости")
top_costs = grouped.sort_values(by="Стоимость", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
ax.set_title("Топ-10 дорогих продуктов")
st.pyplot(fig)

st.subheader("⚖️ Топ-10 продуктов по количеству")
top_qty = grouped.sort_values(by="Количество", ascending=False).head(10)
fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(x="Количество", y="Товар", data=top_qty, ax=ax2)
ax2.set_title("Топ-10 продуктов по количеству")
st.pyplot(fig2)

# Категорийная аналитика

st.subheader("🏷️ Категории — расходы и количество")
cat_agg = (
    filtered.groupby("Категория", dropna=False)
    .agg({"Стоимость": "sum", "Количество": "sum"})
    .reset_index()
    .sort_values("Стоимость", ascending=False)
)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Топ категорий по стоимости**")
    fig3, ax3 = plt.subplots(figsize=(6, 4))
    sns.barplot(x="Стоимость", y="Категория", data=cat_agg.head(10), ax=ax3)
    ax3.set_xlabel("Стоимость"); ax3.set_ylabel("")
    st.pyplot(fig3)

with col2:
    st.markdown("**Топ категорий по количеству**")
    fig4, ax4 = plt.subplots(figsize=(6, 4))
    sns.barplot(x="Количество", y="Категория", data=cat_agg.sort_values("Количество", ascending=False).head(10), ax=ax4)
    ax4.set_xlabel("Количество"); ax4.set_ylabel("")
    st.pyplot(fig4)

# Итоги

st.subheader("📈 Общая статистика")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
c2.metric("Всего строк", f"{filtered.shape[0]:,}")
c3.metric("Уникальных продуктов", f"{grouped.shape[0]:,}")
if "Дата" in filtered.columns and filtered["Дата"].notna().any():
    period_text = f"{RU_MONTHS.get(int(filtered['Месяц'].iloc[0]), filtered['Месяц'].iloc[0])} {int(filtered['Год'].iloc[0])}" if not filtered.empty else "-"
    c4.metric("Период выборки", period_text)

# «Прочее» — чтобы дообучить словарь

st.subheader("❓ Прочее (не распознано словарём)")
other = filtered[filtered["Категория"] == "Прочее"]
if other.empty:
    st.success("Отлично! Все позиции классифицированы.")
else:
    other_top = (
        other.groupby("Товар", dropna=False)
        .agg({"Стоимость": "sum", "Ед. изм.": lambda x: ", ".join(sorted(set(map(str, x))))})
        .reset_index()
        .sort_values("Стоимость", ascending=False)
        .rename(columns={"Ед. изм.": "Ед. изм. (варианты)"})
        .head(50)
    )
    st.write("Ниже топ-50 «Прочее» по стоимости — добавь характерные части слов в CATEGORY_KEYWORDS:")
    st.dataframe(other_top, use_container_width=True)
