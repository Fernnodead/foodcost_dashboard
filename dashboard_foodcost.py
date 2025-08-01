import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Загрузка данных (предполагается, что уже агрегированы)
@st.cache_data
def load_data():
    df = pd.read_excel("Фудкост.xlsx", sheet_name=None, skiprows=6)
    all_detailed = []
    for sheet, data in df.items():
        if sheet in ["Фудкост", "Цены с новым фудкостом"]:
            continue
        temp = data.rename(columns={
            data.columns[3]: "Товар",
            data.columns[5]: "Ед. изм.",
            data.columns[6]: "Количество",
            data.columns[8]: "Стоимость"
        })
        temp = temp[["Товар", "Ед. изм.", "Количество", "Стоимость"]]
        temp = temp.dropna()
        temp["Курс"] = sheet
        temp["Стоимость"] = pd.to_numeric(temp["Стоимость"], errors="coerce")
        temp["Количество"] = pd.to_numeric(temp["Количество"], errors="coerce")
        temp = temp[(temp["Стоимость"] < 0) & (temp["Количество"] > 0)]
        temp["Стоимость"] = temp["Стоимость"].abs()
        all_detailed.append(temp)
    return pd.concat(all_detailed, ignore_index=True)

df = load_data()

st.title("📊 Дэшборд по фудкосту кулинарных курсов")

# Фильтры
with st.sidebar:
    st.header("Фильтры")
    selected_course = st.multiselect("Выберите курсы", options=sorted(df["Курс"].unique()))
    selected_unit = st.multiselect("Единица измерения", options=sorted(df["Ед. изм."].unique()))

filtered = df.copy()
if selected_course:
    filtered = filtered[filtered["Курс"].isin(selected_course)]
if selected_unit:
    filtered = filtered[filtered["Ед. изм."].isin(selected_unit)]

# Группировка
grouped = (
    filtered.groupby(["Товар", "Ед. изм."])
    .agg({"Стоимость": "sum", "Количество": "sum", "Курс": lambda x: ", ".join(sorted(set(x)))})
    .reset_index()
    .rename(columns={"Курс": "Курсы"})
)

# Основная таблица
st.subheader("📦 Сводка по продуктам")
st.dataframe(grouped.sort_values(by="Стоимость", ascending=False), use_container_width=True)

# Визуализация
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

# Итоги
st.subheader("📈 Общая статистика")
st.metric("Общая стоимость", f"{filtered['Стоимость'].sum():,.2f} ₽")
st.metric("Всего позиций", filtered.shape[0])
st.metric("Уникальных продуктов", grouped.shape[0])
