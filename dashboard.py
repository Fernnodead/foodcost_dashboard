import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

# Классификатор по ключевым словам
CATEGORY_KEYWORDS = {
    "Мясо": ["говядина", "баранина", "свинина", "мясо", "фарш"],
    "Птица": ["кур", "индейк", "утк", "бедро", "грудк"],
    "Рыба/морепродукты": ["лосось", "тунец", "дорадо", "филе", "креветк", "кальмар", "треск", "форель", "сибас", "рыб"],
    "Сыр": ["сыр", "моцарелла", "пармезан", "фета", "бри"],
    "Молочка": ["сливк", "масло", "молок", "йогурт", "сметан"],
    "Фрукты/овощи": ["помид", "томат", "огур", "лук", "картоф", "лимон", "яблок", "апельс", "зелень", "капуст", "перец", "баклажан", "фрукт", "овощ", "манго", "виноград", "гранат", "груша", "ананас", "морков"],
    "Бакалея": ["мука", "сахар", "соль", "рис", "крупа", "спец", "масло", "гречк", "овсян", "макарон", "какао"],
    "Хлеб/выпечка": ["лаваш", "булк", "хлеб", "лепеш", "тортиль", "пита", "багет"],
    "Соусы": ["соус", "кетчуп", "горчиц", "майонез", "паста", "аджик"],
    "Прочее": []
}

def assign_category(product):
    name = product.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return category
    return "Прочее"

@st.cache_data
def load_data():
    df = pd.read_excel("Фудкост.xlsx", sheet_name=None, skiprows=6)
    all_detailed = []
    for sheet, data in df.items():
        if sheet in ["Фудкост", "Цены с новым фудкостом"]:
            continue
        if data.shape[1] < 9:
            continue
        try:
            current_date = None
            for i in range(len(data)):
                row_text = str(data.iloc[i, 1])
                match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", row_text)
                if match:
                    current_date = pd.to_datetime(match.group(0), dayfirst=True)
                if pd.notna(data.iloc[i, 3]) and isinstance(data.iloc[i, 3], str):
                    row = {
                        "Товар": data.iloc[i, 3],
                        "Ед. изм.": data.iloc[i, 5],
                        "Количество": pd.to_numeric(data.iloc[i, 6], errors="coerce"),
                        "Стоимость": pd.to_numeric(data.iloc[i, 8], errors="coerce"),
                        "Курс": sheet,
                        "Дата": current_date
                    }
                    all_detailed.append(row)
        except Exception as e:
            print(f"Ошибка при обработке листа '{sheet}': {e}")
            continue
    df_final = pd.DataFrame(all_detailed)
    df_final = df_final.dropna(subset=["Товар", "Стоимость", "Количество"])
    df_final = df_final[(df_final["Стоимость"] < 0) & (df_final["Количество"] > 0)]
    df_final["Стоимость"] = df_final["Стоимость"].abs()
    df_final["Категория"] = df_final["Товар"].apply(assign_category)
    df_final["Месяц"] = df_final["Дата"].dt.to_period("M").astype(str)
    return df_final

# Загрузка данных
df = load_data()

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

# Фильтры
with st.sidebar:
    st.header("Фильтры")
    selected_course = st.multiselect("Выберите курсы", options=sorted(df["Курс"].dropna().unique()))
    selected_unit = st.multiselect("Единица измерения", options=sorted(df["Ед. изм."].dropna().unique()))
    selected_category = st.multiselect("Категория", options=sorted(df["Категория"].dropna().unique()))
    selected_month = st.selectbox("Месяц закупки", options=sorted(df["Месяц"].dropna().unique()), index=len(df["Месяц"].unique())-1)

# Применение фильтров
filtered = df.copy()
if selected_course:
    filtered = filtered[filtered["Курс"].isin(selected_course)]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].isin(selected_unit)]
if selected_category:
    filtered = filtered[filtered["Категория"].isin(selected_category)]
if selected_month:
    filtered = filtered[filtered["Месяц"] == selected_month]

# Группировка
grouped = (
    filtered.groupby(["Товар", "Ед. изм.", "Категория"])
    .agg({"Стоимость": "sum", "Количество": "sum", "Курс": lambda x: ", ".join(sorted(set(x)))})
    .reset_index()
    .rename(columns={"Курс": "Курсы"})
)

# Таблица
st.subheader("📦 Сводка по продуктам")
st.dataframe(grouped.sort_values(by="Стоимость", ascending=False), use_container_width=True)

# Топ по стоимости
st.subheader("💰 Топ-10 продуктов по стоимости")
top_costs = grouped.sort_values(by="Стоимость", ascending=False).head(10)
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(x="Стоимость", y="Товар", data=top_costs, ax=ax)
ax.set_title("Топ-10 дорогих продуктов")
st.pyplot(fig)

# Топ по количеству
st.subheader("⚖️ Топ-10 продуктов по количеству")
top_qty = grouped.sort_values(by="Количество", ascending=False).head(10)
fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(x="Количество", y="Товар", data=top_qty, ax=ax2)
ax2.set_title("Топ-10 продуктов по количеству")
st.pyplot(fig2)

# Самый дорогой продукт месяца
st.subheader(f"💎 Самый дорогой продукт за {selected_month}")
if not filtered.empty:
    top_item = filtered.groupby("Товар")["Стоимость"].sum().sort_values(ascending=False).idxmax()
    top_value = filtered.groupby("Товар")["Стоимость"].sum().max()
    st.markdown(f"**{top_item}** — {top_value:,.2f} ₽")
else:
    st.write("Нет данных за выбранный месяц.")

# Общая статистика
st.subheader("📈 Общая статистика")
st.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
st.metric("Всего позиций", filtered.shape[0])
st.metric("Уникальных продуктов", grouped.shape[0])
