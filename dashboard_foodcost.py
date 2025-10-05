import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path

st.set_page_config(page_title="Фудкост — дэшборд", layout="wide")

# =========================
# Категории и ключевые слова (РАСШИРЕНО)
# =========================
CATEGORY_KEYWORDS = {
    "Мясо": [
        "говядин", "баранин", "свинин", "телятин", "мяс", "фарш", "вырезк",
        "стейк", "бекон", "ветчин", "ребр", "шея", "плечо", "окорок", "корейк",
        "рибай", "порос"
    ],
    "Птица": [
        "кур", "индейк", "утк", "цыпл", "цыплят", "бройл",
        "бедро", "грудк", "крылыш", "окороч", "печень кур", "сердечк", "желудк"
    ],
    "Рыба/морепродукты": [
        "лосос", "семг", "форел", "сибас", "дорадо", "тунец", "треск", "хек",
        "окун", "щук", "скумбр", "камбал", "анчоус", "сельд", "кревет", "мид",
        "кальмар", "осьминог", "гребеш", "краб", "устриц", "масляная рыба"
    ],
    "Сыр": [
        "сыр", "моцарелл", "пармез", "бри", "фет", "чеддер", "горгонзол",
        "маскарпон", "рикотт", "сулугуни", "брынз", "эмментал", "дорблю",
        "камамбер", "плавлен", "сливочный сыр", "крем-сыр", "гауд"
    ],
    "Молочка": [
        "сливк", "масло слив", "молок", "йогурт", "сметан", "творог",
        "ряженк", "кефир", "сгущен", "сыворотк"
    ],
    "Фрукты/овощи": [
        "помид", "томат", "огур", "лук", "картоф", "капуст", "перец", "баклаж",
        "кабач", "цуккин", "морков", "свекл", "чеснок", "имбир", "зелень",
        "укроп", "петруш", "кинз", "базилик", "шпинат", "сельдер", "рукол",
        "фенхел", "лимон", "лайм", "апельс", "яблок", "груш", "манго",
        "виноград", "ананас", "гранат", "киви", "авокадо", "черри",
        "маслин", "олив", "горошек", "броккол", "айсберг", "вешен", "розмар",
        "эстрагон", "тархун", "мят", "вишн", "клубник"
    ],
    "Бакалея": [
        "мук", "сахар", "соль", "рис", "круп", "греч", "овсян", "макарон", "какао",
        "дрожж", "крахмал", "кускус", "булгур", "чечевиц", "нут", "фасол",
        "паниров", "ванили", "разрыхл", "сода", "орех", "семеч", "изюм",
        "шоколад", "сироп", "масло раст", "оливков", "панко", "уксус", "яйц",
        "желток", "белок", "стружк кокос", "хондаши", "бадьян", "ореган",
        "тимьян", "чабрец", "кориандр", "паприк", "фисташ", "каперс", "кунжут"
    ],
    "Хлеб/выпечка": [
        "лаваш", "булк", "булочк", "хлеб", "лепеш", "тортиль", "пита",
        "багет", "чиабат", "тесто", "слоен", "бургер бул"
    ],
    "Соусы": [
        "соус", "кетчуп", "горчиц", "майонез", "паст томат", "аджик", "соев",
        "терияк", "табаск", "тартар", "песто", "цезар", "хойсин", "устрич",
        "васаб", "деми", "барбекю"
    ],
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

# =========================
# ЧТЕНИЕ ДАННЫХ: Excel или экспортная CSV
# =========================
DATE_PAT = re.compile(r"(\d{2}\.\d{2}\.\d{4})")
PERIOD_PAT = re.compile(r"[Пп]ериод\s*[csс]\s*(\d{2}\.\d{2}\.\d{4})\s*по\s*(\d{2}\.\d{2}\.\d{4})")

def find_header_row(raw: pd.DataFrame, max_scan: int = 60) -> int | None:
    for i in range(min(max_scan, len(raw))):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if any("товар" in c for c in row):
            return i
    return None

def extract_period_from_top(raw: pd.DataFrame, head_scan: int = 12):
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
    if "Отпускные суммы" in cols: return "Отпускные суммы"
    for c in cols:
        cl = str(c).lower()
        if "сумм" in cl or "стоим" in cl:
            return c
    return None

def choose_qty_column(cols: list[str]) -> str | None:
    return "Количество" if "Количество" in cols else None

def choose_unit_column(cols: list[str]) -> str | None:
    return "Ед. изм." if "Ед. изм." in cols else None

def extract_row_date_series(df: pd.DataFrame) -> pd.Series:
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

@st.cache_data
def load_from_excel(path: str = "Фудкост (1).xlsx"):
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

        prod_col = "Товар" if "Товар" in df.columns else (df.columns[3] if len(df.columns) > 3 else df.columns[-1])
        unit_col = choose_unit_column(cols) or (df.columns[5] if len(df.columns) > 5 else df.columns[-1])
        qty_col  = choose_qty_column(cols)  or (df.columns[6] if len(df.columns) > 6 else df.columns[-1])
        cost_col = choose_cost_column(cols) or (df.columns[11] if len(df.columns) > 11 else df.columns[-1])

        tmp = df[[prod_col, unit_col, qty_col, cost_col]].copy()
        tmp.columns = ["Товар", "Ед. изм.", "Количество", "Стоимость"]
        tmp = tmp.dropna(subset=["Товар"])

        tmp["Стоимость"] = pd.to_numeric(tmp["Стоимость"], errors="coerce")
        tmp["Количество"] = pd.to_numeric(tmp["Количество"], errors="coerce")

        tmp["Курс"] = sheet
        row_dates = extract_row_date_series(df)
        tmp["Дата"] = row_dates
        if tmp["Дата"].isna().all():
            tmp["Дата"] = period_start
        tmp["Дата"] = pd.to_datetime(tmp["Дата"], errors="coerce", dayfirst=True)

        all_rows.append(tmp)

    if not all_rows:
        return pd.DataFrame(columns=["Товар","Ед. изм.","Количество","Стоимость","Курс","Дата"])

    out = pd.concat(all_rows, ignore_index=True)
    return out

@st.cache_data
def load_from_csv(path: str = "2025-10-05T13-35_export.csv"):
    # Ожидаем колонки: Товар, Ед. изм., Категория, Стоимость, Количество, Курсы
    df = pd.read_csv(path)
    # Даты в экспорте могут отсутствовать — оставим пустыми
    if "Дата" not in df.columns:
        df["Дата"] = pd.NaT
    # Если «Курсы» уже склеены строкой — оставляем как есть
    # Нормализуем типы
    for col in ["Стоимость", "Количество"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата"]]

@st.cache_data
def load_data(auto_path_excel="Фудкост (1).xlsx", auto_path_csv="2025-10-05T13-35_export.csv"):
    p_csv = Path(auto_path_csv)
    p_xlsx = Path(auto_path_excel)
    if p_csv.exists():
        df = load_from_csv(str(p_csv))
    elif p_xlsx.exists():
        df = load_from_excel(str(p_xlsx))
    else:
        return pd.DataFrame(columns=["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата"])
    # Добьём год/месяц для фильтров, если даты есть
    df["Дата"] = pd.to_datetime(df["Дата"], errors="coerce", dayfirst=True)
    df["Год"] = df["Дата"].dt.year
    df["Месяц"] = df["Дата"].dt.month
    return df

df = load_data()

# =========================
# РЕКАТЕГОРИЗАЦИЯ: вытаскиваем «Прочее», куда возможно
# =========================
if "Категория" not in df.columns:
    df["Категория"] = df["Товар"].apply(detect_category)
else:
    # если Прочее — пытаемся угадать
    mask_other = df["Категория"].fillna("Прочее").eq("Прочее")
    df.loc[mask_other, "Категория"] = df.loc[mask_other, "Товар"].apply(detect_category)

# Для Excel-пути подставим курс как отдельный столбец; для CSV уже есть «Курсы»
if "Курс" not in df.columns and "Курсы" in df.columns:
    # оставляем как есть (Курсы = список/строка курсов)
    pass

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

# =========================
# Фильтры (по месяцу и году + по курсам/категориям)
# =========================
with st.sidebar:
    st.header("Фильтры")

    # Год/месяц
    if df["Месяц"].notna().any() and df["Год"].notna().any():
        years = sorted(df["Год"].dropna().unique().tolist())
        months = sorted([int(m) for m in df["Месяц"].dropna().unique().tolist() if 1 <= int(m) <= 12])
        selected_year = st.selectbox("Год", options=years, index=len(years)-1)
        selected_month = st.selectbox(
            "Месяц", options=months, index=len(months)-1,
            format_func=lambda m: {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}.get(int(m), str(m))
        )
    else:
        selected_year, selected_month = None, None

    # Курсы — если есть «Курс» (Excel) или «Курсы» (CSV)
    if "Курс" in df.columns:
        course_list = sorted(df["Курс"].dropna().unique().tolist())
    elif "Курсы" in df.columns:
        # распакуем склейку в список уникальных курсов для фильтра
        exploded = df["Курсы"].dropna().astype(str).str.split(",").explode().str.strip()
        course_list = sorted(exploded.unique().tolist())
    else:
        course_list = []

    selected_course = st.multiselect("Курсы", options=course_list)

    selected_unit = st.multiselect("Ед. изм.", options=sorted(df["Ед. изм."].dropna().unique().tolist()))
    selected_category = st.multiselect("Категория", options=sorted(df["Категория"].dropna().unique().tolist()))

# применяем фильтры
filtered = df.copy()
if selected_year is not None and selected_month is not None:
    filtered = filtered[(filtered["Год"] == selected_year) & (filtered["Месяц"] == selected_month)]

if selected_course:
    if "Курс" in filtered.columns:
        filtered = filtered[filtered["Курс"].isin(selected_course)]
    elif "Курсы" in filtered.columns:
        filtered = filtered[filtered["Курсы"].fillna("").apply(
            lambda s: any(c in [x.strip() for x in str(s).split(",")] for c in selected_course)
        )]

if selected_unit:
    filtered = filtered[filtered["Ед. изм."].isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].isin(selected_category)]

# =========================
# ВКЛАДКИ: Детализация / По продуктам / По курсам
# =========================
tab_detail, tab_by_product, tab_by_course = st.tabs(["🔎 Детализация", "📦 По продуктам", "🏫 По курсам"])

with tab_detail:
    st.subheader("🔎 Детализация (строки)")
    base_cols = ["Дата", "Категория", "Товар", "Ед. изм.", "Количество", "Стоимость"]
    if "Курс" in filtered.columns:
        base_cols.insert(1, "Курс")
    elif "Курсы" in filtered.columns:
        base_cols.insert(1, "Курсы")
    show = filtered[base_cols].sort_values(by=["Стоимость"], ascending=False)
    st.dataframe(show, use_container_width=True)

with tab_by_product:
    st.subheader("📦 Сводка по продуктам (с курсами)")
    if "Курс" in filtered.columns:
        courses_repr = "Курс"
    else:
        courses_repr = "Курсы"

    grouped_products = (
        filtered.groupby(["Товар", "Ед. изм."], dropna=False)
        .agg({
            "Стоимость": "sum",
            "Количество": "sum",
            courses_repr: lambda x: ", ".join(sorted(set(map(str, x))))
        })
        .reset_index()
        .rename(columns={courses_repr: "Курсы (список)"})
        .sort_values(by="Стоимость", ascending=False)
    )
    st.dataframe(grouped_products, use_container_width=True)

    st.markdown("**💰 Топ-10 продуктов по стоимости**")
    top_costs = grouped_products.head(10)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
    ax.set_title("Топ-10 дорогих продуктов")
    st.pyplot(fig)

    st.markdown("**⚖️ Топ-10 продуктов по количеству**")
    grouped_qty = grouped_products.sort_values(by="Количество", ascending=False).head(10)
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    sns.barplot(x="Количество", y="Товар", data=grouped_qty, ax=ax2)
    ax2.set_title("Топ-10 по количеству")
    st.pyplot(fig2)

with tab_by_course:
    st.subheader("🏫 Сводка по курсам")
    # Для CSV «Курсы» склеены — агрегируем по каждой строке как по всей записи
    if "Курс" in filtered.columns:
        grp = filtered.groupby("Курс", dropna=False)
    else:
        # распакуем склейку
        tmp = filtered.copy()
        tmp = tmp.assign(_Курс=tmp["Курсы"].fillna("").astype(str).str.split(",")).explode("_Курс")
        tmp["_Курс"] = tmp["_Курс"].str.strip()
        grp = tmp.groupby("_Курс", dropna=False)

    grouped_courses = grp.agg({"Стоимость": "sum", "Количество": "sum"}).reset_index().rename(columns={"_Курс":"Курс"})
    grouped_courses = grouped_courses.sort_values("Стоимость", ascending=False)
    st.dataframe(grouped_courses, use_container_width=True)

    st.markdown("**💰 Топ-10 курсов по стоимости**")
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    top_courses = grouped_courses.head(10)
    sns.barplot(x="Стоимость", y="Курс", data=top_courses, ax=ax3)
    ax3.set_xlabel("Стоимость"); ax3.set_ylabel("")
    st.pyplot(fig3)

# =========================
# Категорийная аналитика
# =========================
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
    fig4, ax4 = plt.subplots(figsize=(6, 4))
    sns.barplot(x="Стоимость", y="Категория", data=cat_agg.head(10), ax=ax4)
    ax4.set_xlabel("Стоимость"); ax4.set_ylabel("")
    st.pyplot(fig4)
with col2:
    st.markdown("**Топ категорий по количеству**")
    fig5, ax5 = plt.subplots(figsize=(6, 4))
    sns.barplot(x="Количество", y="Категория", data=cat_agg.sort_values("Количество", ascending=False).head(10), ax=ax5)
    ax5.set_xlabel("Количество"); ax5.set_ylabel("")
    st.pyplot(fig5)

# =========================
# Итоги
# =========================
st.subheader("📈 Общая статистика")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
c2.metric("Всего строк", f"{filtered.shape[0]:,}")
c3.metric("Уникальных продуктов", f"{filtered[['Товар','Ед. изм.']].drop_duplicates().shape[0]:,}")
if not filtered.empty and "Год" in filtered and "Месяц" in filtered:
    period_text = (f"{RU_MONTHS.get(int(filtered['Месяц'].dropna().iloc[0]), filtered['Месяц'].dropna().iloc[0])} "
                   f"{int(filtered['Год'].dropna().iloc[0])}")
    c4.metric("Период выборки", period_text)

# =========================
# «Прочее» — инспектор (после рекатегоризации)
# =========================
st.subheader("❓ Прочее (что ещё не распознано словарём)")
other = filtered[filtered["Категория"] == "Прочее"]
if other.empty:
    st.success("Отлично! Все позиции классифицированы.")
else:
    other_top = (
        other.groupby(["Товар"] + (["Курс"] if "Курс" in other.columns else []), dropna=False)
        .agg({"Стоимость": "sum", "Ед. изм.": lambda x: ", ".join(sorted(set(map(str, x))))})
        .reset_index()
        .rename(columns={"Ед. изм.": "Ед. изм. (варианты)"})
        .sort_values("Стоимость", ascending=False)
        .head(50)
    )
    st.write("Ниже топ-50 «Прочее» по стоимости — напиши, в какие категории их отнести, и я дополню словарь:")
    st.dataframe(other_top, use_container_width=True)
