import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
from pathlib import Path
import numpy as np

st.set_page_config(page_title="Фудкост — дэшборд", layout="wide")

# =========================
# Категории и ключевые слова (обновлено)
# =========================
CATEGORY_KEYWORDS = {
    "Мясо": [
        "говядин", "баранин", "свинин", "телятин", "мяс", "фарш", "вырезк",
        "стейк", "бекон", "ветчин", "ребр", "шея", "плечо", "окорок", "корейк",
        "рибай", "флэнк", "фланк", "порос"
    ],
    "Птица": [
        "кур", "индейк", "утк", "цыпл", "цыплят", "бройл",
        "бедро", "грудк", "крылыш", "окороч", "печень кур", "сердечк", "желудк"
    ],
    "Рыба/морепродукты": [
        "лосос", "семг", "форел", "сибас", "дорадо", "тунец", "треск", "хек",
        "окун", "щук", "скумбр", "камбал", "анчоус", "сельд", "кревет", "мид",
        "кальмар", "осьминог", "осьминоги", "гребеш", "краб", "устриц", "масляная рыба"
    ],
    "Сыр": [
        "сыр", "моцарелл", "пармез", "бри", "фет", "чеддер", "горгонзол",
        "маскарпон", "рикотт", "сулугуни", "брынз", "эмментал", "дорблю",
        "камамбер", "плавлен", "сливочный сыр", "крем-сыр", "гауд", "халум"
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
        "эстрагон", "тархун", "мят", "вишн", "клубник", "спарж"
    ],
    "Бакалея": [
        "мук", "сахар", "соль", "рис", "круп", "греч", "овсян", "макарон", "какао",
        "дрожж", "крахмал", "кускус", "булгур", "чечевиц", "нут", "фасол",
        "паниров", "ванили", "разрыхл", "сода", "орех", "семеч", "изюм",
        "шоколад", "сироп", "масло раст", "оливков", "панко", "уксус", "яйц",
        "желток", "белок", "стружк кокос", "хондаши", "бадьян", "ореган",
        "тимьян", "чабрец", "кориандр", "паприк", "фисташ", "каперс", "кунжут", "бульон"
    ],
    "Хлеб/выпечка": [
        "лаваш", "булк", "булочк", "хлеб", "лепеш", "тортиль", "пита",
        "багет", "чиабат", "тесто", "слоен", "бургер бул", "лаваш", "тортилья", "булочки для бургера"
    ],
    "Соусы": [
        "соус", "кетчуп", "горчиц", "майонез", "паст томат", "аджик", "соев",
        "терияк", "табаск", "тартар", "песто", "цезар", "хойсин", "устрич",
        "васаб", "деми", "барбекю", "ткемал", "сальс"
    ],
    "Прочее": []
}

RU_MONTHS = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}
KNOWN_CATS = list(CATEGORY_KEYWORDS.keys())

def detect_category(name: str) -> str:
    s = str(name).lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if cat == "Прочее":
            continue
        for k in keys:
            if k in s:
                return cat
    return "Прочее"

# ======== загрузка (CSV из выгрузки приоритетно) ========
DATE_PAT = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

@st.cache_data
def load_from_csv(path: str = "2025-10-05T13-35_export.csv"):
    df = pd.read_csv(path)
    if "Дата" not in df.columns:
        df["Дата"] = pd.NaT
    for col in ["Стоимость","Количество"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # нормализуем исходную категорию (могут быть пробелы/регистр)
    if "Категория" in df.columns:
        df["Категория"] = df["Категория"].astype(str).str.strip()
        df.loc[df["Категория"].isin(["", "nan", "None"]), "Категория"] = np.nan
    return df[["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата"]]

@st.cache_data
def load_data():
    p_csv = Path("2025-10-05T13-35_export.csv")
    p_xlsx = Path("Фудкост (1).xlsx")
    if p_csv.exists():
        df = load_from_csv(str(p_csv))
    elif p_xlsx.exists():
        # если нужно — можно вернуть excel-ветку из прошлой версии
        df = pd.DataFrame(columns=["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата"])
    else:
        df = pd.DataFrame(columns=["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата"])
    # даты для фильтров (если есть)
    df["Дата"] = pd.to_datetime(df["Дата"], errors="coerce", dayfirst=True)
    df["Год"] = df["Дата"].dt.year
    df["Месяц"] = df["Дата"].dt.month
    return df

df = load_data()

# ======== РЕКАТЕГОРИЗАЦИЯ (фикс "осьминоги/авокадо" и т.п.) ========
detected = df["Товар"].apply(detect_category)

# 1) если детект дал не "Прочее" — всегда берём его
# 2) если исходная категория отсутствует или не из KNOWN_CATS — берём детект
# 3) иначе оставляем исходную
orig = df["Категория"].astype(str).str.strip()
use_orig = orig.isin(KNOWN_CATS) & (detected.eq("Прочее"))
df["Категория"] = np.where(use_orig, orig, detected)

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

# ======== Фильтры ========
with st.sidebar:
    st.header("Фильтры")

    # месячный фильтр (если дат нет – не показываем)
    if df["Месяц"].notna().any() and df["Год"].notna().any():
        years = sorted(df["Год"].dropna().unique().tolist())
        months = sorted([int(m) for m in df["Месяц"].dropna().unique().tolist() if 1 <= int(m) <= 12])
        selected_year = st.selectbox("Год", options=years, index=len(years)-1)
        selected_month = st.selectbox("Месяц закупки", options=months, index=len(months)-1,
                                      format_func=lambda m: RU_MONTHS.get(int(m), str(m)))
    else:
        selected_year, selected_month = None, None

    # курсы из склейки "Курсы"
    exploded = df["Курсы"].dropna().astype(str).str.split(",").explode().str.strip()
    course_list = sorted(exploded.unique().tolist())
    selected_course = st.multiselect("Выберите курсы", options=course_list)

    selected_unit = st.multiselect("Единица измерения", options=sorted(df["Ед. изм."].dropna().unique().tolist()))
    selected_category = st.multiselect("Категория", options=sorted(df["Категория"].dropna().unique().tolist()))

filtered = df.copy()
if selected_year is not None and selected_month is not None:
    filtered = filtered[(filtered["Год"] == selected_year) & (filtered["Месяц"] == selected_month)]
if selected_course:
    filtered = filtered[filtered["Курсы"].fillna("").apply(
        lambda s: any(c in [x.strip() for x in str(s).split(",")] for c in selected_course)
    )]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].isin(selected_category)]

# ======== Таблица по продуктам ========
st.subheader("📦 Сводка по продуктам")
grouped = (
    filtered.groupby(["Товар", "Ед. изм.", "Категория"], dropna=False)
    .agg({"Стоимость": "sum", "Количество": "sum", "Курсы": lambda x: ", ".join(sorted(set(map(str, x))))})
    .reset_index()
    .rename(columns={"Курсы": "Курсы"})
    .sort_values(by="Стоимость", ascending=False)
)
st.dataframe(grouped, use_container_width=True)

# ======== Визуализации ========
st.subheader("💰 Топ-10 продуктов по стоимости")
top_costs = grouped.head(10)
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
ax.set_title("Топ-10 дорогих продуктов")
st.pyplot(fig)

st.subheader("⚖️ Топ-10 продуктов по количеству")
top_qty = grouped.sort_values(by="Количество", ascending=False).head(10)
fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(x="Количество", y="Товар", data=top_qty, ax=ax2)
ax2.set_title("Топ-10 по количеству")
st.pyplot(fig2)

# ======== Категорийная аналитика ========
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

# ======== Итоги ========
st.subheader("📈 Общая статистика")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
c2.metric("Всего строк", f"{filtered.shape[0]:,}")
c3.metric("Уникальных продуктов", f"{grouped[['Товар','Ед. изм.']].drop_duplicates().shape[0]:,}")
if filtered["Месяц"].notna().any() and filtered["Год"].notna().any():
    try:
        period_text = f"{RU_MONTHS.get(int(filtered['Месяц'].dropna().iloc[0]), filtered['Месяц'].dropna().iloc[0])} {int(filtered['Год'].dropna().iloc[0])}"
        c4.metric("Период выборки", period_text)
    except Exception:
        c4.metric("Период выборки", "-")

# ======== Инспектор «Прочее» (после рекатегоризации) ========
st.subheader("❓ Прочее — что ещё не распознано словарём")
other = filtered[filtered["Категория"] == "Прочее"]
if other.empty:
    st.success("Отлично! Все позиции классифицированы.")
else:
    other_top = (
        other.groupby(["Товар"], dropna=False)
        .agg({"Стоимость": "sum", "Ед. изм.": lambda x: ", ".join(sorted(set(map(str, x)))) , "Курсы": lambda x: ", ".join(sorted(set(map(str, x))))})
        .reset_index()
        .rename(columns={"Ед. изм.": "Ед. изм. (варианты)"})
        .sort_values("Стоимость", ascending=False)
        .head(50)
    )
    st.write("Ниже топ-50 «Прочее». Напиши, куда их отнести — я дополню словарь:")
    st.dataframe(other_top, use_container_width=True)
