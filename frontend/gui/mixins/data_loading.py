from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox
import requests

from database.utils.import_parsing import SpreadsheetImportError
from database.utils.populate_tables import import_spreadsheet
from database.utils.project_archive import export_project as write_project_archive
from database.utils.project_archive import import_project as extract_project_archive
from frontend.gui.constants import API_BASE_URL, ASPIRATING_SESSION_COLOR, PROJECT_ROOT


def _metadata_text(value):
    return str(value).strip() if value is not None and str(value).strip() else "N/A"


def _aspirating_marker_icon():
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    with QPainter(pixmap) as painter:
        painter.setBrush(ASPIRATING_SESSION_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
    return QIcon(pixmap)


class DataLoadingMixin:
    def _load_initial_ui_state(self):
        self.load_participants()
        if self.participantsSection.count() > 0:
            self.participantsSection.setCurrentRow(0)
        else:
            self.statusBar().showMessage("Import a spreadsheet to load recordings.")

    def export_project(self):
        archive_path, _ = QFileDialog.getSaveFileName(
            self, "Export project", "project.swallowproj", "Swallow projects (*.swallowproj)"
        )
        if not archive_path:
            return
        try:
            missing = write_project_archive(PROJECT_ROOT, archive_path)
        except ValueError as error:
            if not str(error).startswith("Missing audio: "):
                QMessageBox.critical(self, "Export failed", str(error))
                return
            answer = QMessageBox.question(
                self, "Missing recordings",
                f"{error}\n\nCreate an incomplete archive anyway? "
                "Missing recordings will have no audio path in the archive copy. "
                "The current database will not be changed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                missing = write_project_archive(PROJECT_ROOT, archive_path, skip_missing_audio=True)
            except Exception as retry_error:
                QMessageBox.critical(self, "Export failed", str(retry_error))
                return
        except Exception as error:
            QMessageBox.critical(self, "Export failed", str(error))
            return
        if missing:
            QMessageBox.warning(
                self, "Incomplete test archive",
                f"Project saved to {archive_path}, but these recordings were omitted:\n"
                + "\n".join(missing),
            )
            return
        QMessageBox.information(self, "Export complete", f"Project saved to {archive_path}")

    def open_project(self):
        archive_path, _ = QFileDialog.getOpenFileName(
            self, "Open project archive", "", "Swallow projects (*.swallowproj);;ZIP archives (*.zip)"
        )
        if not archive_path:
            return
        parent_path = QFileDialog.getExistingDirectory(self, "Select a folder for the extracted project")
        if not parent_path:
            return
        destination = Path(parent_path) / Path(archive_path).stem
        try:
            extract_project_archive(archive_path, destination)
            settings = QSettings("Thesis", "Swallow Audio Annotation")
            settings.setValue("project_root", str(destination))
            settings.sync()
            if settings.status() != QSettings.Status.NoError:
                raise OSError("Could not save the project selection")
        except Exception as error:
            QMessageBox.critical(self, "Open project failed", str(error))
            return
        QMessageBox.information(
            self,
            "Project ready",
            f"Project extracted to {destination}. Close and reopen the application to use it. "
            "The current project remains open until then.",
        )

    def import_data(self):
        spreadsheet_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select spreadsheet to import",
            "",
            "Excel files (*.xlsx *.xls);;All files (*)",
        )
        if not spreadsheet_path:
            return

        try:
            imported_rows, warnings = import_spreadsheet(spreadsheet_path)
        except SpreadsheetImportError as error:
            QMessageBox.critical(self, "Import failed", str(error))
            return
        except Exception as error:
            QMessageBox.critical(self, "Import failed", f"Unexpected error: {error}")
            return

        self.load_participants()
        # Selection may already be on row 0, which wouldn't retrigger the sessions/swallows chain.
        if self.participantsSection.count() > 0:
            self.participantsSection.setCurrentRow(0)
            self.load_sessions(self.participantsSection.currentItem().text())

        summary = f"Processed {imported_rows} spreadsheet row(s). New records were added; existing records were updated."
        if not warnings:
            QMessageBox.information(self, "Import complete", summary)
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Import completed with warnings")
        dialog.setText(f"{summary}\n\n{len(warnings)} problem(s) were found. Click 'Show Details...' to see them.")
        dialog.setDetailedText("\n".join(warnings))
        dialog.exec()

    def load_participants(self):
        response = requests.get(f"{API_BASE_URL}/participants")
        response.raise_for_status()
        participants = response.json()["participants"]
        self.participant_records = {participant["id"]: participant for participant in participants}
        self.participantsSection.clear()
        for participant in participants:
            self.participantsSection.addItem(participant["id"])

    def load_sessions(self, participant_id=None):
        participant = self.participant_records.get(participant_id, {})
        self.ageValueLabel.setText(_metadata_text(participant.get("age")))
        self.sexValueLabel.setText(_metadata_text(participant.get("gender")))
        self.dxValueLabel.setText(_metadata_text(participant.get("dx")))
        self.methodValueLabel.setText("N/A")
        url = f"{API_BASE_URL}/sessions"
        if participant_id is not None:
            url += f"?participant_id={participant_id}"
        response = requests.get(url)
        response.raise_for_status()
        self.sessionSection.clear()
        self.session_records = {}
        for session in response.json()["sessions"]:
            session_id = str(session["id"])
            self.session_records[session_id] = session
            item = QListWidgetItem(session_id)
            if session.get("aspirating"):
                item.setIcon(_aspirating_marker_icon())
                item.setToolTip("Aspirating session")
            self.sessionSection.addItem(item)
        if self.sessionSection.count() > 0:
            self.sessionSection.setCurrentRow(0)

    def load_swallows(self, session_id=None):
        session = self.session_records.get(session_id)
        self.methodValueLabel.setText(_metadata_text(session.get("method_of_drinking") if session else None))
        if not session_id:
            self.swallowSection.clear()
            self.swallow_records = {}
            return
        if session is not None and session.get("audio_file_path"):
            self.current_audio_start_time = float(session.get("audio_start_time") or 0.0)
            self.load_audio_file(session["audio_file_path"])
        response = requests.get(f"{API_BASE_URL}/swallows/session/{session_id}")
        response.raise_for_status()
        self.swallowSection.clear()
        self.swallow_records = {}
        for swallow in response.json()["swallows"]:
            swallow_number = str(swallow["swallow_number"])
            self.swallow_records[swallow_number] = swallow
            item = QListWidgetItem(swallow_number)
            item.setData(Qt.ItemDataRole.UserRole, swallow_number)
            if swallow.get("flagged"):
                item.setIcon(_aspirating_marker_icon())
                item.setToolTip("Flagged swallow (Which Swallows)")
            self.swallowSection.addItem(item)
        if self.swallowSection.count() > 0:
            self.swallowSection.setCurrentRow(0)

