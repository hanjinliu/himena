from __future__ import annotations

import numpy as np
from qtpy import QtWidgets as QtW
from sklearn.mixture import GaussianMixture
from himena.plugins import validate_protocol
from himena import StandardType, new_window
from himena.types import MergeResult, WidgetDataModel
import matplotlib.pyplot as plt

# This example demonstrates how to combine scikit-learn with the `merge_model` protocol.
# `merge_model` is the protocol method for defining the callback when a window is
# dropped on the widget.

class GmmWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._n_comps = QtW.QSpinBox()
        self._n_comps.setValue(2)
        self._params = QtW.QPlainTextEdit()
        self._params.setReadOnly(True)
        self._drop_mode = QtW.QComboBox()
        self._drop_mode.addItems(["Fit", "Predict", "Plot"])
        self._gmm: GaussianMixture | None = None
        layout.addWidget(self._n_comps)
        layout.addWidget(self._params)
        layout.addWidget(self._drop_mode)

    @validate_protocol
    def update_model(self, model: WidgetDataModel) -> None:
        self._params.setPlainText(str(model.value))

    @validate_protocol
    def mergeable_model_types(self) -> list[StandardType]:
        return [StandardType.TABLE]

    @validate_protocol
    def merge_model(self, model: WidgetDataModel) -> MergeResult:
        input_array = np.asarray(model.value, dtype=np.float64)
        if self._drop_mode.currentText() == "Fit":
            if self._gmm is None:
                self._gmm = GaussianMixture(n_components=self._n_comps.value())
            self._gmm.fit(input_array)
            self._update_text()
            self._n_comps.setEnabled(False)
            return MergeResult(delete_input=False, outputs=None)
        elif self._drop_mode.currentText() == "Predict":
            if self._gmm is None:
                raise ValueError("Model is not created yet.")
            out = self._gmm.predict(input_array)
            output_model = WidgetDataModel(
                value=out,
                type=StandardType.TABLE,
                title=f"[Predict] {model.title}"
            )
            return MergeResult(delete_input=False, outputs=output_model)
        elif self._drop_mode.currentText() == "Plot":
            if self._gmm is None:
                raise ValueError("Model is not created yet.")
            fig, ax = plt.subplots()
            ax.scatter(input_array[:, 0], input_array[:, 1], c=self._gmm.predict(input_array))
            output_model = WidgetDataModel(
                value=fig,
                type=StandardType.MPL_FIGURE,
                title=f"[Plot] {model.title}"
            )
            return MergeResult(delete_input=False, outputs=output_model)

    def _update_text(self):
        self._params.clear()
        for i in range(self._n_comps.value()):
            self._params.appendPlainText(f"Component {i}:")
            self._params.appendPlainText(f"  Weight: {self._gmm.weights_[i]}")
            self._params.appendPlainText(f"  Mean: {self._gmm.means_[i]}")
            self._params.appendPlainText(f"  Covariance: {self._gmm.covariances_[i]}")

if __name__ == "__main__":
    ui = new_window()
    ui.add_widget(GmmWidget())

    # add sample data
    rng = np.random.default_rng(12345)
    data1 = rng.normal(loc=(0, 0), scale=(1, 1), size=(36, 2))
    data2 = rng.normal(loc=(5, 3), scale=(1, 1), size=(32, 2))
    data = np.vstack([data1, data2])
    model = ui.add_object(data, type=StandardType.TABLE, title="Sample Data")

    ui.show(run=True)
