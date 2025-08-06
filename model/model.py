from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sqlalchemy import create_engine
import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler

credenciales_felipe = "mysql+pymysql://root:Enero182005%@127.0.0.1:3306/gold"
engine = create_engine(credenciales_felipe, echo=True)

df=pd.read_sql_query("SELECT*FROM risk_level_data",engine)
categoricas = df.select_dtypes("object").columns
df_processed = pd.get_dummies(df, columns=categoricas)

X=df_processed.drop("TARGET",axis=1)
y=df["TARGET"]
model_columns = X.columns.tolist()
scaler = StandardScaler()
X = scaler.fit_transform(X)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42,class_weight='balanced')
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nReporte de Clasificación:")
print(classification_report(y_test, y_pred))


mapa_riesgo = ['Riesgo Alto','Riesgo Medio','Riesgo Bajo']

with open('risk_columns.pkl', 'wb') as columns:
    pickle.dump(model_columns, columns)

# Guardar el modelo
with open("risk_classifer_model.pickle", "wb") as model_file:
    pickle.dump(model, model_file)

# Guardar el mapeo de clases (uniques)
with open("risk_classifer_output.pickle", "wb") as mapping_file:
    pickle.dump(mapa_riesgo, mapping_file)