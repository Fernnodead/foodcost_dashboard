# foodcost_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re

st.set_page_config(page_title="Фудкост — дэшборд", layout="wide")

# ===== Google Sheets (Publish to Web → CSV) =====
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0eKDqy05ncTpiWM0oFxv-dthUJ53rPIMf5A-NFCBAJSrLEDRjHdpz2eNnmR192e5eZMD05Ua4bMD7/pub?output=csv"

# ===== Фиксированные позиции колонок (1-базные буквы) =====
# D + E → Товар, F → Ед. изм., G → Количество, N → Стоимость
COL_D = 4   # 1-базный номер колонки D
COL_E = 5   # E
COL_F = 6   # F
COL_G = 7   # G
COL_N = 14  # N

# ===== Категории =====
CATEGORY_KEYWORDS = {
    "Мясо": ["говядин","баранин","свинин","телятин","мяс","фарш","вырезк","стейк",
             "бекон","ветчин","ребр","шея","плечо","окорок","корейк","рибай","флэнк","фланк","порос"],
    "Птица": ["кур","индейк","утк","цыпл","цыплят","бройл","бедро","грудк","крылыш","окороч","печень кур","сердечк","желудк"],
    "Рыба/морепродукты": ["лосос","семг","форел","сибас","дорадо","тунец","треск","хек","окун","щук","скумбр",
                          "камбал","анчоус","сельд","кревет","мид","кальмар","осьминог","осьминоги","гребеш","краб","устриц","масляная рыба"],
    "Сыр": ["сыр","моцарелл","пармез","бри","фет","чеддер","горгонзол","маскарпон","рикотт",
            "сулугуни","брынз","эмментал","дорблю","камамбер","плавлен","сливочный сыр","крем-сыр","гауд","халум","халуми"],
    "Молочка": ["сливк","масло слив","молок","йогурт","сметан","творог","ряженк","кефир","сгущен","сыворотк"],
    "Фрукты/овощи": ["помид","томат","огур","лук","картоф","капуст","перец","баклаж","кабач","цуккин","морков","свекл","чеснок",
                     "имбир","зелень","укроп","петруш","кинз","базилик","шпинат","сельдер","рукол","фенхел",
                     "лимон","лайм","апельс","яблок","груш","манго","виноград","ананас","гранат","киви","авокадо","черри",
                     "маслин","олив","горошек","броккол","айсберг","вешен","розмар","эстрагон","тархун","мят","вишн","клубник","спарж"],
    "Бакалея": ["мук","сахар","соль","рис","круп","греч","овсян","макарон","какао","дрожж","крахмал","кускус","булгур","чечевиц",
                "нут","фасол","паниров","ванили","разрыхл","сода","орех","семеч","изюм","шоколад","сироп","масло раст","оливков",
                "панко","уксус","яйц","желток","белок","стружк кокос","хондаши","бадьян","ореган","тимьян","чабрец","кориандр",
                "паприк","фисташ","каперс","кунжут","бульон"],
    "Хлеб/выпечка": ["лаваш","булк","булочк","хлеб","лепеш","тортиль","пита","багет","чиабат","тесто","слоен",
                    "бургер бул","булочки для бургера","тортилья"],
    "Соусы": ["соус","кетчуп","горчиц","майонез","паст томат","аджик","соев","терияк","табаск","тартар",
              "песто","цезар","хойсин","устрич","васаб","деми","барбекю","ткемал","сальс"],
    "Прочее": []
}
KNOWN_CATS = list(CATEGORY_KEYWORDS.keys())
RU_MONTHS = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}

def detect_category(name: str) -> str:
    s = str(name).lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if cat == "Прочее": continue
        for k in keys:
            if k in s:
                return cat
    return "Прочее"

def normalize_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
              .str.replace("\u00a0", " ", regex=False)   # NBSP
              .str.replace(" ", "", regex=False)         # thousand sep
              .str.replace(",", ".", regex=False),       # comma → dot
        errors="coerce"
    )

@st.cache_data(show_spinner=True)
def load_data_by_positions(url: str) -> pd.DataFrame:
    # читаем CSV (и на случай ; вместо ,)
    try:
        raw = pd.read_csv(url, header=0, dtype=str)
    except Exception:
        raw = pd.read_csv(url, header=0, dtype=str, sep=";")

    # если файл с «шапкой» выше заголовков — просто используем позиции
    # переводим 1-базные индексы в 0-базные
    d, e, f, g, n = COL_D-1, COL_E-1, COL_F-1, COL_G-1, COL_N-1
    ncols = raw.shape[1]
    if max(d,e,f,g,n) >= ncols:
        # защита: если колонок меньше, покажем диагностику
        return pd.DataFrame()

    # собираем рабочий датафрейм (D+E → Товар)
    prod = raw.iloc[:, d].fillna("") + " " + raw.iloc[:, e].fillna("")
    prod = prod.str.strip()

    unit = raw.iloc[:, f] if f < ncols else ""
    qty  = raw.iloc[:, g] if g < ncols else ""
    cost = raw.iloc[:, n] if n < ncols else ""

    df = pd.DataFrame({
        "Товар": prod,
        "Ед. изм.": unit,
        "Количество": normalize_numeric(qty),
        "Стоимость":  normalize_numeric(cost),
        # «Курсы» и «Дата» в твоём CSV отсутствуют — ставим пусто
        "Курсы": "",
        "Дата":  pd.NaT,
    })

    # чистим пустые товары
    df = df[df["Товар"].astype(str).str.strip() != ""].copy()

    # категоризация
    df["Категория"] = df["Товар"].apply(detect_category)

    # год/месяц (нет дат — будут NaN, фильтр по месяцам просто не появится)
    df["Год"] = pd.to_datetime(df["Дата"], errors="coerce").dt.year
    df["Месяц"] = pd.to_datetime(df["Дата"], errors="coerce").dt.month

    return df

df = load_data_by_positions(GOOGLE_SHEET_URL)

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

with st.expander("📋 Диагностика данных"):
    st.write("Первые строки после позиционного чтения (D+E,F,G,N):")
    st.dataframe(df.head(20), use_container_width=True)
    st.write("Колонки:", list(df.columns))
    st.write("Размер:", df.shape)

if df.empty:
    st.error("Не удалось прочитать данные по позициям D+E (товар), F (ед.), G (кол-во), N (стоимость). Проверь, что опубликован нужный лист Google Sheets и структура колонок совпадает.")
    st.stop()

# ===== Фильтры =====
with st.sidebar:
    st.header("Фильтры")
    has_dates = df["Месяц"].notna().any() and df["Год"].notna().any()
    if has_dates:
        years  = sorted(df["Год"].dropna().unique().tolist())
        months = sorted([int(m) for m in df["Месяц"].dropna().unique().tolist() if 1 <= int(m) <= 12])
        selected_year  = st.selectbox("Год", options=years, index=len(years)-1)
        selected_month = st.selectbox("Месяц закупки", options=months, index=len(months)-1,
                                      format_func=lambda m: RU_MONTHS.get(int(m), str(m)))
    else:
        selected_year, selected_month = None, None

    # курсы в этом источнике пустые — фильтр не показываем, если нечего выбирать
    exploded = df["Курсы"].dropna().astype(str).str.split(",").explode().str.strip()
    course_opts = sorted([c for c in exploded.unique().tolist() if c])
    selected_course = st.multiselect("Выберите курсы", options=course_opts) if course_opts else []

    unit_opts = sorted(df["Ед. изм."].dropna().astype(str).unique().tolist())
    selected_unit = st.multiselect("Единица измерения", options=unit_opts)

    cat_opts = sorted(df["Категория"].dropna().astype(str).unique().tolist())
    selected_category = st.multiselect("Категория", options=cat_opts)

filtered = df.copy()
if selected_year is not None and selected_month is not None:
    filtered = filtered[(filtered["Год"] == selected_year) & (filtered["Месяц"] == selected_month)]
if selected_course:
    filtered = filtered[filtered["Курсы"].fillna("").apply(
        lambda s: any(c in [x.strip() for x in str(s).split(",")] for c in selected_course)
    )]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].astype(str).isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].astype(str).isin(selected_category)]

if filtered.empty:
    st.info("По текущим фильтрам данных нет.")
    st.stop()

# ===== Сводка по продуктам =====
st.subheader("📦 Сводка по продуктам")
grouped = (
    filtered.groupby(["Товар","Ед. изм.","Категория"], dropna=False)
    .agg({"Стоимость":"sum","Количество":"sum","Курсы":lambda x: ", ".join(sorted(set(map(str, x))))})
    .reset_index()
    .sort_values("Стоимость", ascending=False)
)
st.dataframe(grouped, use_container_width=True)

# ===== Графики =====
st.subheader("💰 Топ-10 продуктов по стоимости")
top_costs = grouped.head(10)
if not top_costs.empty:
    fig, ax = plt.subplots(figsize=(10,5))
    sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
    ax.set_title("Топ-10 дорогих продуктов")
    st.pyplot(fig)
else:
    st.write("Нет данных для отображения.")

st.subheader("⚖️ Топ-10 продуктов по количеству")
top_qty = grouped.sort_values(by="Количество", ascending=False).head(10)
if not top_qty.empty:
    fig2, ax2 = plt.subplots(figsize=(10,5))
    sns.barplot(x="Количество", y="Товар", data=top_qty, ax=ax2)
    ax2.set_title("Топ-10 по количеству")
    st.pyplot(fig2)
else:
    st.write("Нет данных для отображения.")

# ===== Категории =====
st.subheader("🏷️ Категории — расходы и количество")
cat_agg = (
    filtered.groupby("Категория", dropna=False)
    .agg({"Стоимость":"sum","Количество":"sum"})
    .reset_index()
    .sort_values("Стоимость", ascending=False)
)
col1, col2 = st.columns(2)
with col1:
    fig3, ax3 = plt.subplots(figsize=(6,4))
    sns.barplot(x="Стоимость", y="Категория", data=cat_agg.head(10), ax=ax3)
    ax3.set_xlabel("Стоимость"); ax3.set_ylabel("")
    ax3.set_title("Топ категорий по стоимости")
    st.pyplot(fig3)
with col2:
    fig4, ax4 = plt.subplots(figsize=(6,4))
    sns.barplot(x="Количество", y="Категория", data=cat_agg.sort_values("Количество", ascending=False).head(10), ax=ax4)
    ax4.set_xlabel("Количество"); ax4.set_ylabel("")
    ax4.set_title("Топ категорий по количеству")
    st.pyplot(fig4)

# ===== Итоги =====
st.subheader("📈 Общая статистика")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
c2.metric("Всего строк", f"{filtered.shape[0]:,}")
c3.metric("Уникальных продуктов", f"{grouped[['Товар','Ед. изм.']].drop_duplicates().shape[0]:,}")
if filtered["Месяц"].notna().any() and filtered["Год"].notna().any():
    period_text = f"{RU_MONTHS.get(int(filtered['Месяц'].dropna().iloc[0]), filtered['Месяц'].dropna().iloc[0])} {int(filtered['Год'].dropna().iloc[0])}"
    c4.metric("Период выборки", period_text)
else:
    c4.metric("Период выборки", "—")

# ===== Инспектор «Прочее» =====
st.subheader("❓ Прочее — что ещё не распознано словарём")
other = filtered[filtered["Категория"] == "Прочее"]
if other.empty:
    st.success("Отлично! Все позиции классифицированы.")
else:
    other_top = (
        other.groupby(["Товар"], dropna=False)
        .agg({"Стоимость":"sum","Ед. изм.": lambda x: ", ".join(sorted(set(map(str, x)))),"Курсы": lambda x: ", ".join(sorted(set(map(str, x))))})
        .reset_index()
        .rename(columns={"Ед. изм.":"Ед. изм. (варианты)"})
        .sort_values("Стоимость", ascending=False)
        .head(50)
    )
    st.write("Подскажи категории для позиций ниже — добавлю триггеры в словарь:")
    st.dataframe(other_top, use_container_width=True)
