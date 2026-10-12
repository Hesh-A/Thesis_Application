from PyQt6.QtCore import QSignalBlocker
import requests

from frontend.gui.constants import API_BASE_URL


class AnnotationMixin:
    def load_annotation(self, swallow_id):
        try:
            response = requests.get(f"{API_BASE_URL}/annotations/swallow/{swallow_id}")
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            self.statusBar().showMessage(f"Failed to load annotation: {error}", 5000)
            return
        self._set_annotation_state(data.get("text", ""))

    def _set_annotation_state(self, text):
        with QSignalBlocker(self.annotationText):
            self.annotationText.setPlainText(text)

    def save_annotation(self):
        if self.selected_swallow_id is None:
            self.statusBar().showMessage("Select a swallow before saving an annotation", 3000)
            return

        payload = {"text": self.annotationText.toPlainText()}
        try:
            response = requests.put(
                f"{API_BASE_URL}/annotations/swallow/{self.selected_swallow_id}",
                json=payload,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            self.statusBar().showMessage(f"Failed to save annotation: {error}", 5000)
            return
        self.statusBar().showMessage("Annotation saved", 3000)
