# foodcost_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re

st.set_page_config(page_title="Фудкост — дэшборд", layout="wide")

# ===== 1) ВСТАВЬ ССЫЛКУ НА GOOGLE SHEETS (Publish to Web → CSV) =====
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0eKDqy05ncTpiWM0oFxv-dthUJ53rPIMf5A-NFCBAJSrLEDRjHdpz2eNnmR192e5eZMD05Ua4bMD7/pub?output=csv"

# ===== Категории (расширенные) =====
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

# ===== Умная загрузка CSV с поиском строки заголовков и колонок =====
TARGETS = {
    "Товар":      [r"товар", r"наимен", r"product", r"item", r"ingr", r"name"],
    "Ед. изм.":   [r"ед", r"ед\.*\s*изм", r"unit"],
    "Стоимость":  [r"стоим", r"сумм", r"amount", r"price", r"отпуск"],
    "Количество": [r"кол", r"qty", r"кол-во", r"kol", r"колич"],
    "Курсы":      [r"курс", r"курсы", r"course", r"class"]
}

def _best_header_row(df_raw: pd.DataFrame, max_scan: int = 30) -> int | None:
    # ищем строку, где больше всего совпадений с нужными заголовками
    best_idx, best_score = None, -1
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i].astype(str).str.lower().fillna("")
        score = 0
        for cell in row:
            for pats in TARGETS.values():
                if any(re.search(p, cell) for p in pats):
                    score += 1; break
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx if best_score > 0 else None

def _find_col(df: pd.DataFrame, target_key: str) -> str | None:
    pats = TARGETS[target_key]
    cols = list(df.columns)
    # 1) прямые совпадения по названию
    for c in cols:
        cl = str(c).lower()
        if any(re.search(p, cl) for p in pats):
            return c
    # 2) эвристики: для стоимости часто есть «Отпускные суммы»
    if target_key == "Стоимость":
        for pref in ["Отпускные суммы"]:
            if pref in cols:
                return pref
    return None

def read_google_csv_smart(url: str) -> pd.DataFrame:
    if not url or "output=csv" not in url:
        raise ValueError("Ссылка должна быть в формате Google Sheets CSV (…output=csv).")
    # 1) пробуем стандартно
    try:
        df0 = pd.read_csv(url, dtype=str)
    except Exception:
        # иногда ; вместо ,
        df0 = pd.read_csv(url, dtype=str, sep=";")

    # если всё склеилось в одну колонку — пробуем альтернативный sep
    if df0.shape[1] == 1 and df0.iloc[:,0].str.contains(",").any():
        df0 = pd.read_csv(url, dtype=str, sep=",")

    # 2) найдём строку заголовка
    header_idx = _best_header_row(df0)
    if header_idx is not None:
        try:
            df = pd.read_csv(url, header=header_idx)
        except Exception:
            df = pd.read_csv(url, header=header_idx, sep=";")
    else:
        df = df0.copy()
        # попытаемся поднять первую строку как заголовки, если похоже на заголовок
        if df.shape[0] > 0:
            maybe_header = df.iloc[0].astype(str).str.lower().tolist()
            if any(re.search(r"товар|стоим|кол", c) for c in maybe_header):
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)

    # 3) приведём колонки к нужным именам по шаблонам
    col_map = {}
    for need in TARGETS.keys():
        found = _find_col(df, need)
        if found: col_map[found] = need
    df = df.rename(columns=col_map)

    # 4) если ключевых столбцов всё ещё нет — добавим пустые
    for must in ["Товар","Ед. изм.","Стоимость","Количество"]:
        if must not in df.columns:
            df[must] = np.nan
    if "Курсы" not in df.columns:
        # иногда «Курс»
        if "Курс" in df.columns:
            df["Курсы"] = df["Курс"].astype(str)
        else:
            df["Курсы"] = ""

    # 5) чистка и типы
    # заменим запятые на точки в числовых, уберём пробелы-тысячные
    for num in ["Стоимость","Количество"]:
        df[num] = (
            df[num]
            .astype(str)
            .str.replace("\u00a0", " ", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[num] = pd.to_numeric(df[num], errors="coerce")

    # дата (если есть)
    if "Дата" in df.columns:
        df["Дата"] = pd.to_datetime(df["Дата"], errors="coerce", dayfirst=True)
    else:
        df["Дата"] = pd.NaT

    # фильтр пустых товаров
    df = df[df["Товар"].notna() & (df["Товар"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)

@st.cache_data(show_spinner=True)
def load_data(url: str) -> pd.DataFrame:
    df = read_google_csv_smart(url)
    # рекатегоризация
    detected = df["Товар"].apply(detect_category)
    orig = df.get("Категория", pd.Series(index=df.index, dtype=object)).astype(str).str.strip()
    use_orig = orig.isin(KNOWN_CATS) & detected.eq("Прочее")
    df["Категория"] = np.where(use_orig, orig, detected)

    # год/месяц
    df["Год"] = df["Дата"].dt.year
    df["Месяц"] = df["Дата"].dt.month
    return df[["Товар","Ед. изм.","Категория","Стоимость","Количество","Курсы","Дата","Год","Месяц"]]

# ======== ЗАГРУЗКА ========
try:
    df = load_data(GOOGLE_SHEET_URL)
except Exception as e:
    st.error(f"Не удалось загрузить Google Sheet: {e}")
    st.stop()

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

with st.expander("📋 Диагностика данных"):
    st.write("Первые строки:")
    st.dataframe(df.head(20), use_container_width=True)
    st.write("Колонки:", list(df.columns))
    st.write("Размер:", df.shape)

if df.empty:
    st.warning("В таблице не найдено строк с товарами. Проверь: публикуется ли нужный ЛИСТ и есть ли в нём колонки «Товар/Стоимость/Количество».")
    st.stop()

# ======== Фильтры ========
with st.sidebar:
    st.header("Фильтры")
    # месяц/год, только если даты есть
    has_dates = df["Месяц"].notna().any() and df["Год"].notna().any()
    if has_dates:
        years  = sorted(df["Год"].dropna().unique().tolist())
        months = sorted([int(m) for m in df["Месяц"].dropna().unique().tolist() if 1 <= int(m) <= 12])
        selected_year  = st.selectbox("Год", options=years, index=len(years)-1)
        selected_month = st.selectbox("Месяц закупки", options=months, index=len(months)-1,
                                      format_func=lambda m: RU_MONTHS.get(int(m), str(m)))
    else:
        selected_year, selected_month = None, None

    # курсы — распакуем склейку
    exploded = df["Курсы"].dropna().astype(str).str.split(",").explode().str.strip()
    course_opts = sorted([c for c in exploded.unique().tolist() if c])
    selected_course = st.multiselect("Выберите курсы", options=course_opts)

    unit_opts = sorted(df["Ед. изм."].dropna().astype(str).unique().tolist())
    selected_unit = st.multiselect("Ед. изм.", options=unit_opts)

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

# ======== Таблица по продуктам ========
st.subheader("📦 Сводка по продуктам")
grouped = (
    filtered.groupby(["Товар","Ед. изм.","Категория"], dropna=False)
    .agg({"Стоимость":"sum","Количество":"sum","Курсы":lambda x: ", ".join(sorted(set(map(str, x))))})
    .reset_index()
    .sort_values("Стоимость", ascending=False)
)
st.dataframe(grouped, use_container_width=True)

# ======== Графики ========
st.subheader("💰 Топ-10 продуктов по стоимости")
top_costs = grouped.head(10)
if not top_costs.empty:
    fig, ax = plt.subplots(figsize=(10,5))
    sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
    ax.set_title("Топ-10 дорогих продуктов")
    st.pyplot(fig)

st.subheader("⚖️ Топ-10 продуктов по количеству")
top_qty = grouped.sort_values(by="Количество", ascending=False).head(10)
if not top_qty.empty:
    fig2, ax2 = plt.subplots(figsize=(10,5))
    sns.barplot(x="Количество", y="Товар", data=top_qty, ax=ax2)
    ax2.set_title("Топ-10 по количеству")
    st.pyplot(fig2)

# ======== Категории ========
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

# ======== Итоги ========
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

# ======== Инспектор «Прочее» ========
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
    st.write("Подскажи категории для позиций ниже — добавлю в словарь:")
    st.dataframe(other_top, use_container_width=True)
