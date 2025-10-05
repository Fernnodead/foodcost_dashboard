# foodcost_dashboard_multi_sheets.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="Фудкост — дэшборд (мульти-листы)", layout="wide")

# ===== Колонки по позициям (1-базные) =====
COL_D, COL_E, COL_F, COL_G, COL_N = 4, 5, 6, 7, 14  # D, E, F, G, N

# ===== Категории =====
CATEGORY_KEYWORDS = {
    "Мясо": ["говядин","баранин","свинин","телятин","мяс","фарш","вырезк","стейк","бекон","ветчин","ребр","шея","плечо","окорок","корейк","рибай","флэнк","фланк","порос"],
    "Птица": ["кур","индейк","утк","цыпл","цыплят","бройл","бедро","грудк","крылыш","окороч","печень кур","сердечк","желудк"],
    "Рыба/морепродукты": ["лосос","семг","форел","сибас","дорадо","тунец","треск","хек","окун","щук","скумбр","камбал","анчоус","сельд","кревет","мид","кальмар","осьминог","осьминоги","гребеш","краб","устриц","масляная рыба"],
    "Сыр": ["сыр","моцарелл","пармез","бри","фет","чеддер","горгонзол","маскарпон","рикотт","сулугуни","брынз","эмментал","дорблю","камамбер","плавлен","сливочный сыр","крем-сыр","гауд","халум","халуми"],
    "Молочка": ["сливк","масло слив","молок","йогурт","сметан","творог","ряженк","кефир","сгущен","сыворотк"],
    "Фрукты/овощи": ["помид","томат","огур","лук","картоф","капуст","перец","баклаж","кабач","цуккин","морков","свекл","чеснок","имбир","зелень","укроп","петруш","кинз","базилик","шпинат","сельдер","рукол","фенхел","лимон","лайм","апельс","яблок","груш","манго","виноград","ананас","гранат","киви","авокадо","черри","маслин","олив","горошек","броккол","айсберг","вешен","розмар","эстрагон","тархун","мят","вишн","клубник","спарж"],
    "Бакалея": ["мук","сахар","соль","рис","круп","греч","овсян","макарон","какао","дрожж","крахмал","кускус","булгур","чечевиц","нут","фасол","паниров","ванили","разрыхл","сода","орех","семеч","изюм","шоколад","сироп","масло раст","оливков","панко","уксус","яйц","желток","белок","стружк кокос","хондаши","бадьян","ореган","тимьян","чабрец","кориандр","паприк","фисташ","каперс","кунжут","бульон"],
    "Хлеб/выпечка": ["лаваш","булк","булочк","хлеб","лепеш","тортиль","пита","багет","чиабат","тесто","слоен","бургер бул","булочки для бургера","тортилья"],
    "Соусы": ["соус","кетчуп","горчиц","майонез","паст томат","аджик","соев","терияк","табаск","тартар","песто","цезар","хойсин","устрич","васаб","деми","барбекю","ткемал","сальс"],
    "Прочее": []
}
RU_MONTHS = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}

def detect_category(name: str) -> str:
    s = str(name).lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if cat == "Прочее": continue
        for k in keys:
            if k in s: return cat
    return "Прочее"

def normalize_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("\u00a0"," ", regex=False).str.replace(" ","", regex=False).str.replace(",",".", regex=False),
        errors="coerce"
    )

def guess_course_from_url(url: str, fallback: str) -> str:
    # попытаемся вытащить gid, чтобы различать листы
    try:
        q = parse_qs(urlparse(url).query)
        gid = q.get("gid", [""])[0]
        return f"{fallback} (gid={gid})" if gid else fallback
    except Exception:
        return fallback

@st.cache_data(show_spinner=True)
def read_sheet_by_positions(url: str) -> pd.DataFrame:
    # читаем CSV (пробуем и ; как разделитель)
    try:
        raw = pd.read_csv(url, header=0, dtype=str)
    except Exception:
        raw = pd.read_csv(url, header=0, dtype=str, sep=";")
    # позиции (0-базные)
    d, e, f, g, n = COL_D-1, COL_E-1, COL_F-1, COL_G-1, COL_N-1
    ncols = raw.shape[1]
    if max(d,e,f,g,n) >= ncols:
        return pd.DataFrame()  # структура не совпала
    prod = (raw.iloc[:, d].fillna("") + " " + raw.iloc[:, e].fillna("")).str.strip()
    unit = raw.iloc[:, f] if f < ncols else ""
    qty  = raw.iloc[:, g] if g < ncols else ""
    cost = raw.iloc[:, n] if n < ncols else ""
    df = pd.DataFrame({
        "Товар": prod,
        "Ед. изм.": unit,
        "Количество": normalize_numeric(qty),
        "Стоимость": normalize_numeric(cost),
        "Дата": pd.NaT
    })
    df = df[df["Товар"].astype(str).str.strip() != ""].copy()
    df["Категория"] = df["Товар"].apply(detect_category)
    df["Год"] = pd.NaT
    df["Месяц"] = pd.NaT
    return df

# ---------- UI: список листов ----------
st.sidebar.header("Источники (листы Google Sheets)")
urls_text = st.sidebar.text_area(
    "Вставь ссылки CSV по одному на строку (начиная с «Экспресс интенсив» и дальше):",
    value="https://docs.google.com/spreadsheets/d/e/2PACX-1vT0eKDqy05ncTpiWM0oFxv-dthUJ53rPIMf5A-NFCBAJSrLEDRjHdpz2eNnmR192e5eZMD05Ua4bMD7/pub?gid=0&single=true&output=csv",
    height=150
)
courses_text = st.sidebar.text_area(
    "Имена курсов (опционально, по одному на строку, в той же очередности):",
    value="Экспресс интенсив",
    height=100
)
urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
course_names = [c.strip() for c in courses_text.splitlines() if c.strip()]
while len(course_names) < len(urls):
    course_names.append(guess_course_from_url(urls[len(course_names)], f"Курс #{len(course_names)+1}"))

# ---------- Загрузка всех листов ----------
frames = []
for url, cname in zip(urls, course_names):
    df_sheet = read_sheet_by_positions(url)
    if df_sheet.empty:
        continue
    df_sheet["Курсы"] = cname
    frames.append(df_sheet)

df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата","Год","Месяц"])

st.title("📊 Дэшборд по фудкосту кулинарных курсов (мульти-листы)")

with st.expander("📋 Диагностика"):
    st.write("Кол-во источников:", len(urls))
    st.write("Первые строки:")
    st.dataframe(df.head(20), use_container_width=True)
    st.write("Размер:", df.shape)

if df.empty:
    st.error("Не удалось прочитать данные. Проверь, что каждый лист опубликован как CSV, и структура колонок соответствует (D+E, F, G, N).")
    st.stop()

# ---------- Фильтры ----------
with st.sidebar:
    st.header("Фильтры")
    course_opts = sorted(df["Курсы"].dropna().unique().tolist())
    selected_course = st.multiselect("Курсы", options=course_opts)
    unit_opts = sorted(df["Ед. изм."].dropna().astype(str).unique().tolist())
    selected_unit = st.multiselect("Ед. изм.", options=unit_opts)
    cat_opts = sorted(df["Категория"].dropna().astype(str).unique().tolist())
    selected_category = st.multiselect("Категория", options=cat_opts)

filtered = df.copy()
if selected_course:
    filtered = filtered[filtered["Курсы"].isin(selected_course)]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].astype(str).isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].astype(str).isin(selected_category)]

if filtered.empty:
    st.info("По текущим фильтрам данных нет.")
    st.stop()

# ---------- Сводка по продуктам ----------
st.subheader("📦 Сводка по продуктам")
grouped = (
    filtered.groupby(["Товар","Ед. изм.","Категория"], dropna=False)
    .agg({"Стоимость":"sum","Количество":"sum","Курсы":lambda x: ", ".join(sorted(set(map(str, x))))})
    .reset_index()
    .sort_values("Стоимость", ascending=False)
)
st.dataframe(grouped, use_container_width=True)

# ---------- Графики ----------
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

# ---------- Категории ----------
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

# ---------- Итоги ----------
st.subheader("📈 Общая статистика")
c1, c2, c3 = st.columns(3)
c1.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
c2.metric("Всего строк", f"{filtered.shape[0]:,}")
c3.metric("Уникальных продуктов", f"{grouped[['Товар','Ед. изм.']].drop_duplicates().shape[0]:,}")

# ---------- Инспектор «Прочее» ----------
st.subheader("❓ Прочее — что ещё не распознано словарём")
other = filtered[filtered["Категория"] == "Прочее"]
if other.empty:
    st.success("Отлично! Все позиции классифицированы.")
else:
    other_top = (
        other.groupby(["Товар","Курсы"], dropna=False)
        .agg({"Стоимость":"sum","Ед. изм.": lambda x: ", ".join(sorted(set(map(str, x))))})
        .reset_index()
        .rename(columns={"Ед. изм.":"Ед. изм. (варианты)"})
        .sort_values("Стоимость", ascending=False)
        .head(50)
    )
    st.write("Уточни категории для этих позиций — добавлю в словарь:")
    st.dataframe(other_top, use_container_width=True)
