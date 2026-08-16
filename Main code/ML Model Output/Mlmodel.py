import pickle
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.neighbors import KNeighborsClassifier

# -----------------------------
# 1. LOAD DATA
# -----------------------------
with open(r"C:\Major Project\sign-language-detector-python-master\data.pickle", "rb") as f:
    data = pickle.load(f)

if isinstance(data, dict):
    X = data.get("X", data.get("data"))
    y = data.get("y", data.get("labels"))
elif isinstance(data, (list, tuple)):
    X, y = data
else:
    raise ValueError("Unsupported format")

X = np.array(X)
y = np.array(y)

# -----------------------------
# 2. REMOVE SPECIFIC EXERCISES
# -----------------------------
exclude_classes = [
    "Extending_the_wrist_down",
    "Extending_the_wrist_relax",
    "Extending_the_wrist_up",
    "Finger_flexion_with_ball_compress",
    "Finger_flexion_with_ball_relax",
    "Turning_a_bottle_left",
    "Turning_a_bottle_relax",
    "Turning_a_bottle_right"
]

y_clean = np.array([label.strip() for label in y])
mask = ~np.isin(y_clean, exclude_classes)

X = X[mask]
y = y_clean[mask]

print("\nRemaining Classes:\n", np.unique(y))

# -----------------------------
# 3. ENCODE LABELS
# -----------------------------
le = LabelEncoder()
y_encoded = le.fit_transform(y)
class_names = le.classes_

# -----------------------------
# 4. SHORT LABEL FUNCTION
# -----------------------------
def short_label(label):
    return "".join([word[0].upper() for word in label.split("_")])

short_labels = [short_label(lbl) for lbl in class_names]

print("\nLabel Mapping:")
for f, s in zip(class_names, short_labels):
    print(f"{f} → {s}")

# -----------------------------
# 5. TRAIN TEST SPLIT
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

# -----------------------------
# ⚠️ 6. FEATURE SCALING (IMPORTANT)
# -----------------------------
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# -----------------------------
# 7. TRAIN KNN MODEL
# -----------------------------
model = KNeighborsClassifier(n_neighbors=5)
model.fit(X_train, y_train)

# -----------------------------
# 8. PREDICT
# -----------------------------
y_pred = model.predict(X_test)

# -----------------------------
# 9. CLASSIFICATION REPORT
# -----------------------------
print("\n===== CLASSIFICATION REPORT (KNN) =====")
print(classification_report(y_test, y_pred, target_names=class_names))

# -----------------------------
# 10. CONFUSION MATRIX
# -----------------------------
cm = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(10, 8))

# Blue-white color map
plt.imshow(cm, cmap='Blues')

plt.xticks(np.arange(len(short_labels)), short_labels, rotation=45)
plt.yticks(np.arange(len(short_labels)), short_labels)

plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix (KNN - Blue White)")

# Better text visibility
threshold = cm.max() / 2
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        color = "white" if cm[i, j] > threshold else "black"
        plt.text(j, i, cm[i, j], ha="center", va="center", color=color)

plt.colorbar()
plt.tight_layout()

plt.savefig("confusion_matrix_knn_blue.png")
plt.show()